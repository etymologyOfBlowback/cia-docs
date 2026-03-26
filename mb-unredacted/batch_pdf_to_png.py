#!/usr/bin/env python3
"""
Batch extract all iran-cia-*.pdf files to PNG images.

Usage:
    python batch_pdf_to_png.py [directory]
    
If no directory is specified, processes all PDFs in current directory.

For each PDF file, creates:
    - inFile/ directory
    - inFile/page_1.png, inFile/page_2.png, ... (one for each page)
"""

import sys
from pathlib import Path
import subprocess


def batch_convert_pdfs(directory=None):
    """
    Batch convert all PDF files in a directory.
    
    Args:
        directory: Directory containing PDF files (default: current directory)
    """
    if directory is None:
        directory = Path.cwd()
    else:
        directory = Path(directory)
    
    if not directory.exists():
        print(f"✗ Error: Directory not found: {directory}")
        return False
    
    # Find all PDF files
    pdf_files = sorted(directory.glob('iran-cia-*.pdf'))
    
    if not pdf_files:
        print(f"✗ No iran-cia-*.pdf files found in: {directory}")
        return False
    
    print(f"Found {len(pdf_files)} PDF files to process\n")
    print("=" * 70)
    
    python_exe = sys.executable
    pdf_to_png_script = Path(__file__).parent / 'pdf_to_png.py'
    
    if not pdf_to_png_script.exists():
        print(f"✗ Error: pdf_to_png.py not found in {pdf_to_png_script.parent}")
        return False
    
    successful = 0
    failed = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
        print("-" * 70)
        
        try:
            result = subprocess.run(
                [python_exe, str(pdf_to_png_script), str(pdf_file)],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Print the output
                print(result.stdout)
                successful += 1
            else:
                print(f"✗ Failed to process {pdf_file.name}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                failed += 1
                
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout processing {pdf_file.name}")
            failed += 1
        except Exception as e:
            print(f"✗ Error processing {pdf_file.name}: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"\nSummary:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(pdf_files)}")
    
    if failed == 0:
        print(f"\n✓ All PDFs converted successfully!")
        return True
    else:
        print(f"\n⚠ Some PDFs failed to convert")
        return False


def main():
    """Main entry point."""
    directory = sys.argv[1] if len(sys.argv) > 1 else None
    success = batch_convert_pdfs(directory)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
