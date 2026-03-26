#!/usr/bin/env python3
"""
Detect if a PDF or PNG file contains redacted content.
Output: Single line with filename, redaction status, stats.
"""

import pdfplumber
import cv2
import numpy as np
from pathlib import Path
import sys

def detect_redactions_in_pdf(pdf_path):
    """Detect redactions in a PDF by looking for black rectangles."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pages_with_redactions = 0
            total_boxes = 0
            
            for page_idx, page in enumerate(pdf.pages, 1):
                black_rects = 0
                if hasattr(page, 'rects'):
                    for rect in page.rects:
                        black_rects += 1
                
                if black_rects > 0:
                    pages_with_redactions += 1
                    total_boxes += black_rects
            
            if pages_with_redactions > 0:
                redaction_percentage = (pages_with_redactions / total_pages) * 100
                status = "REDACTIONS DETECTED"
                return {
                    'has_redactions': True,
                    'status': status,
                    'pages': pages_with_redactions,
                    'percentage': redaction_percentage,
                    'boxes': total_boxes
                }
            else:
                return {
                    'has_redactions': False,
                    'status': 'NO REDACTIONS',
                    'pages': 0,
                    'percentage': 0.0,
                    'boxes': 0
                }
            
    except Exception as e:
        return {
            'has_redactions': None,
            'error': str(e)
        }

def detect_redactions_in_png(png_path, threshold=50):
    """Detect redactions in a PNG by analyzing dark pixel regions."""
    try:
        img = cv2.imread(str(png_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {'has_redactions': None, 'error': 'Could not read PNG'}
        
        height, width = img.shape
        total_pixels = height * width
        
        dark_pixels = np.where(img < threshold)
        dark_count = len(dark_pixels[0])
        
        if dark_count > 0:
            binary_mask = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY_INV)[1]
            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            large_contours = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > (total_pixels * 0.001):
                    large_contours.append(area)
            
            if len(large_contours) > 0:
                dark_percentage = (dark_count / total_pixels) * 100
                return {
                    'has_redactions': True,
                    'status': 'REDACTIONS DETECTED',
                    'regions': len(large_contours),
                    'percentage': dark_percentage
                }
        
        return {
            'has_redactions': False,
            'status': 'NO REDACTIONS',
            'regions': 0,
            'percentage': 0.0
        }
        
    except Exception as e:
        return {
            'has_redactions': None,
            'error': str(e)
        }

def check_file(file_path):
    """Check if a file contains redactions."""
    path = Path(file_path)
    
    if not path.exists():
        return {
            'file': path.name,
            'error': 'File not found'
        }
    
    if path.suffix.lower() == '.pdf':
        result = detect_redactions_in_pdf(path)
        result['file'] = path.name
        result['file_type'] = 'PDF'
        return result
    
    elif path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tiff']:
        result = detect_redactions_in_png(path)
        result['file'] = path.name
        result['file_type'] = 'PNG'
        return result
    
    else:
        return {'file': path.name, 'error': f'Unsupported type: {path.suffix}'}

def format_result(result):
    """Format result as single-line output."""
    filename = result.get('file', 'Unknown')
    
    if 'error' in result:
        return f"{filename} -- ERROR: {result['error']}"
    
    file_type = result.get('file_type', '')
    status = result.get('status', 'UNKNOWN')
    
    if file_type == 'PDF':
        pages = result.get('pages', 0)
        percentage = result.get('percentage', 0)
        boxes = result.get('boxes', 0)
        
        if pages > 0:
            return f"{filename} -- {status} -- {pages} redacted pages, {percentage:.1f}% -- boxes={boxes}"
        else:
            return f"{filename} -- {status}"
    
    elif file_type == 'PNG':
        regions = result.get('regions', 0)
        percentage = result.get('percentage', 0)
        
        if regions > 0:
            return f"{filename} -- {status} -- {regions} regions, {percentage:.1f}%"
        else:
            return f"{filename} -- {status}"
    
    return f"{filename} -- {status}"

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 detect_redactions.py <file1.pdf> [file2.png] [...]")
        return
    
    files = sys.argv[1:]
    
    for file_arg in files:
        if '*' in file_arg:
            from glob import glob
            matching_files = glob(file_arg)
            if not matching_files:
                continue
            for f in sorted(matching_files):
                result = check_file(f)
                print(format_result(result))
        else:
            result = check_file(file_arg)
            print(format_result(result))

if __name__ == '__main__':
    main()
