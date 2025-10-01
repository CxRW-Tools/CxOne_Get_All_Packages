"""File management utilities."""

import os
import shutil
from datetime import datetime

class FileManager:
    """Manage temporary and output files."""
    
    def __init__(self, config, debug=False):
        """Initialize the file manager.
        
        Args:
            config (Config): Configuration instance
            debug (bool): Enable debug output
        """
        self.config = config
        self.debug = debug
        self.temp_files = []
    
    def setup_directories(self):
        """Create necessary directories."""
        os.makedirs(self.config.temp_directory, exist_ok=True)
        os.makedirs(self.config.output_directory, exist_ok=True)
        
        if self.debug:
            print(f"Created directories:")
            print(f"  - Temp: {self.config.temp_directory}")
            print(f"  - Output: {self.config.output_directory}")
    
    def get_temp_file_path(self, scan_id, branch_name):
        """Generate a temporary file path.
        
        Args:
            scan_id (str): Scan ID
            branch_name (str): Branch name
            
        Returns:
            str: Full path to temp file
        """
        # Sanitize branch name for filesystem
        safe_branch = branch_name.replace('/', '_').replace('\\', '_')
        filename = f"{scan_id}_{safe_branch}.zip"
        path = os.path.join(self.config.temp_directory, filename)
        self.temp_files.append(path)
        return path
    
    def get_output_file_path(self):
        """Generate the output file path.
        
        Returns:
            str: Full path to output file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        filename = self.config.output_filename_template.format(
            tenant=self.config.tenant_name,
            timestamp=timestamp
        )
        
        return os.path.join(self.config.output_directory, filename)
    
    def cleanup_temp_files(self):
        """Remove all temporary files."""
        if not self.config.temp_file_cleanup:
            if self.debug:
                print("Skipping temp file cleanup (disabled in config)")
            return
        
        removed_count = 0
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    removed_count += 1
            except Exception as e:
                if self.debug:
                    print(f"Failed to remove {file_path}: {e}")
        
        # Remove temp directory if empty
        try:
            if os.path.exists(self.config.temp_directory):
                if not os.listdir(self.config.temp_directory):
                    os.rmdir(self.config.temp_directory)
        except Exception as e:
            if self.debug:
                print(f"Failed to remove temp directory: {e}")
        
        if self.debug:
            print(f"Cleaned up {removed_count} temporary files")
    
    def get_temp_files(self):
        """Get list of all temporary files.
        
        Returns:
            list: List of temp file paths
        """
        return [f for f in self.temp_files if os.path.exists(f)]

