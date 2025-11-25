#!/usr/bin/env python3
"""
CSV Filter Script
Filters a CSV file based on field=value criteria with OR (||) and AND (&&) logic support.
Uses chunk-based processing for large files.
Matches the syntax used by the main tool (--filter-packages).
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import tqdm


def parse_filter_criteria(filter_string):
    """Parse filter criteria string into field and value components.
    
    Args:
        filter_string (str): Filter string in format "field=value" with OR (||) and AND (&&) support
        
    Returns:
        tuple: (field_name, filter_value) or (None, None) if invalid
    """
    if not filter_string or '=' not in filter_string:
        return None, None
    
    # Split on first '=' to separate field and value
    parts = filter_string.split('=', 1)
    if len(parts) != 2:
        return None, None
    
    field_name = parts[0].strip()
    filter_value = parts[1].strip()
    
    if not field_name or not filter_value:
        return None, None
    
    return field_name, filter_value


def apply_filter_logic(df, field, filter_value):
    """
    Apply filter logic to DataFrame based on field and filter criteria.
    Supports OR (||) and AND (&&) logic.
    Handles non-string columns by converting to string first.
    
    Args:
        df (DataFrame): DataFrame to filter
        field (str): Column name to filter on
        filter_value (str): Filter criteria with OR (||) and AND (&&) support
        
    Returns:
        DataFrame: Filtered DataFrame
    """
    # Convert column to string for comparison (handles boolean, numeric, etc.)
    # Use astype(str) instead of .str accessor to handle all types
    field_values = df[field].astype(str).str.lower()
    
    # Handle OR logic (||)
    if '||' in filter_value:
        # Split by || and create OR condition
        or_conditions = [field_values == condition.strip().lower() for condition in filter_value.split('||')]
        # Combine with OR logic
        combined_condition = or_conditions[0]
        for condition in or_conditions[1:]:
            combined_condition = combined_condition | condition
        return df[combined_condition]
    
    # Handle AND logic (&&)
    elif '&&' in filter_value:
        # Split by && and create AND condition
        and_conditions = [field_values == condition.strip().lower() for condition in filter_value.split('&&')]
        # Combine with AND logic
        combined_condition = and_conditions[0]
        for condition in and_conditions[1:]:
            combined_condition = combined_condition & condition
        return df[combined_condition]
    
    # Simple equality check (case insensitive)
    else:
        return df[field_values == filter_value.lower()]


def filter_csv(input_file, output_file, filter_criteria, chunk_size=50000):
    """
    Filter a CSV file based on filter criteria in field=value format.
    
    Args:
        input_file (str): Path to the input CSV file
        output_file (str): Path to the output CSV file
        filter_criteria (str): Filter criteria in format "field=value" with OR (||) and AND (&&) support
        chunk_size (int): Number of rows to process at a time (default: 50000)
        
    Returns:
        bool: True if filtering successful, False otherwise
    """
    # Parse filter criteria
    field, filter_value = parse_filter_criteria(filter_criteria)
    if not field or not filter_value:
        print(f"Error: Invalid filter criteria '{filter_criteria}'. Must be in format 'field=value'", file=sys.stderr)
        return False
    try:
        # Check if input file exists and resolve to absolute path
        input_path = Path(input_file).resolve()
        if not input_path.exists():
            print(f"Error: Input file '{input_file}' does not exist.", file=sys.stderr)
            return False
        
        if not input_path.is_file():
            print(f"Error: '{input_file}' is not a file.", file=sys.stderr)
            return False
        
        # Get file size
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        print(f"Input file size: {file_size_mb:.2f} MB")
        
        # Count total lines in the file
        print("Counting total lines in file...")
        total_lines = 0
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            for _ in f:
                total_lines += 1
        
        # Subtract 1 for header (we'll process header separately)
        data_rows = total_lines - 1
        print(f"Total lines: {total_lines:,} (including header)")
        print(f"Data rows to process: {data_rows:,}")
        
        # Get output path and resolve to absolute path
        output_path = Path(output_file).resolve()
        
        # Ensure output has .csv extension
        if output_path.suffix.lower() != '.csv':
            output_path = output_path.with_suffix('.csv')
            print(f"Note: Adding .csv extension to output file: {output_path}")
        
        print(f"Filtering CSV in chunks of {chunk_size:,} rows...")
        print(f"Filter: {field} = '{filter_value}' (case insensitive)")
        print(f"Reading from: {input_path}")
        print(f"Writing to: {output_path}")
        print()
        
        total_rows_processed = 0
        total_rows_written = 0
        chunk_num = 0
        header_written = False
        num_columns = 0
        
        # Check if PackageRepository column exists in first chunk
        first_chunk = True
        
        # Create progress bar
        progress_bar = tqdm.tqdm(
            total=data_rows,
            desc="Processing CSV",
            unit="rows",
            unit_scale=True,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
        
        # Process CSV in chunks
        for chunk in pd.read_csv(str(input_path), chunksize=chunk_size, low_memory=False):
            chunk_num += 1
            chunk_rows = len(chunk)
            total_rows_processed += chunk_rows
            
            # Check if specified field column exists
            if first_chunk:
                if field not in chunk.columns:
                    progress_bar.close()
                    print(f"Error: Column '{field}' not found in CSV file.", file=sys.stderr)
                    print(f"Available columns: {', '.join(chunk.columns)}", file=sys.stderr)
                    return False
                num_columns = len(chunk.columns)
                first_chunk = False
            
            # Apply filter logic
            filtered_chunk = apply_filter_logic(chunk, field, filter_value)
            filtered_rows = len(filtered_chunk)
            
            if filtered_rows > 0:
                # Write header on first filtered chunk
                if not header_written:
                    filtered_chunk.to_csv(str(output_path), index=False, mode='w')
                    header_written = True
                    total_rows_written += filtered_rows
                else:
                    # Append data rows only (skip header)
                    filtered_chunk.to_csv(str(output_path), index=False, mode='a', header=False)
                    total_rows_written += filtered_rows
            
            # Update progress bar
            progress_bar.update(chunk_rows)
            progress_bar.set_postfix({
                'chunk': chunk_num,
                'matched': filtered_rows,
                'total_matched': total_rows_written
            })
        
        # Close progress bar
        progress_bar.close()
        
        print(f"\n✓ Successfully filtered {input_path.name} to {output_path.name}")
        print(f"  Total rows processed: {total_rows_processed:,}")
        print(f"  Rows written (matching filter): {total_rows_written:,}")
        print(f"  Columns: {num_columns}")
        
        if total_rows_written == 0:
            print(f"\n⚠ Warning: No rows found matching filter criteria: {filter_criteria}")
        
        return True
        
    except pd.errors.EmptyDataError:
        print(f"Error: The CSV file '{input_file}' is empty.", file=sys.stderr)
        return False
    except pd.errors.ParserError as e:
        print(f"Error: Failed to parse CSV file '{input_file}': {e}", file=sys.stderr)
        return False
    except PermissionError:
        print(f"Error: Permission denied when accessing files.", file=sys.stderr)
        return False
    except MemoryError:
        print(f"Error: Out of memory. Try using a smaller chunk size with --chunk-size.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}", file=sys.stderr)
        return False


def main():
    """Main function to handle command-line arguments and execute filtering."""
    parser = argparse.ArgumentParser(
        description='Filter a CSV file based on field=value criteria with OR (||) and AND (&&) logic support. Uses the same syntax as the main tool.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Filter for npm packages only
  %(prog)s --input data.csv --output npm_packages.csv --filter-packages "PackageRepository=npm"
  
  # Filter for both npm and nuget packages (OR logic)
  %(prog)s -i data.csv -o packages.csv --filter-packages "PackageRepository=npm||nuget"
  
  # Filter for packages with critical vulnerabilities
  %(prog)s -i data.csv -o critical.csv --filter-packages "CriticalVulnerabilityCount>0"
  
  # Filter for malicious packages
  %(prog)s -i data.csv -o malicious.csv --filter-packages "IsMalicious=true"
  
  # Filter for outdated packages
  %(prog)s -i data.csv -o outdated.csv --filter-packages "Outdated=true"
  
  # Custom chunk size for large files
  %(prog)s -i huge_file.csv -o filtered.csv --filter-packages "PackageRepository=npm" --chunk-size 100000

Filter Syntax:
  - Format: "field=value"
  - Use || for OR logic: "PackageRepository=npm||pypi" matches npm OR pypi packages
  - Use && for AND logic: "Name=react&&typescript" matches packages containing both terms
  - Case insensitive matching
  - No spaces around || and && operators
  - Handles string, boolean, and numeric columns

Common Use Cases:
  - Package repositories: --filter-packages "PackageRepository=npm||nuget||pypi"
  - Vulnerability counts: --filter-packages "CriticalVulnerabilityCount>0"
  - Package status: --filter-packages "Outdated=true"
  - Malicious packages: --filter-packages "IsMalicious=true"
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Path to the input CSV file'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Path to the output CSV file'
    )
    
    parser.add_argument(
        '--filter-packages',
        required=True,
        help='Filter criteria in format "field=value" with OR (||) and AND (&&) logic support. Examples: "PackageRepository=npm", "IsMalicious=true"'
    )
    
    parser.add_argument(
        '--chunk-size', '-c',
        type=int,
        default=50000,
        help='Number of rows to process at a time (default: 50000)'
    )
    
    args = parser.parse_args()
    
    # Validate chunk size
    if args.chunk_size < 1:
        print("Error: Chunk size must be at least 1.", file=sys.stderr)
        sys.exit(1)
    
    if args.chunk_size > 1000000:
        print("Warning: Very large chunk size may cause memory issues.", file=sys.stderr)
    
    # Perform filtering
    success = filter_csv(args.input, args.output, args.filter_packages, args.chunk_size)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
