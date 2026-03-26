#!/usr/bin/env python3
"""
Detect physical black redactions in PDFs and PNGs by finding large black rectangles.
Uses connected component analysis with smart filtering to identify rectangular redaction boxes.
Filters out decorative elements (thin lines, etc) by checking aspect ratio and minimum dimensions.
"""

import sys
import os
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
import pdfplumber

def find_black_rectangles_in_image(image_path, min_area=2500, min_size=30):
    """
    Find large black rectangles in an image using connected component analysis.
    Filters out thin lines and decorative elements using aspect ratio and minimum dimensions.
    
    Args:
        image_path: Path to image file
        min_area: Minimum area in pixels (default 2500 = 50x50 box)
        min_size: Minimum width AND height (filters out thin lines)
    
    Returns list of (x, y, w, h, area) tuples for actual redaction boxes.
    """
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return []
    
    # Threshold to find black regions (very dark pixels)
    # Black redactions are typically RGB(0,0,0) or very close
    _, black_mask = cv2.threshold(img, 30, 255, cv2.THRESH_BINARY_INV)
    
    # Find connected components
    num_labels, labels = cv2.connectedComponents(black_mask)
    
    rectangles = []
    
    # Analyze each connected component
    for label_id in range(1, num_labels):  # Skip background (0)
        component_mask = (labels == label_id).astype(np.uint8) * 255
        
        # Get bounding box
        contours, _ = cv2.findContours(component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            continue
        
        x, y, w, h = cv2.boundingRect(contours[0])
        area = w * h
        
        # Filter 1: Minimum area (eliminates small noise)
        if area < min_area:
            continue
        
        # Filter 2: Minimum dimensions (eliminates thin lines)
        # Both width AND height must be reasonable
        if w < min_size or h < min_size:
            continue
        
        # Filter 3: Aspect ratio (redactions should be roughly square or rectangular, not extremely thin)
        aspect_ratio = max(w, h) / min(w, h)
        if aspect_ratio > 10:  # Too elongated = likely a decorative line
            continue
        
        rectangles.append((x, y, w, h, area))
    
    return rectangles

def find_black_rectangles_in_image_cv(gray_image, min_area=2500, min_size=30):
    """
    Find large black rectangles in OpenCV grayscale image with smart filtering.
    """
    # Threshold to find black regions
    _, black_mask = cv2.threshold(gray_image, 30, 255, cv2.THRESH_BINARY_INV)
    
    # Find connected components
    num_labels, labels = cv2.connectedComponents(black_mask)
    
    rectangles = []
    
    for label_id in range(1, num_labels):
        component_mask = (labels == label_id).astype(np.uint8) * 255
        
        contours, _ = cv2.findContours(component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            continue
        
        x, y, w, h = cv2.boundingRect(contours[0])
        area = w * h
        
        # Filter 1: Minimum area
        if area < min_area:
            continue
        
        # Filter 2: Minimum dimensions
        if w < min_size or h < min_size:
            continue
        
        # Filter 3: Aspect ratio
        aspect_ratio = max(w, h) / min(w, h)
        if aspect_ratio > 10:
            continue
        
        rectangles.append((x, y, w, h, area))
    
    return rectangles

def analyze_png_directory(png_dir):
    """
    Analyze a directory of PNG files for black rectangles.
    """
    png_dir = Path(png_dir)
    if not png_dir.is_dir():
        return False, None
    
    png_files = sorted(png_dir.glob('page_*.png'))
    if not png_files:
        return False, None
    
    total_redactions = 0
    pages_with_redactions = 0
    
    for png_file in png_files:
        rectangles = find_black_rectangles_in_image(png_file, min_area=2500, min_size=30)
        
        if rectangles:
            pages_with_redactions += 1
            total_redactions += len(rectangles)
    
    num_pages = len(png_files)
    
    if pages_with_redactions == 0:
        return False, None
    
    percentage = (pages_with_redactions / num_pages) * 100
    return True, {
        'pages': pages_with_redactions,
        'total_pages': num_pages,
        'percentage': percentage,
        'boxes': total_redactions
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: detect_blackRedactions.py <png_dir_path> [...]")
        sys.exit(1)
    
    for arg in sys.argv[1:]:
        path = Path(arg)
        
        if path.is_dir():
            # PNG directory
            has_redactions, stats = analyze_png_directory(path)
            filename = path.name
        else:
            continue
        
        if has_redactions is None:
            status = "ERROR"
            output = f"{filename} -- {status}"
        elif has_redactions:
            status = "BLACK REDACTIONS FOUND"
            pages = stats['pages']
            total = stats['total_pages']
            pct = stats['percentage']
            boxes = stats['boxes']
            output = f"{filename} -- {status} -- {pages}/{total} pages, {pct:.1f}% -- boxes={boxes}"
        else:
            status = "NO BLACK REDACTIONS"
            output = f"{filename} -- {status}"
        
        print(output)

if __name__ == '__main__':
    main()
