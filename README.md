# CxOne SCA Package Aggregator

A comprehensive tool for aggregating SCA (Software Composition Analysis) package reports from all project-branch combinations in Checkmarx One.

## Overview

This tool automates the process of:
1. Discovering all projects in your CxOne tenant
2. Discovering all branches by extracting unique branch names from scans (CxOne has no dedicated branches endpoint)
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
│   │   └── csv_streamer.py  # CSV merging
│   └── operations/          # Business logic operations
│       ├── base.py          # Base operation class
│       ├── project_discovery.py
│       ├── branch_discovery.py
│       ├── scan_finder.py
│       ├── report_generator.py
│       └── data_merger.py
├── main.py                  # Main entry point
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## Setup

1. Clone this repository
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
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

**Multi-Tenant Tip:** Create separate env files (e.g., `.env-rw`, `.env-tu`, `.env-prod`) for different tenants and specify which to use with `--env-file`.

### Command Line Arguments

- `--env-file` - Path to environment file (default: `.env`)
- `--base-url` - Region Base URL
- `--tenant-name` - Tenant name
- `--api-key` - API key for authentication
- `--debug` - Enable debug output
- `--max-workers` - Maximum worker threads for report generation
- `--output-dir` - Output directory for final CSV

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
python main.py --env-file .env-tu
```

With debugging enabled:
```powershell
python main.py --debug
```

With custom output directory and worker count:
```powershell
python main.py --output-dir "C:\Reports" --max-workers 10
```

## Output

The tool generates two files in the output directory:

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
- **Summary Statistics** - Overview of execution (projects, branches, scans, packages)
- **Branches Without SCA Scans** - List of branches that had no SCA scans
- **Report Generation Errors** - Details of any failed report generations
- **ZIP Extraction Warnings** - Issues with extracting or parsing ZIP files
- **Scan Errors** - Errors encountered during scan discovery
- **API Errors** - Problems communicating with the CxOne API
- **General Warnings** - Other warnings encountered during execution

The report is organized by category (not chronologically) for easy review and debugging.

## Performance Considerations

For large tenants with thousands of projects:
- **Expected runtime**: Hours (depending on scale)
- **Memory usage**: Optimized for streaming (minimal memory footprint)
- **Threading**: Configurable workers for optimal performance
- **Rate limiting**: Built-in to prevent API throttling

Default threading configuration:
- Project discovery: 5 workers
- Branch discovery: 20 workers
- Scan queries: 50 workers
- Report generation: 10 workers

## Error Handling

The tool is designed to handle errors gracefully:
- Failed API calls are retried up to 3 times with exponential backoff
- Missing SCA scans are silently skipped
- Failed report generations are logged but don't stop execution
- Partial results are saved even if some operations fail

## Future Enhancements

Potential future features:
- Incremental updates (only process changed projects)
- Resume capability (continue from interrupted execution)
- Filtering options (by project pattern, date range)
- Email/webhook notifications for long-running jobs
- JSON output format option

## Implementation Notes

### Branch Discovery
CxOne does not have a dedicated branches endpoint. Instead, branches are discovered by:
1. Querying all scans for each project
2. Extracting unique branch names from the scan data
3. Creating a list of unique project-branch combinations

This means only branches that have at least one scan will be discovered. Branches with no scans will not appear in the results.

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
