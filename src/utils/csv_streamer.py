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
    
    def merge_files(self, file_metadata_list, output_path, exception_reporter=None):
        """Merge multiple ZIP files (extracting Packages.csv) into one CSV.
        
        Args:
            file_metadata_list (list): List of (file_path, metadata_dict) tuples
                                       where metadata_dict has: project_name, project_id, 
                                       branch_name, scan_id, scan_date
            output_path (str): Path to output file
            exception_reporter (ExceptionReporter, optional): Exception reporter instance
            
        Returns:
            tuple: (total_rows, files_processed, files_failed)
        """
        total_rows = 0
        files_processed = 0
        files_failed = 0
        self.exception_reporter = exception_reporter
        header_written = False
        header_columns = None
        
        with open(output_path, 'w', newline='', encoding='utf-8') as outfile:  # nosec - controlled path
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
                        if self.debug:
                            print(f"  Warning: No Packages.csv found in {file_path}")
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
                    for row in reader:
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
                    
                    if self.debug and file_rows > 0:
                        print(f"  Processed {metadata['project_name']}/{metadata['branch_name']}: {file_rows} packages")
                    
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
        
        return total_rows, files_processed, files_failed
    
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
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:  # nosec - controlled path
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

