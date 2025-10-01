"""Progress tracking utilities."""

from tqdm import tqdm
import sys

class ProgressTracker:
    """Track and display progress for long-running operations."""
    
    def __init__(self, debug=False):
        """Initialize the progress tracker.
        
        Args:
            debug (bool): Enable debug output
        """
        self.debug = debug
        self.current_bar = None
    
    def create_bar(self, total, description, unit='items'):
        """Create a new progress bar.
        
        Args:
            total (int): Total number of items
            description (str): Description of the operation
            unit (str): Unit name for items
            
        Returns:
            tqdm: Progress bar instance
        """
        if self.current_bar:
            self.current_bar.close()
        
        self.current_bar = tqdm(
            total=total,
            desc=description,
            unit=unit,
            ncols=100,
            file=sys.stdout
        )
        return self.current_bar
    
    def update(self, n=1):
        """Update the current progress bar.
        
        Args:
            n (int): Number of items to increment
        """
        if self.current_bar:
            self.current_bar.update(n)
    
    def close(self):
        """Close the current progress bar."""
        if self.current_bar:
            self.current_bar.close()
            self.current_bar = None
    
    def set_postfix(self, **kwargs):
        """Set postfix values for the progress bar.
        
        Args:
            **kwargs: Key-value pairs to display
        """
        if self.current_bar:
            self.current_bar.set_postfix(**kwargs)
    
    def print(self, message):
        """Print a message without interfering with progress bar.
        
        Args:
            message (str): Message to print
        """
        if self.current_bar:
            self.current_bar.write(message)
        else:
            print(message)


class StageTracker:
    """Track multi-stage operations."""
    
    def __init__(self, debug=False):
        """Initialize the stage tracker.
        
        Args:
            debug (bool): Enable debug output
        """
        self.debug = debug
        self.stats = {}
    
    def start_stage(self, stage_name):
        """Start a new stage.
        
        Args:
            stage_name (str): Name of the stage
        """
        print(f"\n{'='*80}")
        print(f"Stage: {stage_name}")
        print(f"{'='*80}")
        self.stats[stage_name] = {}
    
    def end_stage(self, stage_name, **stats):
        """End a stage and record statistics.
        
        Args:
            stage_name (str): Name of the stage
            **stats: Statistics to record
        """
        self.stats[stage_name].update(stats)
        
        print(f"\n{stage_name} completed:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")
    
    def get_stats(self):
        """Get all recorded statistics.
        
        Returns:
            dict: All statistics
        """
        return self.stats
    
    def print_summary(self):
        """Print a summary of all stages."""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        
        for stage, stats in self.stats.items():
            print(f"\n{stage}:")
            for key, value in stats.items():
                print(f"  - {key}: {value}")

