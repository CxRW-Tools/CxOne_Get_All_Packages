"""Report generation operation."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.operations.base import Operation
from src.models.report_metadata import ReportMetadata

class ReportGenerator(Operation):
    """Generate and download SCA reports."""
    
    def execute(self, scans, file_manager, exception_reporter=None):
        """Execute report generation for all scans.
        
        Args:
            scans (list): List of Scan objects
            file_manager (FileManager): File manager instance
            exception_reporter (ExceptionReporter, optional): Exception reporter instance
            
        Returns:
            list: List of (file_path, metadata_dict) tuples
                  where metadata_dict has: project_name, project_id, branch_name, scan_id, scan_date
        """
        report_metadata = []
        success_count = 0
        failed_count = 0
        self.exception_reporter = exception_reporter
        
        if self.config.debug:
            print(f"\nGenerating SCA reports for {len(scans)} scans...")
        
        # Use threading with rate limiting for report generation
        with ThreadPoolExecutor(max_workers=self.config.max_workers_reports) as executor:
            # Submit all tasks
            future_to_scan = {
                executor.submit(self._generate_and_download_report, scan, file_manager): scan
                for scan in scans
            }
            
            # Process completed tasks
            for future in as_completed(future_to_scan):
                scan = future_to_scan[future]
                try:
                    result = future.result()
                    
                    if result:
                        file_path, metadata = result
                        report_metadata.append((file_path, metadata))
                        success_count += 1
                    else:
                        failed_count += 1
                    
                    if self.progress:
                        self.progress.update(1)
                        self.progress.set_postfix(
                            generated=success_count,
                            failed=failed_count
                        )
                        
                except Exception as e:
                    failed_count += 1
                    if self.config.debug:
                        print(f"\nError generating report for scan {scan.scan_id}: {e}")
                    # Report generation error
                    if self.exception_reporter:
                        self.exception_reporter.add_report_generation_error(
                            scan.project_name,
                            scan.branch_name,
                            scan.scan_id,
                            str(e)
                        )
        
        if self.config.debug:
            print(f"\nReport generation completed:")
            print(f"  - Generated: {success_count}")
            print(f"  - Failed: {failed_count}")
        
        return report_metadata
    
    def _generate_and_download_report(self, scan, file_manager):
        """Generate and download a single SCA report.
        
        Args:
            scan (Scan): Scan object
            file_manager (FileManager): File manager instance
            
        Returns:
            tuple: (file_path, branch_name, project_name) if successful, None otherwise
        """
        try:
            # Rate limiting - intentional delay for API rate limit compliance
            time.sleep(self.config.report_generation_delay)  # nosec - intentional rate limiting
            
            # Step 1: Request report generation
            export_data = {
                'ScanId': scan.scan_id,
                'FileFormat': 'ScanReportCsv'
            }
            
            response = self.api_client.post_sca_export('/api/sca/export/requests', json_data=export_data)
            
            if not response:
                if self.config.debug:
                    print(f"\nFailed to request report for scan {scan.scan_id}")
                return None
            
            # Debug: Print full response to understand structure
            if self.config.debug:
                print(f"\nSCA Export Response: {response}")
            
            # Extract export ID from response - try multiple possible field names
            export_id = (response.get('exportId') or 
                        response.get('ExportId') or
                        response.get('exportID') or
                        response.get('ExportID') or
                        response.get('id') or
                        response.get('Id'))
            
            if not export_id:
                print(f"\nNo exportId in response for scan {scan.scan_id}")
                print(f"Response keys: {list(response.keys())}")
                return None
            
            # Step 2: Poll for completion and get download URL
            file_url = self._wait_for_export_completion(export_id)
            if not file_url:
                if self.config.debug:
                    print(f"\nExport {export_id} did not complete in time")
                return None
            
            # Step 3: Download the report using the fileUrl from the response
            file_path = file_manager.get_temp_file_path(scan.scan_id, scan.branch_name)
            
            # The fileUrl contains the full URL path, extract just the path part
            # fileUrl format: "https://ast.checkmarx.net/api/sca/export/requests/{exportId}/download"
            if file_url.startswith('http'):
                # Extract path from full URL
                from urllib.parse import urlparse
                parsed = urlparse(file_url)
                download_endpoint = parsed.path
            else:
                download_endpoint = file_url
            
            success = self.api_client.download_file(download_endpoint, file_path)
            
            if not success:
                if self.config.debug:
                    print(f"\nFailed to download report for export {export_id}")
                return None
            
            # Return file path and metadata dictionary
            metadata = {
                'project_name': scan.project_name,
                'project_id': scan.project_id,
                'branch_name': scan.branch_name,
                'scan_id': scan.scan_id,
                'scan_date': scan.created_at
            }
            return (file_path, metadata)
            
        except Exception as e:
            if self.config.debug:
                print(f"\nError in report generation for scan {scan.scan_id}: {e}")
            return None
    
    def _wait_for_export_completion(self, export_id):
        """Wait for export to complete with exponential backoff up to max wait time.
        
        Uses exponential backoff strategy:
        - Starts with polling_interval (5s)
        - Doubles each time up to polling_max_wait (2 minutes)
        - Then continues polling every 2 minutes
        - Gives up after max_polling_time (2 hours)
        
        Args:
            export_id (str): Export ID to check
            
        Returns:
            str: fileUrl if completed, None if timed out or failed
        """
        start_time = time.time()
        attempt = 0
        wait_time = self.config.polling_interval
        
        while True:
            elapsed = time.time() - start_time
            
            # Check if we've exceeded max polling time
            if elapsed > self.config.max_polling_time:
                if self.config.debug:
                    print(f"\nExport {export_id} timed out after {elapsed/60:.1f} minutes")
                return None
            
            try:
                # Status check endpoint with query parameter
                status_endpoint = f'/api/sca/export/requests?exportId={export_id}'
                response = self.api_client.get(status_endpoint)  # nosec - export_id from our API
                
                if not response:
                    # Wait before retry with exponential backoff
                    time.sleep(wait_time)  # nosec - intentional polling delay
                    wait_time = min(wait_time * 2, self.config.polling_max_wait)
                    attempt += 1
                    continue
                
                # Get export status
                status = response.get('exportStatus', '').lower()
                
                if self.config.debug and attempt == 0:
                    print(f"\nExport {export_id} initial status: {status}")
                
                if status == 'completed':
                    # Return the fileUrl for downloading
                    file_url = response.get('fileUrl')
                    if self.config.debug:
                        print(f"\nExport {export_id} completed after {elapsed:.1f}s")
                    if file_url:
                        return file_url
                    else:
                        # Fallback to constructing the URL
                        return f'/api/sca/export/requests/{export_id}/download'
                        
                elif status in ['failed', 'error']:
                    error_msg = response.get('errorMessage', 'Unknown error')
                    if self.config.debug:
                        print(f"\nExport {export_id} failed: {error_msg}")
                    return None
                
                # Still processing - wait with exponential backoff
                if self.config.debug and attempt % 10 == 0 and attempt > 0:
                    print(f"\nExport {export_id} still processing... (elapsed: {elapsed/60:.1f}m, wait: {wait_time}s)")
                
                time.sleep(wait_time)  # nosec - intentional polling delay
                
                # Exponential backoff up to max_wait, then stay at max_wait
                wait_time = min(wait_time * 2, self.config.polling_max_wait)
                attempt += 1
                
            except Exception as e:
                if self.config.debug:
                    print(f"\nError checking export status: {e}")
                time.sleep(wait_time)  # nosec - intentional polling delay
                wait_time = min(wait_time * 2, self.config.polling_max_wait)
                attempt += 1
                continue

