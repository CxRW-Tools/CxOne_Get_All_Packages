"""Exception and summary reporting utilities."""

import os
from datetime import datetime

class ExceptionReporter:
    """Track and report exceptions, warnings, and summaries throughout execution."""
    
    def __init__(self):
        """Initialize the exception reporter."""
        self.branches_no_sca = []
        self.scan_errors = []
        self.report_generation_errors = []
        self.zip_extraction_warnings = []
        self.api_errors = []
        self.general_warnings = []
        
        # Summary statistics
        self.stats = {
            'total_projects': 0,
            'total_branches': 0,
            'scans_found': 0,
            'scans_not_found': 0,
            'reports_generated': 0,
            'reports_failed': 0,
            'packages_merged': 0,
            'files_processed': 0,
            'files_failed': 0,
            'execution_time': '0h 0m 0s',
            'output_file': '',
            'output_size': ''
        }
    
    def add_branch_no_sca(self, project_name, branch_name):
        """Record a branch with no SCA scans."""
        self.branches_no_sca.append({
            'project': project_name,
            'branch': branch_name
        })
    
    def add_scan_error(self, project_name, branch_name, error_message):
        """Record a scan-related error."""
        self.scan_errors.append({
            'project': project_name,
            'branch': branch_name,
            'error': error_message
        })
    
    def add_report_generation_error(self, project_name, branch_name, scan_id, error_message):
        """Record a report generation error."""
        self.report_generation_errors.append({
            'project': project_name,
            'branch': branch_name,
            'scan_id': scan_id,
            'error': error_message
        })
    
    def add_zip_extraction_warning(self, project_name, branch_name, scan_id, warning_message):
        """Record a ZIP extraction warning."""
        self.zip_extraction_warnings.append({
            'project': project_name,
            'branch': branch_name,
            'scan_id': scan_id,
            'warning': warning_message
        })
    
    def add_api_error(self, endpoint, error_message):
        """Record an API error."""
        self.api_errors.append({
            'endpoint': endpoint,
            'error': error_message
        })
    
    def add_general_warning(self, category, message):
        """Record a general warning."""
        self.general_warnings.append({
            'category': category,
            'message': message
        })
    
    def update_stats(self, **kwargs):
        """Update summary statistics."""
        self.stats.update(kwargs)
    
    def generate_report(self, output_csv_path):
        """Generate and save the exception report.
        
        Args:
            output_csv_path (str): Path to the CSV output file
            
        Returns:
            str: Path to the generated report file
        """
        # Generate report filename (same as CSV but .txt)
        report_path = os.path.splitext(output_csv_path)[0] + '_report.txt'
        
        # Build report content
        lines = []
        lines.append("=" * 80)
        lines.append("CxOne SCA Package Aggregator - Execution Report")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # === SUMMARY STATISTICS ===
        lines.append("=" * 80)
        lines.append("SUMMARY STATISTICS")
        lines.append("=" * 80)
        lines.append(f"Total Projects:        {self.stats['total_projects']:,}")
        lines.append(f"Total Branches:        {self.stats['total_branches']:,}")
        lines.append(f"Scans Found:           {self.stats['scans_found']:,}")
        lines.append(f"Scans Not Found:       {self.stats['scans_not_found']:,}")
        lines.append(f"Reports Generated:     {self.stats['reports_generated']:,}")
        lines.append(f"Reports Failed:        {self.stats['reports_failed']:,}")
        lines.append(f"Total Packages:        {self.stats['packages_merged']:,}")
        lines.append(f"CSV Files Processed:   {self.stats['files_processed']:,}")
        lines.append(f"CSV Files Failed:      {self.stats['files_failed']:,}")
        lines.append(f"Execution Time:        {self.stats['execution_time']}")
        lines.append(f"Output File:           {self.stats['output_file']}")
        if self.stats['output_size']:
            lines.append(f"Output Size:           {self.stats['output_size']}")
        lines.append("")
        
        # === BRANCHES WITHOUT SCA SCANS ===
        if self.branches_no_sca:
            lines.append("=" * 80)
            lines.append(f"BRANCHES WITHOUT SCA SCANS ({len(self.branches_no_sca)})")
            lines.append("=" * 80)
            lines.append("")
            
            # Group by project
            by_project = {}
            for item in self.branches_no_sca:
                project = item['project']
                if project not in by_project:
                    by_project[project] = []
                by_project[project].append(item['branch'])
            
            for project in sorted(by_project.keys()):
                lines.append(f"Project: {project}")
                for branch in sorted(by_project[project]):
                    lines.append(f"  - {branch}")
                lines.append("")
        
        # === REPORT GENERATION ERRORS ===
        if self.report_generation_errors:
            lines.append("=" * 80)
            lines.append(f"REPORT GENERATION ERRORS ({len(self.report_generation_errors)})")
            lines.append("=" * 80)
            lines.append("")
            
            for idx, error in enumerate(self.report_generation_errors, 1):
                lines.append(f"{idx}. Project: {error['project']}")
                lines.append(f"   Branch: {error['branch']}")
                lines.append(f"   Scan ID: {error['scan_id']}")
                lines.append(f"   Error: {error['error']}")
                lines.append("")
        
        # === ZIP EXTRACTION WARNINGS ===
        if self.zip_extraction_warnings:
            lines.append("=" * 80)
            lines.append(f"ZIP EXTRACTION WARNINGS ({len(self.zip_extraction_warnings)})")
            lines.append("=" * 80)
            lines.append("")
            
            for idx, warning in enumerate(self.zip_extraction_warnings, 1):
                lines.append(f"{idx}. Project: {warning['project']}")
                lines.append(f"   Branch: {warning['branch']}")
                lines.append(f"   Scan ID: {warning['scan_id']}")
                lines.append(f"   Warning: {warning['warning']}")
                lines.append("")
        
        # === SCAN ERRORS ===
        if self.scan_errors:
            lines.append("=" * 80)
            lines.append(f"SCAN ERRORS ({len(self.scan_errors)})")
            lines.append("=" * 80)
            lines.append("")
            
            for idx, error in enumerate(self.scan_errors, 1):
                lines.append(f"{idx}. Project: {error['project']}")
                lines.append(f"   Branch: {error['branch']}")
                lines.append(f"   Error: {error['error']}")
                lines.append("")
        
        # === API ERRORS ===
        if self.api_errors:
            lines.append("=" * 80)
            lines.append(f"API ERRORS ({len(self.api_errors)})")
            lines.append("=" * 80)
            lines.append("")
            
            for idx, error in enumerate(self.api_errors, 1):
                lines.append(f"{idx}. Endpoint: {error['endpoint']}")
                lines.append(f"   Error: {error['error']}")
                lines.append("")
        
        # === GENERAL WARNINGS ===
        if self.general_warnings:
            lines.append("=" * 80)
            lines.append(f"GENERAL WARNINGS ({len(self.general_warnings)})")
            lines.append("=" * 80)
            lines.append("")
            
            # Group by category
            by_category = {}
            for warning in self.general_warnings:
                category = warning['category']
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(warning['message'])
            
            for category in sorted(by_category.keys()):
                lines.append(f"Category: {category}")
                for message in by_category[category]:
                    lines.append(f"  - {message}")
                lines.append("")
        
        # === SUCCESS SUMMARY ===
        if not (self.branches_no_sca or self.report_generation_errors or 
                self.zip_extraction_warnings or self.scan_errors or 
                self.api_errors or self.general_warnings):
            lines.append("=" * 80)
            lines.append("NO ERRORS OR WARNINGS")
            lines.append("=" * 80)
            lines.append("All operations completed successfully!")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        # Write to file
        with open(report_path, 'w', encoding='utf-8') as f:  # nosec - controlled path
            f.write('\n'.join(lines))
        
        return report_path

