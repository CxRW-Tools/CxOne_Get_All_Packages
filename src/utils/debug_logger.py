"""Debug logging to file with live updates."""

import sys
from datetime import datetime

class DebugLogger:
    """Logger that writes debug output to both console and file in real-time."""
    
    def __init__(self, log_file_path, console_debug=False):
        """Initialize the debug logger.
        
        Args:
            log_file_path (str): Path to the debug log file
            console_debug (bool): Whether to also print to console
        """
        self.log_file_path = log_file_path
        self.console_debug = console_debug
        self.file_handle = None
        
        # Open file in write mode with line buffering for live updates
        try:
            # nosec B113 B601 - controlled path, line buffering for live updates
            self.file_handle = open(log_file_path, 'w', encoding='utf-8', buffering=1)
            self.log(f"Debug log started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log("="*120)
        except Exception as e:
            print(f"Warning: Could not open debug log file: {e}")
    
    def log(self, message):
        """Write a message to the debug log.
        
        Args:
            message (str): Message to log
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_line = f"[{timestamp}] {message}"
        
        # Write to file if handle is open
        if self.file_handle:
            try:
                self.file_handle.write(log_line + '\n')
                self.file_handle.flush()  # Force write to disk immediately
            except Exception as e:
                print(f"Warning: Failed to write to debug log: {e}")
        
        # Also print to console if debug mode is enabled
        if self.console_debug:
            print(message)
    
    def close(self):
        """Close the log file."""
        if self.file_handle:
            try:
                self.log("="*120)
                self.log(f"Debug log ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.file_handle.close()
            except:
                pass
            self.file_handle = None
    
    def __del__(self):
        """Ensure file is closed on destruction."""
        self.close()

