class Operation:
    """Base class for all operations."""
    
    def __init__(self, config, auth_manager, api_client=None, progress=None, debug_logger=None):
        """Initialize the operation.
        
        Args:
            config (Config): Configuration instance
            auth_manager (AuthManager): Authentication manager instance
            api_client (APIClient, optional): API client instance
            progress (ProgressTracker, optional): Progress tracker instance
            debug_logger (DebugLogger, optional): Debug logger instance
        """
        self.config = config
        self.auth = auth_manager
        self.api_client = api_client
        self.progress = progress
        self.logger = debug_logger

    def execute(self):
        """Execute the operation.
        
        This method should be overridden by specific operations.
        """
        raise NotImplementedError("Operation must implement execute method") 