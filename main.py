#!/usr/bin/env python3
"""
CxOne SCA Package Aggregator

Aggregates SCA package reports from all project-branch combinations in CxOne.
"""

import sys
import argparse
import time
from datetime import datetime
from src.utils.auth import AuthManager
from src.utils.config import Config
from src.utils.api_client import APIClient
from src.utils.progress import ProgressTracker, StageTracker
from src.utils.file_manager import FileManager
from src.utils.csv_streamer import CSVStreamer
from src.utils.exception_reporter import ExceptionReporter
from src.utils.debug_logger import DebugLogger
from src.operations.project_discovery import ProjectDiscovery
from src.operations.branch_discovery import BranchDiscovery
from src.operations.scan_finder import ScanFinder
from src.operations.report_generator import ReportGenerator
from src.operations.data_merger import DataMerger

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='CxOne SCA Package Aggregator - Collect SCA packages from all project-branch combinations'
    )
    parser.add_argument('--env-file', help='Path to environment file (default: .env)')
    parser.add_argument('--base-url', help='Region Base URL')
    parser.add_argument('--tenant-name', help='Tenant name')
    parser.add_argument('--api-key', help='API key for authentication')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--max-workers', type=int, help='Maximum worker threads for report generation')
    parser.add_argument('--output-dir', help='Output directory for final CSV')
    parser.add_argument('--retry-failed', help='Path to failed reports CSV file to retry only those scans')
    return parser.parse_args()

def load_failed_scans(failed_csv_path):
    """Load scans from a failed reports CSV file.
    
    Args:
        failed_csv_path (str): Path to the failed reports CSV file
        
    Returns:
        list: List of Scan objects from the CSV
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist
        ValueError: If the CSV format is invalid
    """
    import csv
    import os
    from src.models.scan import Scan
    
    if not os.path.exists(failed_csv_path):
        raise FileNotFoundError(f"Failed reports file not found: {failed_csv_path}")
    
    scans = []
    
    with open(failed_csv_path, 'r', encoding='utf-8') as f:  # nosec B113 - user-provided file path
        reader = csv.DictReader(f)
        
        # Validate header
        expected_headers = {'ProjectName', 'ProjectId', 'BranchName', 'ScanId', 'ScanDate'}
        actual_headers = set(reader.fieldnames or [])
        
        if not expected_headers.issubset(actual_headers):
            missing = expected_headers - actual_headers
            raise ValueError(f"Invalid CSV format. Missing headers: {missing}")
        
        for row in reader:
            scan = Scan(
                scan_id=row['ScanId'],
                project_id=row['ProjectId'],
                project_name=row['ProjectName'],
                branch_name=row['BranchName'],
                created_at=row['ScanDate']
            )
            scans.append(scan)
    
    return scans

def main():
    """Main entry point."""
    start_time = time.time()
    
    # Parse arguments
    args = parse_args()
    
    # Initialize configuration (with optional custom env file)
    env_file = args.env_file if hasattr(args, 'env_file') and args.env_file else '.env'
    config = Config.from_env(env_file)
    
    # Override with command line arguments if provided
    if args.base_url:
        config.base_url = args.base_url
    if args.tenant_name:
        config.tenant_name = args.tenant_name
    if args.api_key:
        config.api_key = args.api_key
    if args.debug:
        config.debug = args.debug
    if args.max_workers:
        config.max_workers_reports = args.max_workers
    if args.output_dir:
        config.output_directory = args.output_dir

    # Validate configuration
    is_valid, error = config.validate()
    if not is_valid:
        print(f"Configuration error: {error}")
        sys.exit(1)

    print("="*120)
    print("CxOne SCA Package Aggregator")
    print("="*120)
    print(f"Tenant: {config.tenant_name}")
    print(f"Base URL: {config.base_url}")
    print(f"Output Directory: {config.output_directory}")
    print(f"Max Report Workers: {config.max_workers_reports}")
    print("="*120)

    # Initialize auth manager
    auth_manager = AuthManager(
        base_url=config.base_url,
        tenant_name=config.tenant_name,
        api_key=config.api_key,
        debug=config.debug
    )

    try:
        # Verify authentication works
        auth_manager.ensure_authenticated()
        
        if config.debug:
            print("\n✓ Successfully authenticated with CxOne")
        
        # Initialize utilities
        file_manager = FileManager(config, config.debug)
        
        # Setup directories
        file_manager.setup_directories()
        
        # Initialize debug logger (always active, writes to file)
        debug_log_path = file_manager.get_debug_log_path()
        debug_logger = DebugLogger(debug_log_path, console_debug=config.debug)
        debug_logger.log(f"CxOne SCA Package Aggregator - Debug Log")
        debug_logger.log(f"Tenant: {config.tenant_name}")
        debug_logger.log(f"Base URL: {config.base_url}")
        debug_logger.log(f"Max Report Workers: {config.max_workers_reports}")
        debug_logger.log("="*120)
        
        api_client = APIClient(config.base_url, auth_manager, config, config.debug, debug_logger)
        progress_tracker = ProgressTracker(config.debug)
        stage_tracker = StageTracker(config.debug)
        csv_streamer = CSVStreamer(config.debug, debug_logger)
        exception_reporter = ExceptionReporter()
        
        # Check if in retry mode
        if args.retry_failed:
            print(f"\n⚠️  RETRY MODE: Loading scans from {args.retry_failed}")
            debug_logger.log(f"RETRY MODE: Loading failed scans from {args.retry_failed}")
            scans = load_failed_scans(args.retry_failed)
            print(f"✓ Loaded {len(scans)} failed scans for retry\n")
            debug_logger.log(f"Loaded {len(scans)} scans for retry")
            
            # Set dummy values for summary statistics
            projects = []
            branches = []
        else:
            # ========================================
            # Stage 1: Discover Projects
            # ========================================
            stage_tracker.start_stage("Stage 1: Discovering Projects")
            debug_logger.log("Starting Stage 1: Project Discovery")
            
            project_discovery = ProjectDiscovery(config, auth_manager, api_client, progress_tracker, debug_logger)
            projects = project_discovery.execute()
            
            if not projects:
                print("No projects found. Exiting.")
                debug_logger.log("ERROR: No projects found")
                debug_logger.close()
                sys.exit(0)
            
            debug_logger.log(f"Found {len(projects)} projects")
            stage_tracker.end_stage(
                "Stage 1: Discovering Projects",
                total_projects=len(projects)
            )
            
            # ========================================
            # Stage 2: Discover Branches
            # ========================================
            stage_tracker.start_stage("Stage 2: Discovering Branches")
            debug_logger.log(f"Starting Stage 2: Branch Discovery for {len(projects)} projects")
            
            progress_bar = progress_tracker.create_bar(len(projects), "Fetching branches", "projects")
            
            branch_discovery = BranchDiscovery(config, auth_manager, api_client, progress_tracker, debug_logger)
            branches = branch_discovery.execute(projects)
            
            progress_tracker.close()
            
            if not branches:
                print("No branches found. Exiting.")
                debug_logger.log("ERROR: No branches found")
                debug_logger.close()
                sys.exit(0)
            
            debug_logger.log(f"Found {len(branches)} branches across all projects")
            avg_branches = len(branches) / len(projects) if projects else 0
            stage_tracker.end_stage(
                "Stage 2: Discovering Branches",
                total_branches=len(branches),
                avg_branches_per_project=f"{avg_branches:.1f}"
            )
            
            # ========================================
            # Stage 3: Find Latest SCA Scans
            # ========================================
            stage_tracker.start_stage("Stage 3: Finding Latest SCA Scans")
            debug_logger.log(f"Starting Stage 3: Scan Finding for {len(branches)} branches")
            
            progress_bar = progress_tracker.create_bar(len(branches), "Finding SCA scans", "branches")
            
            scan_finder = ScanFinder(config, auth_manager, api_client, progress_tracker, debug_logger)
            scans = scan_finder.execute(branches, exception_reporter)
            
            progress_tracker.close()
            
            if not scans:
                print("No SCA scans found. Exiting.")
                debug_logger.log("ERROR: No SCA scans found")
                debug_logger.close()
                sys.exit(0)
            
            debug_logger.log(f"Found {len(scans)} SCA scans")
            stage_tracker.end_stage(
                "Stage 3: Finding Latest SCA Scans",
                scans_found=len(scans),
                no_sca_scans=len(branches) - len(scans)
            )
        
        # ========================================
        # Stage 4: Generate SCA Reports
        # ========================================
        stage_tracker.start_stage("Stage 4: Generating SCA Reports")
        debug_logger.log(f"Starting Stage 4: Report Generation for {len(scans)} scans")
        
        progress_bar = progress_tracker.create_bar(len(scans), "Generating reports", "scans")
        
        report_generator = ReportGenerator(config, auth_manager, api_client, progress_tracker, debug_logger)
        report_metadata = report_generator.execute(scans, file_manager, exception_reporter)
        
        progress_tracker.close()
        
        if not report_metadata:
            print("No reports generated. Exiting.")
            debug_logger.log("ERROR: No reports generated successfully")
            debug_logger.close()
            sys.exit(0)
        
        debug_logger.log(f"Generated {len(report_metadata)} reports, {len(scans) - len(report_metadata)} failed")
        stage_tracker.end_stage(
            "Stage 4: Generating SCA Reports",
            reports_generated=len(report_metadata),
            reports_failed=len(scans) - len(report_metadata)
        )
        
        # ========================================
        # Stage 5: Merge All Reports
        # ========================================
        stage_tracker.start_stage("Stage 5: Merging Reports")
        debug_logger.log(f"Starting Stage 5: Data Merging for {len(report_metadata)} reports")
        
        data_merger = DataMerger(config, auth_manager, api_client, progress_tracker, debug_logger)
        output_path, total_rows, files_processed, files_failed = data_merger.execute(
            report_metadata, 
            file_manager, 
            csv_streamer,
            exception_reporter
        )
        
        debug_logger.log(f"Merged {total_rows:,} packages from {files_processed} files ({files_failed} failed)")
        stage_tracker.end_stage(
            "Stage 5: Merging Reports",
            total_packages=total_rows,
            files_processed=files_processed,
            files_failed=files_failed,
            output_file=output_path
        )
        
        # ========================================
        # Cleanup
        # ========================================
        if config.temp_file_cleanup:
            print("\nCleaning up temporary files...")
            debug_logger.log("Cleaning up temporary files...")
            file_manager.cleanup_temp_files()
        
        # ========================================
        # Generate Exception Report
        # ========================================
        elapsed_time = time.time() - start_time
        hours = int(elapsed_time // 3600)
        minutes = int((elapsed_time % 3600) // 60)
        seconds = int(elapsed_time % 60)
        
        # Update report statistics (handle retry mode)
        exception_reporter.update_stats(
            total_projects=len(projects) if not args.retry_failed else 0,
            total_branches=len(branches) if not args.retry_failed else 0,
            scans_found=len(scans),
            scans_not_found=len(branches) - len(scans) if not args.retry_failed else 0,
            reports_generated=len(report_metadata),
            reports_failed=len(scans) - len(report_metadata),
            packages_merged=total_rows,
            files_processed=files_processed,
            files_failed=files_failed,
            execution_time=f"{hours}h {minutes}m {seconds}s",
            output_file=output_path,
            output_size=get_file_size(output_path)
        )
        
        report_path = exception_reporter.generate_report(output_path)
        failed_csv_path = exception_reporter.generate_failed_reports_csv(output_path)
        
        # Log final statistics
        debug_logger.log("="*120)
        debug_logger.log("EXECUTION COMPLETED")
        debug_logger.log(f"Total projects: {len(projects) if not args.retry_failed else 'N/A (retry mode)'}")
        debug_logger.log(f"Total branches: {len(branches) if not args.retry_failed else 'N/A (retry mode)'}")
        debug_logger.log(f"Scans found: {len(scans)}")
        debug_logger.log(f"Reports generated: {len(report_metadata)}")
        debug_logger.log(f"Reports failed: {len(scans) - len(report_metadata)}")
        debug_logger.log(f"Total packages: {total_rows:,}")
        debug_logger.log(f"Execution time: {hours}h {minutes}m {seconds}s")
        debug_logger.log(f"Output file: {output_path}")
        if failed_csv_path:
            debug_logger.log(f"Failed reports CSV: {failed_csv_path}")
        debug_logger.log("="*120)
        
        # Close debug logger
        debug_logger.close()
        
        # ========================================
        # Final Summary
        # ========================================
        
        print("\n" + "="*120)
        if args.retry_failed:
            print("RETRY EXECUTION SUMMARY")
        else:
            print("EXECUTION SUMMARY")
        print("="*120)
        print(f"✓ Successfully completed!")
        print(f"\nStatistics:")
        if not args.retry_failed:
            print(f"  - Total projects: {len(projects)}")
            print(f"  - Total branches: {len(branches)}")
            print(f"  - Branches with SCA: {len(scans)}")
        else:
            print(f"  - Retry attempts: {len(scans)}")
        print(f"  - Reports generated: {len(report_metadata)}")
        print(f"  - Reports failed: {len(scans) - len(report_metadata)}")
        print(f"  - Total packages: {total_rows:,}")
        print(f"\nOutput:")
        print(f"  - Data File: {output_path}")
        print(f"  - Size: {get_file_size(output_path)}")
        print(f"  - Report File: {report_path}")
        print(f"  - Debug Log: {debug_log_path}")
        if failed_csv_path:
            print(f"  - Failed Reports: {failed_csv_path}")
            if not args.retry_failed:
                print(f"\n💡 Tip: Retry failed reports using: --retry-failed {failed_csv_path}")
        print(f"\nExecution time: {hours}h {minutes}m {seconds}s")
        print("="*120)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        if 'debug_logger' in locals():
            debug_logger.log("INTERRUPTED: Operation cancelled by user")
            debug_logger.close()
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        if 'debug_logger' in locals():
            debug_logger.log(f"FATAL ERROR: {e}")
            if config.debug:
                import traceback
                debug_logger.log(f"Traceback: {traceback.format_exc()}")
            debug_logger.close()
        elif config.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def get_file_size(file_path):
    """Get human-readable file size.
    
    Args:
        file_path (str): Path to file
        
    Returns:
        str: Formatted file size
    """
    try:
        import os
        size_bytes = os.path.getsize(file_path)
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.1f} TB"
    except:
        return "Unknown"

if __name__ == "__main__":
    main() 