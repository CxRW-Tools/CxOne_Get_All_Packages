"""Data merger operation."""

from src.operations.base import Operation

class DataMerger(Operation):
    """Merge all SCA reports into a single CSV."""
    
    def execute(self, report_metadata, file_manager, csv_streamer, exception_reporter=None):
        """Execute data merging.
        
        Args:
            report_metadata (list): List of (file_path, metadata_dict) tuples
                                   where metadata_dict has: project_name, project_id, 
                                   branch_name, scan_id, scan_date
            file_manager (FileManager): File manager instance
            csv_streamer (CSVStreamer): CSV streamer instance
            exception_reporter (ExceptionReporter, optional): Exception reporter instance
            
        Returns:
            tuple: (output_path, total_rows, files_processed, files_failed)
        """
        if self.config.debug:
            print(f"\nMerging {len(report_metadata)} reports...")
        
        # Get output file path
        output_path = file_manager.get_output_file_path()
        
        # Merge all CSV files
        total_rows, files_processed, files_failed = csv_streamer.merge_files(
            report_metadata,
            output_path,
            exception_reporter
        )
        
        if self.config.debug:
            print(f"\nData merge completed:")
            print(f"  - Total packages: {total_rows}")
            print(f"  - Files processed: {files_processed}")
            print(f"  - Files failed: {files_failed}")
            print(f"  - Output: {output_path}")
        
        return output_path, total_rows, files_processed, files_failed

