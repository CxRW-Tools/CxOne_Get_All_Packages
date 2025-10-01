"""Branch data model."""

class Branch:
    """Represents a project branch."""
    
    def __init__(self, project_id, project_name, branch_name):
        """Initialize a Branch.
        
        Args:
            project_id (str): The project ID
            project_name (str): The project name
            branch_name (str): The branch name
        """
        self.project_id = project_id
        self.project_name = project_name
        self.branch_name = branch_name
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'branch_name': self.branch_name
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create Branch from dictionary."""
        return cls(
            project_id=data['project_id'],
            project_name=data['project_name'],
            branch_name=data['branch_name']
        )
    
    def __repr__(self):
        return f"Branch(project={self.project_name}, branch={self.branch_name})"

