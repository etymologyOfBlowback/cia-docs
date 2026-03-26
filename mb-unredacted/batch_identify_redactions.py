#!/usr/bin/env python3
"""
Batch identify redactions in all iran-cia-*.pdf files.

Usage:
    python3 batch_identify_redactions.py [directory]
    
If no directory is specified, processes all PDFs in current directory.

Output:
    - inFile_page_N_redactions_marked.png (for each page with redactions)
    - inFile_redaction_report.csv (for each PDF)
    - all_redactions_report.csv (combined summary)
"""

import sys
from pathlib import Path
import subprocess


def batch_identify_redactions(directory=None):
    """
    Batch identify redactions in all PDF files.
    
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
    
    print(f"{'='*70}")
    print(f"BATCH REDACTION IDENTIFICATION")
    print(f"{'='*70}\n")
    print(f"Found {len(pdf_files)} PDF files to process\n")
    
    python_exe = sys.executable
    script_file = Path(__file__).parent / 'identify_redactions.py'
    
    if not script_file.exists():
        print(f"✗ Error: identify_redactions.py not found")
        return False
    
    successful = 0
    failed = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
        print("-" * 70)
        
        try:
            result = subprocess.run(
                [python_exe, str(script_file), str(pdf_file)],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
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
    print(f"Summary:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(pdf_files)}")
    print(f"{'='*70}\n")
    
    if failed == 0:
        print(f"✓ All PDFs processed successfully!")
        print(f"\nOutput files created:")
        print(f"  - inFile_page_N_redactions_marked.png (annotated pages)")
        print(f"  - inFile_redaction_report.csv (per-PDF report)")
        return True
    else:
        print(f"⚠ Some PDFs failed to process")
        return False


def main():
    """Main entry point."""
    directory = sys.argv[1] if len(sys.argv) > 1 else None
    success = batch_identify_redactions(directory)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
