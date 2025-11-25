# CxOne SCA Package Aggregator

A comprehensive tool for aggregating SCA (Software Composition Analysis) package reports from all project-branch combinations in Checkmarx One.

## Overview

This tool automates the process of:
1. Discovering all projects in your CxOne tenant
2. Discovering all branches by extracting unique branch names from scans
3. Finding the most recent successful SCA scan for each project-branch combination
4. Generating and downloading SCA package reports
5. Merging all reports into a single CSV with branch information

## Features

- **Multi-threaded execution** for performance at scale
- **Progress tracking** with live status updates
- **Memory-efficient** streaming for large datasets
- **Robust error handling** with detailed logging
- **Configurable** via environment variables or command-line arguments
- **Production-ready** with retry logic and rate limiting
- **Package filtering** with OR (||) and AND (&&) logic support

## Project Structure

```
.
├── src/
│   ├── models/              # Data models
│   │   ├── project.py       # Project representation
│   │   ├── branch.py        # Branch representation
│   │   ├── scan.py          # Scan representation
│   │   └── report_metadata.py
│   ├── utils/               # Utility modules
│   │   ├── auth.py          # Authentication management
│   │   ├── config.py        # Configuration handling
│   │   ├── api_client.py    # API client with pagination
│   │   ├── progress.py      # Progress tracking
│   │   ├── file_manager.py  # File management
│   │   ├── csv_streamer.py  # CSV merging
│   │   ├── exception_reporter.py  # Exception tracking
│   │   └── debug_logger.py  # Live debug logging
│   └── operations/          # Business logic operations
│       ├── base.py          # Base operation class
│       ├── project_discovery.py
│       ├── branch_discovery.py
│       ├── scan_finder.py
│       ├── report_generator.py
│       └── data_merger.py
├── main.py                  # Main entry point
├── csv_to_xlsx.py          # Helper: CSV to Excel converter
├── filter_csv.py           # Helper: CSV filtering tool
├── requirements.txt         # Dependencies
├── example.env             # Example environment file template
├── LICENSE                 # MIT License
└── README.md               # This file
```

## Setup

1. Clone this repository
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. (Optional) Copy `example.env` to `.env` and configure your CxOne credentials:
   ```powershell
   copy example.env .env
   # Edit .env with your credentials
   ```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

- `CXONE_BASE_URL` - Region Base URL (e.g., `https://ast.checkmarx.net`)
- `CXONE_TENANT` - Tenant name
- `CXONE_API_KEY` - API key for authentication
- `CXONE_DEBUG` - Enable debug output (set to `true` to enable)
- `CXONE_MAX_WORKERS` - Maximum worker threads for report generation (optional)
- `CXONE_OUTPUT_DIR` - Output directory (optional, default: `./output`)
- `CXONE_FILTER_PACKAGES` - Filter packages by field=value with OR (||) and AND (&&) logic (optional)

**Multi-Tenant Tip:** Create separate env files (e.g., `.env-rw`, `.env-test`, `.env-prod`) for different tenants and specify which to use with `--env-file`. You can use `example.env` as a template.

### Command Line Arguments

- `--env-file` - Path to environment file (default: `.env`)
- `--base-url` - Region Base URL
- `--tenant-name` - Tenant name
- `--api-key` - API key for authentication
- `--debug` - Enable debug output
- `--max-workers` - Maximum worker threads for report generation
- `--output-dir` - Output directory for final CSV
- `--filter-packages` - Filter packages by field=value with OR (||) and AND (&&) logic support
- `--retry-failed` - Path to failed reports CSV file to retry only those scans

Command line arguments take precedence over environment variables.

## Usage

### Basic Usage

Using environment variables:
```powershell
python main.py
```

Using command-line arguments:
```powershell
python main.py --base-url "https://ast.checkmarx.net" --tenant-name "myorg" --api-key "YOUR_API_KEY"
```

### Advanced Usage

With a specific environment file:
```powershell
python main.py --env-file .env-rw
python main.py --env-file .env-test
```

With debugging enabled:
```powershell
python main.py --debug
```

With custom output directory and worker count:
```powershell
python main.py --output-dir "C:\Reports" --max-workers 10
```

Retrying failed reports:
```powershell
# Retry only the scans that failed in a previous run
python main.py --retry-failed "output\sca_packages_tenant_20251001_143022_failed-reports.csv"
```

With package filtering:
```powershell
# Only npm packages
python main.py --filter-packages "PackageRepository=npm"

# Only npm and pypi packages (OR logic)
python main.py --filter-packages "PackageRepository=npm||pypi"

# Only packages with critical vulnerabilities
python main.py --filter-packages "CriticalVulnerabilityCount>0"

# Only outdated packages
python main.py --filter-packages "Outdated=true"
```

## Output

The tool generates three main files in the output directory (plus an optional fourth file if there are failures):

### 1. Data File (CSV)
```
sca_packages_{tenant}_{timestamp}.csv
```

The CSV includes:
- **ProjectName** - Name of the project
- **ProjectId** - Unique project identifier
- **BranchName** - Git branch name
- **ScanId** - Unique scan identifier
- **ScanDate** - Timestamp when the scan was created
- All original columns from the SCA Packages report (Id, Name, Version, Licenses, MatchType, vulnerability counts, etc.)

The tool extracts the Packages.csv file from each SCA report ZIP and merges them with the prepended metadata columns.

### 2. Exception Report (TXT)
```
sca_packages_{tenant}_{timestamp}_report.txt
```

The report includes:
- **Summary Statistics** - Overview of execution (projects, branches, scans, packages, filtering stats if applicable)
- **Branches Without SCA Scans** - List of branches that had no SCA scans
- **Report Generation Errors** - Details of any failed report generations (see `*_failed-reports.csv` for retry capability)
- **ZIP Extraction Warnings** - Issues with extracting or parsing ZIP files
- **Scan Errors** - Errors encountered during scan discovery
- **API Errors** - Problems communicating with the CxOne API
- **General Warnings** - Other warnings encountered during execution

The report is organized by category (not chronologically) for easy review and debugging. If filtering was enabled, the summary statistics will include packages filtered out and total packages before filtering.

### 3. Debug Log (TXT)
```
sca_packages_{tenant}_{timestamp}_debug.txt
```

A live debug log that is **always generated** (regardless of `--debug` flag) containing:
- Timestamped entries for all operations
- Stage transitions and progress milestones
- Detailed error messages and stack traces
- Real-time updates (flushed immediately, can be monitored during execution)

This file is invaluable for troubleshooting long-running jobs and can be tailed during execution:
```powershell
Get-Content -Path "output\sca_packages_tenant_20251001_143022_debug.txt" -Wait -Tail 50
```

### 4. Failed Reports CSV (Optional)
```
sca_packages_{tenant}_{timestamp}_failed-reports.csv
```

This file is **only generated if there are failed report generations**. It contains:
- **ProjectName** - Name of the project
- **ProjectId** - Unique project identifier
- **BranchName** - Git branch name
- **ScanId** - Unique scan identifier
- **ScanDate** - Timestamp when the scan was created
- **ErrorMessage** - Details of why the report generation failed

This file can be used with the `--retry-failed` argument to retry only the failed scans:
```powershell
python main.py --retry-failed "output\sca_packages_tenant_20251001_143022_failed-reports.csv"
```

## Helper Tools

The repository includes two helper scripts for post-processing the generated CSV files:

### 1. CSV to Excel Converter (`csv_to_xlsx.py`)

Converts large CSV files to Excel (.xlsx) format using chunk-based processing. Handles files that may exceed Excel's row limit (1,048,576 rows).

**Features:**
- Chunk-based processing for memory efficiency
- Progress bar with real-time statistics
- Automatic handling of Excel row limits
- File size and row count reporting

**Usage:**
```powershell
# Basic conversion
python csv_to_xlsx.py --input data.csv --output data.xlsx

# With custom chunk size for large files
python csv_to_xlsx.py -i huge_file.csv -o output.xlsx --chunk-size 100000
```

**Arguments:**
- `--input`, `-i` - Path to input CSV file (required)
- `--output`, `-o` - Path to output XLSX file (required)
- `--chunk-size`, `-c` - Rows to process at a time (default: 50,000)

**Notes:**
- Excel has a maximum of 1,048,576 rows per worksheet
- Files exceeding this limit will be truncated with a warning
- Larger chunk sizes are faster but use more memory

### 2. CSV Filter Tool (`filter_csv.py`)

Filters CSV files based on field values with support for OR and AND logic. Uses chunk-based processing for large files.

**Features:**
- Case-insensitive filtering
- OR logic with `||` operator
- AND logic with `&&` operator
- Progress bar with real-time statistics
- Memory-efficient chunk-based processing

**Usage:**
```powershell
# Filter for npm packages only
python filter_csv.py --input data.csv --output npm_packages.csv --filter-packages "PackageRepository=npm"

# Filter for multiple package repositories (OR logic)
python filter_csv.py -i data.csv -o packages.csv --filter-packages "PackageRepository=npm||nuget||pypi"

# Filter for malicious packages
python filter_csv.py -i data.csv -o malicious.csv --filter-packages "IsMalicious=true"

# Filter for outdated packages
python filter_csv.py -i data.csv -o outdated.csv --filter-packages "Outdated=true"

# Custom chunk size for large files
python filter_csv.py -i huge_file.csv -o filtered.csv --filter-packages "PackageRepository=npm" --chunk-size 100000
```

**Arguments:**
- `--input`, `-i` - Path to input CSV file (required)
- `--output`, `-o` - Path to output CSV file (required)
- `--filter-packages` - Filter criteria in format "field=value" with OR (`||`) and AND (`&&`) logic (required)
- `--chunk-size`, `-c` - Rows to process at a time (default: 50,000)

**Common Use Cases:**
```powershell
# Filter by package repository
python filter_csv.py -i packages.csv -o npm_only.csv --filter-packages "PackageRepository=npm"

# Filter by multiple repositories (OR logic)
python filter_csv.py -i packages.csv -o packages.csv --filter-packages "PackageRepository=npm||pypi||nuget"

# Filter malicious packages
python filter_csv.py -i packages.csv -o malicious.csv --filter-packages "IsMalicious=true"

# Filter outdated packages
python filter_csv.py -i packages.csv -o outdated.csv --filter-packages "Outdated=true"

# Filter packages with vulnerabilities
python filter_csv.py -i packages.csv -o vulnerable.csv --filter-packages "CriticalVulnerabilityCount>0"
```

**Note:** The filter syntax matches the main tool (`--filter-packages "field=value"`), making it consistent across both tools.

**Note:** All dependencies for the helper tools are included in `requirements.txt`.

## Package Filtering

The tool supports filtering packages during the merge process using the `--filter-packages` argument or `CXONE_FILTER_PACKAGES` environment variable.

### Filter Syntax

- **Format**: `field=value`
- **OR Logic**: Use `||` to match any of multiple values
- **AND Logic**: Use `&&` to match all values (for string matching)
- **Case Insensitive**: All comparisons are case-insensitive

### Examples

```powershell
# Filter by package repository
python main.py --filter-packages "PackageRepository=npm"
python main.py --filter-packages "PackageRepository=npm||pypi||nuget"

# Filter by vulnerability count
python main.py --filter-packages "CriticalVulnerabilityCount>0"
python main.py --filter-packages "HighVulnerabilityCount>0"

# Filter by package status
python main.py --filter-packages "Outdated=true"
python main.py --filter-packages "Outdated=false"

# Filter by package name (partial matching)
python main.py --filter-packages "Name=react"
python main.py --filter-packages "Name=react||vue||angular"

# Filter for malicious packages
python main.py --filter-packages "IsMalicious=true"
```

### Common Use Cases

- **Security Focus**: `CriticalVulnerabilityCount>0` - Only packages with critical vulnerabilities
- **Repository Focus**: `PackageRepository=npm` - Only npm packages
- **Outdated Packages**: `Outdated=true` - Only outdated packages
- **Multiple Repositories**: `PackageRepository=npm||pypi||nuget` - npm, Python, or .NET packages

### Performance Impact

- **Filtering occurs during CSV merging** (Stage 5)
- **No impact on API calls** - all reports are still generated
- **Reduces final CSV size** and processing time for downstream analysis
- **Memory efficient** - filtering happens row-by-row during streaming

## Performance Considerations

For large tenants with tens of thousands of projects:
- **Expected runtime**: Hours (depending on scale)
- **Memory usage**: Optimized for streaming (minimal memory footprint)
- **Threading**: Configurable workers for optimal performance
- **Rate limiting**: Built-in to prevent API throttling

Default threading configuration:
- Project discovery: 5 workers
- Branch discovery: 20 workers
- Scan queries: 20 workers
- Report generation: 10 workers

## Error Handling

The tool is designed to handle errors gracefully:
- Failed API calls are retried up to 3 times with exponential backoff
- Missing SCA scans are silently skipped
- Failed report generations are logged but don't stop execution
- Partial results are saved even if some operations fail

## Troubleshooting

### Authentication Issues
- Verify your API key is valid and not expired
- Ensure the base URL matches your region
- Check tenant name is correct

### No Branches Found
- Verify that scans exist for your projects
- Branches are discovered from scans, so projects with no scans will show no branches
- Enable `--debug` flag to see which projects have scans

### No Data Returned
- Verify projects exist in your tenant
- Check that SCA scans have been run
- Enable `--debug` flag for detailed logging

### Performance Issues
- Reduce `--max-workers` if experiencing rate limiting
- Check network connectivity
- Monitor memory usage with debug mode

## License

MIT License

Copyright (c) 2024-2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
