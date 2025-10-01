"""Scan data model."""

class Scan:
    """Represents a CxOne scan with SCA results."""
    
    def __init__(self, scan_id, project_id, project_name, branch_name, created_at=None):
        """Initialize a Scan.
        
        Args:
            scan_id (str): The scan ID
            project_id (str): The project ID
            project_name (str): The project name
            branch_name (str): The branch name
            created_at (str, optional): Scan creation timestamp
        """
        self.scan_id = scan_id
        self.project_id = project_id
        self.project_name = project_name
        self.branch_name = branch_name
        self.created_at = created_at
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'scan_id': self.scan_id,
            'project_id': self.project_id,
            'project_name': self.project_name,
            'branch_name': self.branch_name,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create Scan from dictionary."""
        return cls(
            scan_id=data['scan_id'],
            project_id=data['project_id'],
            project_name=data['project_name'],
            branch_name=data['branch_name'],
            created_at=data.get('created_at')
        )
    
    def __repr__(self):
        return f"Scan(id={self.scan_id}, project={self.project_name}, branch={self.branch_name})"

