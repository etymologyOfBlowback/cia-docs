#!/usr/bin/env python3
"""
Convert PNG files from a directory back into a PDF file.
Takes PNG page images and combines them into a single PDF.
"""

import sys
from pathlib import Path
from PIL import Image

def png_directory_to_pdf(png_dir, output_pdf):
    """
    Convert a directory of PNG page images back into a PDF file.
    
    Args:
        png_dir: Directory containing page_N.png files
        output_pdf: Output PDF file path
    """
    png_dir = Path(png_dir)
    
    if not png_dir.is_dir():
        print(f"Error: {png_dir} is not a directory")
        return False
    
    # Find all PNG files
    png_files = sorted(png_dir.glob('page_*.png'))
    
    if not png_files:
        print(f"Error: No PNG files found in {png_dir}")
        return False
    
    print(f"Found {len(png_files)} PNG files in {png_dir}")
    
    # Open all images
    images = []
    for png_file in png_files:
        try:
            img = Image.open(png_file)
            # Convert to RGB if needed (for grayscale or RGBA)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)
            print(f"  Loaded: {png_file.name}")
        except Exception as e:
            print(f"  Error loading {png_file.name}: {e}")
            return False
    
    if not images:
        print("Error: No images could be loaded")
        return False
    
    # Save as PDF
    try:
        output_pdf = Path(output_pdf)
        images[0].save(
            output_pdf,
            save_all=True,
            append_images=images[1:],
            optimize=False
        )
        print(f"Successfully created: {output_pdf}")
        return True
    except Exception as e:
        print(f"Error creating PDF: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: png_to_pdf.py <png_directory> [output.pdf]")
        print("Example: png_to_pdf.py iran-cia-main.7 iran-cia-main.7-unredacted.pdf")
        sys.exit(1)
    
    png_dir = sys.argv[1]
    
    # Generate output filename if not provided
    if len(sys.argv) > 2:
        output_pdf = sys.argv[2]
    else:
        # Use directory name with -unredacted suffix
        output_pdf = f"{Path(png_dir).name}-unredacted.pdf"
    
    success = png_directory_to_pdf(png_dir, output_pdf)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
