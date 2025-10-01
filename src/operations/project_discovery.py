"""Project discovery operation."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from src.operations.base import Operation
from src.models.project import Project

class ProjectDiscovery(Operation):
    """Discover all CxOne projects."""
    
    def execute(self):
        """Execute project discovery.
        
        Returns:
            list: List of Project objects
        """
        if self.config.debug:
            print("\nFetching all projects...")
        
        # Fetch projects using pagination
        projects_data = self.api_client.get_paginated('/api/projects')
        
        if not projects_data:
            if self.config.debug:
                print("No projects found or error occurred")
            return []
        
        # Convert to Project objects
        projects = []
        for project_data in projects_data:
            try:
                project = Project.from_dict(project_data)
                projects.append(project)
            except Exception as e:
                if self.config.debug:
                    print(f"Error parsing project: {e}")
                continue
        
        if self.config.debug:
            print(f"Found {len(projects)} projects")
        
        return projects

