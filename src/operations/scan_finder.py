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
        
        if self.logger:
            self.logger.log(f"Finding latest SCA scans for {len(branches)} branches...")
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
                        if self.logger:
                            self.logger.log(f"  ✓ Found SCA scan for {branch.project_name}/{branch.branch_name}: {scan.scan_id}")
                    else:
                        not_found_count += 1
                        if self.logger:
                            self.logger.log(f"  ✗ No SCA scan found for {branch.project_name}/{branch.branch_name}")
                        # Report branch with no SCA scan
                        if exception_reporter:
                            exception_reporter.add_branch_no_sca(branch.project_name, branch.branch_name)
                    
                    if self.progress:
                        self.progress.update(1)
                        self.progress.set_postfix(
                            found=len(scans_found),
                            not_found=not_found_count
                        )
                        
                except Exception as e:
                    error_count += 1
                    if self.logger:
                        self.logger.log(f"ERROR: Failed to find scan for {branch.project_name}/{branch.branch_name}: {e}")
                    if self.config.debug:
                        print(f"\nError finding scan for {branch.project_name}/{branch.branch_name}: {e}")
                    # Report scan error
                    if exception_reporter:
                        exception_reporter.add_scan_error(branch.project_name, branch.branch_name, str(e))
                    
                    if self.progress:
                        self.progress.update(1)
                        self.progress.set_postfix(
                            found=len(scans_found),
                            not_found=not_found_count
                        )
        
        if self.logger:
            self.logger.log(f"Scan discovery completed: {len(scans_found)} found, {not_found_count} not found, {error_count} errors")
        if self.config.debug:
            print(f"\nScan discovery completed:")
            print(f"  - Scans found: {len(scans_found)}")
            print(f"  - Not found (no SCA): {not_found_count}")
            print(f"  - Errors: {error_count}")
        
        return scans_found
    
    def _find_latest_sca_scan(self, branch):
        """Find the most recent completed SCA scan for a branch.
        
        Accepts scans with:
        - Overall status "Completed" with SCA engine
        - Overall status "Partial" where SCA specifically completed
        
        Args:
            branch (Branch): Branch object
            
        Returns:
            Scan: Scan object if found, None otherwise
        """
        try:
            # Query scans API with filters - include both Completed and Partial
            # Note: We use pagination to find the first valid SCA scan efficiently.
            # Since results are sorted by -created_at, we'll find the most recent first.
            params = {
                'project-id': branch.project_id,
                'branch': branch.branch_name,
                'statuses': 'Completed,Partial',
                'sort': '-created_at',
                'limit': self.config.page_size,  # Fetch in pages
                'offset': 0
            }
            
            # Paginate manually to stop as soon as we find a valid SCA scan
            while True:
                response_data = self.api_client.get('/api/scans', params=params)
                
                if not response_data:
                    return None
                
                # Handle different response formats
                if isinstance(response_data, dict):
                    scans_list = response_data.get('scans', [])
                elif isinstance(response_data, list):
                    scans_list = response_data
                else:
                    return None
                
                if not scans_list:
                    return None
                
                # Check this page for a valid SCA scan
                valid_scan = self._find_first_valid_sca_scan(scans_list)
                if valid_scan:
                    return valid_scan
                
                # If page wasn't full, we've reached the end
                if len(scans_list) < self.config.page_size:
                    return None
                
                # Move to next page
                params['offset'] += self.config.page_size
        
        except Exception as e:
            if self.config.debug:
                print(f"\nError querying scans for {branch.project_name}/{branch.branch_name}: {e}")
            return None
    
    def _find_first_valid_sca_scan(self, scans_list):
        """Find the first valid SCA scan from a list of scans.
        
        Args:
            scans_list (list): List of scan data from API
            
        Returns:
            Scan: First valid SCA scan if found, None otherwise
        """
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
            
            if not has_sca:
                continue
            
            # For Partial scans, verify SCA specifically completed
            scan_status = scan_data.get('status', '')
            if scan_status == 'Partial':
                if not self._is_sca_completed(scan_data):
                    if self.logger:
                        self.logger.log(f"  Skipping Partial scan {scan_data.get('id')} - SCA did not complete")
                    if self.config.debug:
                        print(f"\nSkipping Partial scan {scan_data.get('id')} - SCA did not complete")
                    continue
            
            # Check if scan has actual package results
            scan_id = scan_data.get('id')
            if not self._has_package_results(scan_id):
                if self.logger:
                    self.logger.log(f"  Skipping scan {scan_id} - No package results found")
                if self.config.debug:
                    print(f"\nSkipping scan {scan_id} - No package results")
                continue
            
            # Valid SCA scan found - need to extract branch info from scan_data
            scan = Scan(
                scan_id=scan_data.get('id'),
                project_id=scan_data.get('projectId'),
                project_name=scan_data.get('projectName'),
                branch_name=scan_data.get('branch'),
                created_at=scan_data.get('createdAt')
            )
            return scan
        
        # No valid SCA scan found in this list
        return None
    
    def _is_sca_completed(self, scan_data):
        """Check if SCA engine specifically completed in a Partial scan.
        
        Args:
            scan_data (dict): Scan data from API
            
        Returns:
            bool: True if SCA completed, False otherwise
        """
        status_details = scan_data.get('statusDetails', [])
        
        for detail in status_details:
            if detail.get('name', '').lower() == 'sca':
                sca_status = detail.get('status', '')
                return sca_status == 'Completed'
        
        # If no SCA statusDetails found, assume not completed
        return False
    
    def _has_package_results(self, scan_id):
        """Check if a scan has actual package results.
        
        Uses the scan-summary API to check if scaPackagesCounters.totalCounter > 0
        
        Args:
            scan_id (str): Scan ID to check
            
        Returns:
            bool: True if scan has packages, False otherwise
        """
        try:
            # Call scan-summary endpoint with the scan ID
            # Endpoint: GET /api/scan-summary?scan-ids={scan_id}
            params = {'scan-ids': scan_id}
            response_data = self.api_client.get('/api/scan-summary', params=params)
            
            if not response_data:
                if self.logger:
                    self.logger.log(f"  WARNING: No response from scan-summary API for scan {scan_id}")
                # If we can't check, assume it has packages to avoid false negatives
                return True
            
            # Extract scaPackagesCounters from the response
            scans_summaries = response_data.get('scansSummaries', [])
            if not scans_summaries:
                if self.logger:
                    self.logger.log(f"  WARNING: No scan summary found for scan {scan_id}")
                # If we can't check, assume it has packages to avoid false negatives
                return True
            
            # Get the first (and should be only) summary
            summary = scans_summaries[0]
            sca_packages_counters = summary.get('scaPackagesCounters', {})
            total_packages = sca_packages_counters.get('totalCounter', 0)
            
            if self.logger:
                self.logger.log(f"  Scan {scan_id} has {total_packages} packages")
            
            return total_packages > 0
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"  ERROR: Failed to check package results for scan {scan_id}: {e}")
            if self.config.debug:
                print(f"\nError checking package results for scan {scan_id}: {e}")
            # If we can't check due to error, assume it has packages to avoid false negatives
            return True

