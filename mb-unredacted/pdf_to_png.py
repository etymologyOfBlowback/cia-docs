#!/usr/bin/env python3
"""
Extract all pages from a PDF as PNG images.

Usage:
    python pdf_to_png.py inFile.pdf
    
This will create:
    - inFile/ directory
    - inFile/page_1.png, inFile/page_2.png, ... for each page
    
The PNG files can later be processed with OCR.
"""

import sys
from pathlib import Path
import pdfplumber
from PIL import Image
import io


def extract_pdf_to_png(pdf_path):
    """
    Extract all pages from a PDF as PNG images.
    
    Args:
        pdf_path: Path to input PDF file
        
    Returns:
        True if successful, False otherwise
    """
    pdf_file = Path(pdf_path)
    
    # Validate input file
    if not pdf_file.exists():
        print(f"✗ Error: File not found: {pdf_path}")
        return False
    
    if not pdf_file.suffix.lower() == '.pdf':
        print(f"✗ Error: File must be a PDF: {pdf_path}")
        return False
    
    # Create output directory (name without extension)
    output_dir = pdf_file.parent / pdf_file.stem
    output_dir.mkdir(exist_ok=True)
    
    print(f"Processing: {pdf_file.name}")
    print(f"Output directory: {output_dir}")
    print()
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            print(f"Total pages: {total_pages}\n")
            
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # Check if page has images
                    if page.images:
                        # Extract the first image from the page
                        img_info = page.images[0]
                        stream = img_info.get('stream')
                        
                        if stream:
                            # Get raw image data
                            raw_data = stream.get_data()
                            
                            # Open as image and convert to PNG
                            try:
                                img = Image.open(io.BytesIO(raw_data))
                                
                                # Convert to RGB if needed (for consistency)
                                if img.mode != 'RGB' and img.mode != 'L':
                                    img = img.convert('RGB')
                                
                                # Save as PNG
                                output_file = output_dir / f"page_{page_num}.png"
                                img.save(output_file)
                                
                                print(f"  ✓ Page {page_num:3d}: {output_file.name} ({img.size[0]}x{img.size[1]})")
                                
                            except Exception as e:
                                print(f"  ✗ Page {page_num:3d}: Error converting to PNG - {e}")
                        else:
                            print(f"  ✗ Page {page_num:3d}: No image stream found")
                    else:
                        print(f"  ✗ Page {page_num:3d}: No images on this page")
                        
                except Exception as e:
                    print(f"  ✗ Page {page_num:3d}: Error processing page - {e}")
        
        print(f"\n✓ Complete! PNG files saved to: {output_dir}")
        return True
        
    except Exception as e:
        print(f"✗ Error processing PDF: {e}")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_png.py inFile.pdf")
        print()
        print("This will create:")
        print("  - inFile/ directory")
        print("  - inFile/page_1.png, inFile/page_2.png, ... (one for each page)")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    success = extract_pdf_to_png(pdf_path)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
