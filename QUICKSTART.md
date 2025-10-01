# Quick Start Guide

## Installation

1. Install dependencies:
```powershell
pip install -r requirements.txt
```

2. Create a `.env` file (or use command-line arguments):
```
CXONE_BASE_URL=https://ast.checkmarx.net
CXONE_TENANT=your_tenant_name
CXONE_API_KEY=your_api_key_here
CXONE_DEBUG=false
```

**Multi-Tenant Setup:**
```powershell
# Create separate env files for each tenant
# .env-rw
# .env-tu
# .env-prod
```

## Running the Tool

### Using environment variables (.env file):
```powershell
python main.py
```

### Using a specific environment file:
```powershell
python main.py --env-file .env-rw
python main.py --env-file .env-tu
```

### Using command-line arguments:
```powershell
python main.py --base-url "https://ast.checkmarx.net" --tenant-name "myorg" --api-key "YOUR_API_KEY"
```

### With debugging:
```powershell
python main.py --debug
```

## What It Does

The tool will:
1. ✓ Authenticate with CxOne
2. ✓ Discover all projects in your tenant
3. ✓ Discover all branches by extracting unique branch names from scans
4. ✓ Locate the most recent successful SCA scan for each branch
5. ✓ Generate and download SCA package reports
6. ✓ Merge all reports into a single CSV file

**Note:** Branches are discovered from scan data (CxOne doesn't have a dedicated branches endpoint), so only branches with at least one scan will be included.

## Output

Two files will be created in the `./output` directory:

### Data File
```
sca_packages_{tenant}_{timestamp}.csv
```

This file contains:
- **ProjectName** - Name of the project
- **ProjectId** - Unique project identifier  
- **BranchName** - Git branch name
- **ScanId** - Unique scan identifier
- **ScanDate** - Timestamp when the scan was created
- All original columns from the SCA Packages.csv (Id, Name, Version, Licenses, vulnerability counts, etc.)

The tool extracts Packages.csv from each downloaded SCA report ZIP file.

### Exception Report
```
sca_packages_{tenant}_{timestamp}_report.txt
```

This report contains:
- Summary statistics for the entire execution
- Lists of branches without SCA scans
- Details of any errors or warnings encountered
- Organized by category for easy review

## Example Output

```
================================================================================
CxOne SCA Package Aggregator
================================================================================
Tenant: myorg
Base URL: https://ast.checkmarx.net
Output Directory: ./output
Max Report Workers: 5
================================================================================

Stage 1: Discovering Projects
  - Total projects: 150

Stage 2: Discovering Branches
  - Total branches: 750
  - Avg branches per project: 5.0

Stage 3: Finding Latest SCA Scans
  - Scans found: 450
  - No SCA scans: 300

Stage 4: Generating SCA Reports
  - Reports generated: 445
  - Reports failed: 5

Stage 5: Merging Reports
  - Total packages: 12,543
  - Files processed: 445
  - Output file: ./output/sca_packages_myorg_20251001_143022.csv

✓ Successfully completed!
Execution time: 2h 15m 30s
================================================================================
```

## Configuration Options

### Environment Variables
- `CXONE_BASE_URL` - Your CxOne region URL
- `CXONE_TENANT` - Your tenant name
- `CXONE_API_KEY` - Your API key
- `CXONE_DEBUG` - Set to `true` for detailed logging
- `CXONE_MAX_WORKERS` - Number of worker threads (default: 10)
- `CXONE_OUTPUT_DIR` - Output directory (default: ./output)

### Command-Line Arguments
- `--env-file PATH` - Specify environment file (default: .env)
- `--base-url` - Override base URL
- `--tenant-name` - Override tenant name
- `--api-key` - Override API key
- `--debug` - Enable debug mode
- `--max-workers N` - Set max worker threads
- `--output-dir PATH` - Set output directory

## Performance Tuning

For large tenants (1000+ projects):
- The tool uses multi-threading by default
- Adjust `--max-workers` based on your system (default: 10)
- Expected runtime: Several hours for large tenants
- Memory usage is optimized through streaming

## Troubleshooting

### "No branches found"
- **Common cause:** Projects have no scans yet
- Branches are discovered from scans, not a separate endpoint
- Verify at least some projects have been scanned
- Enable `--debug` to see scan discovery details

### "No projects found"
- Check your API key has proper permissions
- Verify tenant name is correct

### "Authentication failed"
- Verify API key is not expired
- Check base URL matches your region

### Slow performance
- This is expected for large tenants
- Consider reducing `--max-workers` if you hit rate limits
- Enable `--debug` to see detailed progress

### Partial results
- The tool continues even if some operations fail
- Check debug output for specific errors
- Failed reports are logged but don't stop execution

## Notes

- Temp files are automatically cleaned up after merging
- The tool handles API rate limiting automatically
- Progress bars show real-time status
- All errors are logged but don't stop execution

