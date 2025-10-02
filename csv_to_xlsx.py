#!/usr/bin/env python3
"""
CSV to XLSX Converter
Converts a CSV file to Excel (.xlsx) format using chunk-based processing for large files.
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import tqdm

# Excel row limit (1,048,576 rows including header)
EXCEL_MAX_ROWS = 1048576


def convert_csv_to_xlsx(input_file, output_file, chunk_size=50000):
    """
    Convert a CSV file to XLSX format using chunk-based processing.
    
    Args:
        input_file (str): Path to the input CSV file
        output_file (str): Path to the output XLSX file
        chunk_size (int): Number of rows to process at a time (default: 50000)
        
    Returns:
        bool: True if conversion successful, False otherwise
    """
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
        
        # Ensure output has .xlsx extension
        if output_path.suffix.lower() != '.xlsx':
            output_path = output_path.with_suffix('.xlsx')
            print(f"Note: Adding .xlsx extension to output file: {output_path}")
        
        print(f"Processing CSV in chunks of {chunk_size:,} rows...")
        print(f"Reading from: {input_path}")
        print(f"Writing to: {output_path}")
        print()
        
        # Create workbook and worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Data"
        
        total_rows = 0
        num_columns = 0
        header_written = False
        chunk_num = 0
        
        # Create progress bar
        progress_bar = tqdm.tqdm(
            total=data_rows,
            desc="Converting to Excel",
            unit="rows",
            unit_scale=True,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
        
        # Process CSV in chunks
        for chunk in pd.read_csv(str(input_path), chunksize=chunk_size, low_memory=False):
            chunk_num += 1
            chunk_rows = len(chunk)
            
            # Check if we'll exceed Excel's row limit
            if total_rows + chunk_rows + 1 > EXCEL_MAX_ROWS:  # +1 for header
                rows_remaining = EXCEL_MAX_ROWS - total_rows - 1
                if rows_remaining > 0:
                    progress_bar.close()
                    print(f"\nWarning: Excel row limit ({EXCEL_MAX_ROWS:,}) will be exceeded!")
                    print(f"Processing only {rows_remaining:,} more rows from this chunk.")
                    chunk = chunk.head(rows_remaining)
                    chunk_rows = len(chunk)
                else:
                    progress_bar.close()
                    print(f"\nWarning: Reached Excel's maximum row limit ({EXCEL_MAX_ROWS:,}).")
                    print(f"Stopping at {total_rows:,} rows. Remaining data will not be converted.")
                    break
            
            # Write header on first chunk
            if not header_written:
                num_columns = len(chunk.columns)
                for r_idx, row in enumerate(dataframe_to_rows(chunk, index=False, header=True), 1):
                    ws.append(row)
                    if r_idx == 1:  # Header row
                        header_written = True
                total_rows += chunk_rows
            else:
                # Write data rows only (skip header)
                for row in dataframe_to_rows(chunk, index=False, header=False):
                    ws.append(row)
                total_rows += chunk_rows
            
            # Update progress bar
            progress_bar.update(chunk_rows)
            progress_bar.set_postfix({
                'chunk': chunk_num,
                'total_rows': total_rows
            })
            
            # Stop if we've hit the Excel limit
            if total_rows + 1 >= EXCEL_MAX_ROWS:
                break
        
        # Close progress bar
        progress_bar.close()
        
        # Save the workbook
        print(f"Saving Excel file...")
        wb.save(str(output_path))
        
        print(f"\n✓ Successfully converted {input_path.name} to {output_path.name}")
        print(f"  Rows: {total_rows:,}")
        print(f"  Columns: {num_columns}")
        
        if total_rows >= EXCEL_MAX_ROWS - 1:
            print(f"\n⚠ Warning: Excel row limit reached. Some data may not have been converted.")
        
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
    """Main function to handle command-line arguments and execute conversion."""
    parser = argparse.ArgumentParser(
        description='Convert a CSV file to XLSX (Excel) format using chunk-based processing.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input data.csv --output data.xlsx
  %(prog)s -i input.csv -o output.xlsx
  %(prog)s -i large_file.csv -o output.xlsx --chunk-size 100000
  
Notes:
  - Excel has a maximum of 1,048,576 rows per worksheet
  - For files larger than this, excess rows will be truncated
  - Larger chunk sizes use more memory but may be faster
  - Smaller chunk sizes use less memory but may be slower
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
        help='Path to the output XLSX file'
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
    
    # Perform conversion
    success = convert_csv_to_xlsx(args.input, args.output, args.chunk_size)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

