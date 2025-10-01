"""Branch discovery operation."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from src.operations.base import Operation
from src.models.branch import Branch

class BranchDiscovery(Operation):
    """Discover all branches for projects by querying scans."""
    
    def execute(self, projects):
        """Execute branch discovery for all projects.
        
        Note: Branches are discovered by querying scans, as CxOne doesn't have
        a dedicated branches endpoint. We extract unique branch names from scans.
        
        Args:
            projects (list): List of Project objects
            
        Returns:
            list: List of Branch objects
        """
        all_branches = []
        
        if self.logger:
            self.logger.log(f"Discovering branches from scans for {len(projects)} projects...")
        if self.config.debug:
            print(f"\nDiscovering branches from scans for {len(projects)} projects...")
        
        # Use threading for branch discovery
        with ThreadPoolExecutor(max_workers=self.config.max_workers_branches) as executor:
            # Submit all tasks
            future_to_project = {
                executor.submit(self._get_branches_for_project, project): project
                for project in projects
            }
            
            # Process completed tasks
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                try:
                    branches = future.result()
                    all_branches.extend(branches)
                    
                    if self.progress:
                        self.progress.update(1)
                        self.progress.set_postfix(
                            total_branches=len(all_branches),
                            current_project=project.name[:30]
                        )
                        
                except Exception as e:
                    if self.logger:
                        self.logger.log(f"ERROR: Failed to fetch branches for {project.name}: {e}")
                    if self.config.debug:
                        print(f"\nError fetching branches for {project.name}: {e}")
        
        if self.logger:
            self.logger.log(f"Found {len(all_branches)} total branches across all projects")
        if self.config.debug:
            print(f"\nFound {len(all_branches)} total branches across all projects")
        
        return all_branches
    
    def _get_branches_for_project(self, project):
        """Get all unique branches for a project by querying its scans.
        
        Args:
            project (Project): Project object
            
        Returns:
            list: List of Branch objects
        """
        try:
            # Query scans for this project to extract branch names
            params = {
                'project-id': project.id
            }
            
            scans_data = self.api_client.get_paginated('/api/scans', params=params)
            
            if not scans_data:
                return []
            
            # Extract unique branch names from scans
            branch_names = set()
            for scan in scans_data:
                branch_name = scan.get('branch')
                if branch_name:
                    branch_names.add(branch_name)
            
            # Create Branch objects for each unique branch
            branches = []
            for branch_name in sorted(branch_names):
                branch = Branch(
                    project_id=project.id,
                    project_name=project.name,
                    branch_name=branch_name
                )
                branches.append(branch)
            
            if self.logger:
                self.logger.log(f"  Project {project.name}: Found {len(branches)} unique branches from {len(scans_data)} scans")
            
            return branches
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"ERROR: Exception in branch discovery for {project.name}: {e}")
            if self.config.debug:
                print(f"\nError fetching branches for {project.name}: {e}")
            return []

