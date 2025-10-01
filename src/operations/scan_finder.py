"""Scan finder operation."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from src.operations.base import Operation
from src.models.scan import Scan

class ScanFinder(Operation):
    """Find the most recent SCA scan for each project-branch combination."""
    
    def execute(self, branches, exception_reporter=None):
        """Execute scan finding for all branches.
        
        Args:
            branches (list): List of Branch objects
            exception_reporter (ExceptionReporter, optional): Exception reporter instance
            
        Returns:
            list: List of Scan objects with SCA results
        """
        scans_found = []
        not_found_count = 0
        error_count = 0
        
        if self.config.debug:
            print(f"\nFinding latest SCA scans for {len(branches)} branches...")
        
        # Use threading for scan discovery
        with ThreadPoolExecutor(max_workers=self.config.max_workers_scans) as executor:
            # Submit all tasks
            future_to_branch = {
                executor.submit(self._find_latest_sca_scan, branch): branch
                for branch in branches
            }
            
            # Process completed tasks
            for future in as_completed(future_to_branch):
                branch = future_to_branch[future]
                try:
                    scan = future.result()
                    
                    if scan:
                        scans_found.append(scan)
                    else:
                        not_found_count += 1
                        # Report branch with no SCA scan
                        if exception_reporter:
                            exception_reporter.add_branch_no_sca(branch.project_name, branch.branch_name)
                    
                    if self.progress:
                        self.progress.update(1)
                        self.progress.set_postfix(
                            found=len(scans_found),
                            not_found=not_found_count,
                            errors=error_count
                        )
                        
                except Exception as e:
                    error_count += 1
                    if self.config.debug:
                        print(f"\nError finding scan for {branch.project_name}/{branch.branch_name}: {e}")
                    # Report scan error
                    if exception_reporter:
                        exception_reporter.add_scan_error(branch.project_name, branch.branch_name, str(e))
        
        if self.config.debug:
            print(f"\nScan discovery completed:")
            print(f"  - Scans found: {len(scans_found)}")
            print(f"  - Not found (no SCA): {not_found_count}")
            print(f"  - Errors: {error_count}")
        
        return scans_found
    
    def _find_latest_sca_scan(self, branch):
        """Find the most recent completed SCA scan for a branch.
        
        Args:
            branch (Branch): Branch object
            
        Returns:
            Scan: Scan object if found, None otherwise
        """
        try:
            # Query scans API with filters
            params = {
                'project-id': branch.project_id,
                'branch': branch.branch_name,
                'statuses': 'Completed',
                'sort': '-created_at',
                'limit': 10  # Get top 10 to check for SCA
            }
            
            scans_data = self.api_client.get('/api/scans', params=params)
            
            if not scans_data:
                return None
            
            # Handle different response formats
            if isinstance(scans_data, dict):
                scans_list = scans_data.get('scans', [])
            elif isinstance(scans_data, list):
                scans_list = scans_data
            else:
                return None
            
            # Find first scan with SCA results
            for scan_data in scans_list:
                # Check if scan has SCA engine
                engines = scan_data.get('engines', [])
                
                # Handle both string array and object array formats
                has_sca = False
                if engines:
                    for engine in engines:
                        if isinstance(engine, str):
                            if engine.lower() == 'sca':
                                has_sca = True
                                break
                        elif isinstance(engine, dict):
                            engine_name = engine.get('name', '').lower()
                            if engine_name == 'sca':
                                has_sca = True
                                break
                
                if has_sca:
                    scan = Scan(
                        scan_id=scan_data.get('id'),
                        project_id=branch.project_id,
                        project_name=branch.project_name,
                        branch_name=branch.branch_name,
                        created_at=scan_data.get('createdAt')
                    )
                    return scan
            
            # No SCA scan found
            return None
            
        except Exception as e:
            if self.config.debug:
                print(f"\nError querying scans for {branch.project_name}/{branch.branch_name}: {e}")
            return None

