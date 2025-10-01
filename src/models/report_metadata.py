"""Report metadata model."""

class ReportMetadata:
    """Represents metadata for a generated report."""
    
    def __init__(self, scan_id, project_name, branch_name, file_path=None, 
                 export_id=None, status='pending'):
        """Initialize ReportMetadata.
        
        Args:
            scan_id (str): The scan ID
            project_name (str): The project name
            branch_name (str): The branch name
            file_path (str, optional): Path to downloaded CSV file
            export_id (str, optional): Export request ID
            status (str): Status of the report (pending, generating, completed, failed)
        """
        self.scan_id = scan_id
        self.project_name = project_name
        self.branch_name = branch_name
        self.file_path = file_path
        self.export_id = export_id
        self.status = status
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'scan_id': self.scan_id,
            'project_name': self.project_name,
            'branch_name': self.branch_name,
            'file_path': self.file_path,
            'export_id': self.export_id,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create ReportMetadata from dictionary."""
        return cls(
            scan_id=data['scan_id'],
            project_name=data['project_name'],
            branch_name=data['branch_name'],
            file_path=data.get('file_path'),
            export_id=data.get('export_id'),
            status=data.get('status', 'pending')
        )
    
    def __repr__(self):
        return f"ReportMetadata(scan={self.scan_id}, status={self.status})"

