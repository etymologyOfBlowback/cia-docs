#!/usr/bin/env python3
"""
Analyze redacted regions in PDF documents and create annotated PNG files.

This script:
1. Extracts redaction box coordinates from PDF structure
2. Creates annotated PNG files with red boxes marking redacted regions
3. Generates a CSV report with redaction statistics

Usage:
    python3 identify_redactions.py inFile.pdf
    
Or batch process:
    python3 identify_redactions.py *.pdf
    
Output:
    - inFile_redactions_marked.png (one per page with redactions)
    - inFile_redaction_report.csv (summary of all redactions)
"""

import sys
from pathlib import Path
import pdfplumber
from PIL import Image, ImageDraw, ImageFont
import io
import csv
from datetime import datetime


def extract_redaction_boxes(pdf_path):
    """
    Extract redaction box coordinates from PDF.
    
    Returns a dict: {page_number: [list of (x0, y0, x1, y1) coordinates]}
    """
    redactions = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # Get page info
            mediabox = page.mediabox
            # mediabox is a tuple: (x0, y0, x1, y1)
            page_width = mediabox[2] - mediabox[0]
            page_height = mediabox[3] - mediabox[1]
            
            # Extract rectangles (potential redaction boxes)
            rects = page.rects
            
            page_redactions = []
            
            for rect in rects:
                # Check if this looks like a redaction box
                # Redaction boxes are typically black (stroking_color=0 or non_stroking_color=0)
                # and have no outline (linewidth=0)
                x0 = rect['x0']
                y0 = rect['y0']
                x1 = rect['x1']
                y1 = rect['y1']
                width = x1 - x0
                height = y1 - y0
                area = width * height
                
                # Filter for black boxes
                # Black redactions: stroking_color or non_stroking_color = 0
                is_black = (
                    rect.get('stroking_color') == 0 or 
                    rect.get('non_stroking_color') == 0
                )
                
                # Has substantial size (not just a thin line)
                min_size = 100  # Minimum area in points squared
                
                if is_black and area > min_size:
                    page_redactions.append({
                        'x0': x0,
                        'y0': y0,
                        'x1': x1,
                        'y1': y1,
                        'width': width,
                        'height': height,
                        'area': area,
                        'page_width': page_width,
                        'page_height': page_height
                    })
            
            if page_redactions:
                redactions[page_num] = page_redactions
    
    return redactions


def extract_and_mark_pdf(pdf_path, output_dir=None):
    """
    Extract PDF pages as PNG and mark redacted regions.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save annotated images (default: current directory)
        
    Returns:
        (success: bool, redaction_data: dict)
    """
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"✗ Error: File not found: {pdf_path}")
        return False, {}
    
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(exist_ok=True)
    
    print(f"Processing: {pdf_file.name}")
    print(f"Output directory: {output_dir}\n")
    
    # Extract redaction coordinates
    redactions = extract_redaction_boxes(pdf_file)
    
    if not redactions:
        print("⚠ No redaction boxes detected in this PDF")
        return True, {}
    
    print(f"Found redactions on {len(redactions)} page(s)\n")
    
    # Store metadata for CSV report
    redaction_data = {
        'pdf_name': pdf_file.name,
        'timestamp': datetime.now().isoformat(),
        'pages_with_redactions': []
    }
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                if page_num not in redactions:
                    continue
                
                # Extract image
                if not page.images:
                    print(f"  Page {page_num}: No images found, skipping")
                    continue
                
                img_info = page.images[0]
                stream = img_info.get('stream')
                
                if not stream:
                    continue
                
                raw_data = stream.get_data()
                img = Image.open(io.BytesIO(raw_data))
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Get image dimensions
                img_width, img_height = img.size
                mediabox = page.mediabox
                pdf_width = mediabox[2] - mediabox[0]
                pdf_height = mediabox[3] - mediabox[1]
                
                # Create drawing context
                draw = ImageDraw.Draw(img, 'RGBA')
                
                # Mark redacted regions
                page_data = {
                    'page_num': page_num,
                    'image_size': (img_width, img_height),
                    'redactions': []
                }
                
                for rect in redactions[page_num]:
                    # Convert PDF coordinates to image coordinates
                    # PDF coordinates origin is bottom-left, image is top-left
                    pdf_x0, pdf_y0 = rect['x0'], rect['y0']
                    pdf_x1, pdf_y1 = rect['x1'], rect['y1']
                    
                    # Scale to image dimensions
                    img_x0 = int((pdf_x0 / pdf_width) * img_width)
                    img_x1 = int((pdf_x1 / pdf_width) * img_width)
                    img_y0 = int((1 - pdf_y1 / pdf_height) * img_height)
                    img_y1 = int((1 - pdf_y0 / pdf_height) * img_height)
                    
                    # Draw red box around redaction
                    # Red rectangle with semi-transparent fill
                    draw.rectangle(
                        [(img_x0, img_y0), (img_x1, img_y1)],
                        outline='red',
                        width=3,
                        fill=(255, 0, 0, 30)
                    )
                    
                    # Draw label with coordinates
                    label = f"REDACTED\n({img_x0},{img_y0})-({img_x1},{img_y1})"
                    label_y = img_y0 - 25 if img_y0 > 25 else img_y1 + 5
                    
                    try:
                        # Try to use a default font, fall back to default if not available
                        draw.text(
                            (img_x0 + 5, label_y),
                            label,
                            fill='red'
                        )
                    except:
                        pass  # Font not available, skip label
                    
                    # Store redaction data
                    redaction_width = img_x1 - img_x0
                    redaction_height = img_y1 - img_y0
                    redaction_area = redaction_width * redaction_height
                    page_area = img_width * img_height
                    percent_redacted = (redaction_area / page_area) * 100
                    
                    page_data['redactions'].append({
                        'x0': img_x0,
                        'y0': img_y0,
                        'x1': img_x1,
                        'y1': img_y1,
                        'width': redaction_width,
                        'height': redaction_height,
                        'area': redaction_area,
                        'percent': percent_redacted
                    })
                
                redaction_data['pages_with_redactions'].append(page_data)
                
                # Save annotated image
                output_filename = f"{pdf_file.stem}_page_{page_num}_redactions_marked.png"
                output_path = output_dir / output_filename
                img.save(output_path)
                
                # Print summary
                total_redaction_area = sum(r['area'] for r in page_data['redactions'])
                page_area = img_width * img_height
                percent = (total_redaction_area / page_area) * 100
                num_boxes = len(page_data['redactions'])
                
                print(f"  ✓ Page {page_num:3d}: {num_boxes} redaction box(es), {percent:5.1f}% of page")
                print(f"             Saved: {output_filename}")
        
        return True, redaction_data
        
    except Exception as e:
        print(f"✗ Error processing PDF: {e}")
        return False, redaction_data


def save_redaction_report(redaction_data, output_file):
    """
    Save redaction statistics to CSV file.
    """
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'PDF File',
            'Page Number',
            'Redaction Box #',
            'X0 (pixels)',
            'Y0 (pixels)',
            'X1 (pixels)',
            'Y1 (pixels)',
            'Width (pixels)',
            'Height (pixels)',
            'Area (pixels²)',
            'Percent of Page Redacted',
            'Total Boxes on Page',
            'Total Page Redaction %',
            'Image Size (WxH)',
            'Processing Time'
        ])
        
        # Data rows
        pdf_name = redaction_data.get('pdf_name', 'Unknown')
        timestamp = redaction_data.get('timestamp', 'Unknown')
        
        for page_data in redaction_data.get('pages_with_redactions', []):
            page_num = page_data['page_num']
            image_size = f"{page_data['image_size'][0]}x{page_data['image_size'][1]}"
            num_boxes = len(page_data['redactions'])
            total_page_redaction = sum(r['percent'] for r in page_data['redactions'])
            
            for box_num, redaction in enumerate(page_data['redactions'], 1):
                writer.writerow([
                    pdf_name,
                    page_num,
                    box_num,
                    redaction['x0'],
                    redaction['y0'],
                    redaction['x1'],
                    redaction['y1'],
                    redaction['width'],
                    redaction['height'],
                    int(redaction['area']),
                    f"{redaction['percent']:.1f}%",
                    num_boxes,
                    f"{total_page_redaction:.1f}%",
                    image_size,
                    timestamp
                ])


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 identify_redactions.py inFile.pdf [inFile2.pdf ...]")
        print()
        print("This will:")
        print("  1. Extract redaction box coordinates from PDF structure")
        print("  2. Create annotated PNG with red boxes marking redactions")
        print("  3. Generate CSV report with redaction statistics")
        sys.exit(1)
    
    pdf_files = [Path(arg) for arg in sys.argv[1:]]
    output_dir = Path.cwd()
    
    print(f"{'='*70}")
    print(f"REDACTION IDENTIFICATION TOOL")
    print(f"{'='*70}\n")
    
    all_redaction_data = []
    
    for pdf_path in pdf_files:
        success, redaction_data = extract_and_mark_pdf(pdf_path, output_dir)
        
        if success and redaction_data:
            all_redaction_data.append(redaction_data)
            
            # Save individual PDF report
            report_file = output_dir / f"{Path(pdf_path).stem}_redaction_report.csv"
            save_redaction_report(redaction_data, report_file)
            print(f"  Report: {report_file.name}\n")
        elif success:
            print(f"  No redactions found in this PDF\n")
        else:
            print(f"  Failed to process {pdf_path}\n")
    
    # Create combined report if multiple files
    if len(all_redaction_data) > 1:
        combined_report = output_dir / "all_redactions_report.csv"
        
        with open(combined_report, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Summary Report', f'Generated: {datetime.now().isoformat()}'])
            writer.writerow([])
            writer.writerow(['PDF File', 'Pages with Redactions', 'Total Redaction Boxes'])
            
            for data in all_redaction_data:
                num_pages = len(data['pages_with_redactions'])
                num_boxes = sum(
                    len(page['redactions']) 
                    for page in data['pages_with_redactions']
                )
                writer.writerow([data['pdf_name'], num_pages, num_boxes])
        
        print(f"{'='*70}")
        print(f"Combined report: {combined_report.name}")
        print(f"{'='*70}\n")
    
    print(f"✓ Complete!")


if __name__ == '__main__':
    main()
