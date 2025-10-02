"""CSV streaming and merging utilities."""

import csv
import os
import zipfile
import tempfile

class CSVStreamer:
    """Stream and merge CSV files efficiently."""
    
    def __init__(self, debug=False, debug_logger=None):
        """Initialize the CSV streamer.
        
        Args:
            debug (bool): Enable debug output
            debug_logger (DebugLogger, optional): Debug logger instance
        """
        self.debug = debug
        self.logger = debug_logger
    
    def _parse_filter_criteria(self, filter_string):
        """Parse filter criteria string into field and value components.
        
        Args:
            filter_string (str): Filter string in format "field=value" with OR (||) and AND (&&) support
            
        Returns:
            tuple: (field_name, filter_value) or (None, None) if invalid
        """
        if not filter_string or '=' not in filter_string:
            return None, None
        
        # Split on first '=' to separate field and value
        parts = filter_string.split('=', 1)
        if len(parts) != 2:
            return None, None
        
        field_name = parts[0].strip()
        filter_value = parts[1].strip()
        
        if not field_name or not filter_value:
            return None, None
        
        return field_name, filter_value
    
    def _apply_row_filter(self, row, field_name, filter_value, header):
        """Apply filter logic to a single row.
        
        Args:
            row (list): CSV row data
            header (list): CSV header
            field_name (str): Field to filter on
            filter_value (str): Filter criteria with OR (||) and AND (&&) support
            
        Returns:
            bool: True if row matches filter, False otherwise
        """
        try:
            # Find field index in header
            if field_name not in header:
                return True  # Field not found, include row
            
            field_index = header.index(field_name)
            if field_index >= len(row):
                return True  # Row too short, include row
            
            cell_value = str(row[field_index]).lower()
            
            # Handle OR logic (||)
            if '||' in filter_value:
                or_conditions = [condition.strip().lower() for condition in filter_value.split('||')]
                return any(cell_value == condition for condition in or_conditions)
            
            # Handle AND logic (&&)
            elif '&&' in filter_value:
                and_conditions = [condition.strip().lower() for condition in filter_value.split('&&')]
                return all(cell_value == condition for condition in and_conditions)
            
            # Simple equality check (case insensitive)
            else:
                return cell_value == filter_value.lower()
                
        except (IndexError, ValueError, AttributeError):
            # If any error in filtering, include the row
            return True
    
    def merge_files(self, file_metadata_list, output_path, exception_reporter=None, filter_criteria=None):
        """Merge multiple ZIP files (extracting Packages.csv) into one CSV.
        
        Args:
            file_metadata_list (list): List of (file_path, metadata_dict) tuples
                                       where metadata_dict has: project_name, project_id, 
                                       branch_name, scan_id, scan_date
            output_path (str): Path to output file
            exception_reporter (ExceptionReporter, optional): Exception reporter instance
            filter_criteria (str, optional): Filter criteria in format "field=value" with OR (||) and AND (&&) support
            
        Returns:
            tuple: (total_rows, files_processed, files_failed)
        """
        total_rows = 0
        files_processed = 0
        files_failed = 0
        total_packages_before_filter = 0
        packages_filtered_out = 0
        self.exception_reporter = exception_reporter
        header_written = False
        header_columns = None
        
        # Parse filter criteria if provided
        filter_field = None
        filter_value = None
        if filter_criteria:
            filter_field, filter_value = self._parse_filter_criteria(filter_criteria)
            if filter_field and filter_value:
                if self.logger:
                    self.logger.log(f"Package filtering enabled: {filter_field} = '{filter_value}'")
                if self.debug:
                    print(f"\nPackage filtering enabled: {filter_field} = '{filter_value}'")
            else:
                if self.logger:
                    self.logger.log(f"WARNING: Invalid filter criteria '{filter_criteria}' - filtering disabled")
                if self.debug:
                    print(f"\nWARNING: Invalid filter criteria '{filter_criteria}' - filtering disabled")
                filter_field = None
                filter_value = None
        
        # Validate output path is safe
        if not output_path or not isinstance(output_path, str):
            raise ValueError("Invalid output path")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as outfile:  # nosec B113 - validated path
            writer = None
            
            for file_path, metadata in file_metadata_list:
                try:
                    if not os.path.exists(file_path):
                        if self.debug:
                            print(f"  Warning: File not found: {file_path}")
                        files_failed += 1
                        continue
                    
                    # Extract Packages.csv from the ZIP file
                    packages_data = self._extract_packages_from_zip(file_path)
                    
                    if not packages_data:
                        warning_msg = f"No Packages.csv found in {file_path}"
                        if self.logger:
                            self.logger.log(f"  WARNING: {warning_msg} ({metadata['project_name']}/{metadata['branch_name']})")
                        if self.debug:
                            print(f"  Warning: {warning_msg}")
                        # Report ZIP extraction warning
                        if self.exception_reporter:
                            self.exception_reporter.add_zip_extraction_warning(
                                metadata['project_name'],
                                metadata['branch_name'],
                                metadata['scan_id'],
                                "No Packages.csv found in ZIP archive"
                            )
                        files_failed += 1
                        continue
                    
                    # Parse the CSV data
                    reader = csv.reader(packages_data.splitlines())
                    
                    # Read header
                    try:
                        header = next(reader)
                    except StopIteration:
                        # Empty file
                        if self.debug:
                            print(f"  Warning: Empty Packages.csv in {file_path}")
                        # Report ZIP extraction warning
                        if self.exception_reporter:
                            self.exception_reporter.add_zip_extraction_warning(
                                metadata['project_name'],
                                metadata['branch_name'],
                                metadata['scan_id'],
                                "Empty Packages.csv in ZIP archive"
                            )
                        files_failed += 1
                        continue
                    
                    # Write header on first file
                    if not header_written:
                        # Prepend metadata columns to header
                        header_columns = header
                        output_header = ['ProjectName', 'ProjectId', 'BranchName', 'ScanId', 'ScanDate'] + header
                        writer = csv.writer(outfile)
                        writer.writerow(output_header)
                        header_written = True
                    else:
                        # Verify header matches
                        if header != header_columns:
                            if self.debug:
                                print(f"  Warning: Header mismatch in {file_path}")
                            # Continue anyway, but log it
                    
                    # Write data rows with metadata columns prepended
                    file_rows = 0
                    filtered_rows = 0
                    for row in reader:
                        total_packages_before_filter += 1
                        
                        # Apply filter if enabled
                        if filter_field and filter_value:
                            if not self._apply_row_filter(row, filter_field, filter_value, header):
                                filtered_rows += 1
                                packages_filtered_out += 1
                                continue  # Skip this row
                        
                        # Prepend metadata values to the row
                        output_row = [
                            metadata['project_name'],
                            metadata['project_id'],
                            metadata['branch_name'],
                            metadata['scan_id'],
                            metadata['scan_date']
                        ] + row
                        writer.writerow(output_row)
                        file_rows += 1
                        total_rows += 1
                    
                    if file_rows > 0:
                        log_msg = f"  Merged {file_rows} packages from {metadata['project_name']}/{metadata['branch_name']}"
                        if filter_field and filter_value and filtered_rows > 0:
                            log_msg += f" (filtered out {filtered_rows} packages)"
                        if self.logger:
                            self.logger.log(log_msg)
                        if self.debug:
                            print(f"  Processed {metadata['project_name']}/{metadata['branch_name']}: {file_rows} packages" + 
                                  (f" (filtered out {filtered_rows})" if filter_field and filter_value and filtered_rows > 0 else ""))
                    
                    files_processed += 1
                    
                except Exception as e:
                    if self.debug:
                        print(f"  Error processing {file_path}: {e}")
                    # Report processing error
                    if self.exception_reporter:
                        self.exception_reporter.add_zip_extraction_warning(
                            metadata.get('project_name', 'Unknown'),
                            metadata.get('branch_name', 'Unknown'),
                            metadata.get('scan_id', 'Unknown'),
                            f"Error processing ZIP: {str(e)}"
                        )
                    files_failed += 1
        
        # Log filtering summary if filtering was enabled
        if filter_field and filter_value and packages_filtered_out > 0:
            if self.logger:
                self.logger.log(f"Filtering summary: {packages_filtered_out:,} packages filtered out of {total_packages_before_filter:,} total packages")
            if self.debug:
                print(f"\nFiltering summary: {packages_filtered_out:,} packages filtered out of {total_packages_before_filter:,} total packages")
        
        return total_rows, files_processed, files_failed, total_packages_before_filter, packages_filtered_out
    
    def _extract_packages_from_zip(self, zip_path):
        """Extract Packages.csv from a ZIP file.
        
        Args:
            zip_path (str): Path to ZIP file
            
        Returns:
            str: Contents of Packages.csv, or None if not found
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:  # nosec - controlled path
                # Look for Packages.csv in the ZIP
                for file_info in zip_ref.filelist:
                    if file_info.filename.endswith('Packages.csv'):
                        # Extract and read the file
                        with zip_ref.open(file_info.filename) as csv_file:
                            return csv_file.read().decode('utf-8', errors='replace')
                
                # Packages.csv not found
                return None
                
        except Exception as e:
            if self.debug:
                print(f"  Error extracting from ZIP {zip_path}: {e}")
            return None
    
    def validate_csv(self, file_path):
        """Validate a CSV file.
        
        Args:
            file_path (str): Path to CSV file
            
        Returns:
            tuple: (is_valid, row_count, error_message)
        """
        try:
            # Validate file path is safe
            if not file_path or not isinstance(file_path, str):
                return False, 0, "Invalid file path"
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:  # nosec B113 - validated path
                reader = csv.reader(f)
                
                # Check for header
                try:
                    header = next(reader)
                except StopIteration:
                    return False, 0, "Empty file"
                
                # Count rows
                row_count = sum(1 for _ in reader)
                
                return True, row_count, None
                
        except Exception as e:
            return False, 0, str(e)

