#!/usr/bin/env python3
"""
Part 1: iran-cia-images-list.py

Iran-CIA specific image lister.
Scans for iran-cia-* directories, collects page_*.png files,
sorts by iran-cia canonical order, and outputs paths with
orig-files-proc/ prefix.

Output format: plain text, one path per line
  orig-files-proc/iran-cia-intro/page_1.png
  orig-files-proc/iran-cia-intro/page_2.png
  ...

Can be piped to images-list-to4up-latex.py:
  iran-cia-images-list.py | images-list-to4up-latex.py > output.tex

Usage:
  python iran-cia-images-list.py
  python iran-cia-images-list.py --output list.txt
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


PAGE_PATTERN = re.compile(r"page_(\d+)\.png$")


def section_sort_key(section_name: str) -> Tuple[int, int, str]:
    """
    Canonical order for iran-cia sections:
      1) iran-cia-intro
      2) iran-cia-summary
      3) iran-cia-main.1 ... iran-cia-main.10
      4) iran-cia-appendix-a ... iran-cia-appendix-e
      5) everything else (lexical)
    """
    if section_name == "iran-cia-intro":
        return (1, 0, section_name)
    if section_name == "iran-cia-summary":
        return (2, 0, section_name)

    match_main = re.match(r"iran-cia-main\.(\d+)$", section_name)
    if match_main:
        return (3, int(match_main.group(1)), section_name)

    match_appendix = re.match(r"iran-cia-appendix-([a-z])$", section_name)
    if match_appendix:
        letter_index = ord(match_appendix.group(1)) - ord("a") + 1
        return (4, letter_index, section_name)

    return (9, 0, section_name)


def collect_images(image_root: Path) -> List[str]:
    """
    Collect iran-cia images in canonical order.
    Returns list of paths like: orig-files-proc/iran-cia-intro/page_1.png
    """
    section_dirs = [p for p in image_root.glob("iran-cia-*") if p.is_dir()]
    section_dirs.sort(key=lambda path: section_sort_key(path.name))

    paths: List[str] = []
    for section_dir in section_dirs:
        page_paths = []
        for png in section_dir.glob("page_*.png"):
            match = PAGE_PATTERN.search(png.name)
            if not match:
                continue
            page_paths.append((int(match.group(1)), png))

        page_paths.sort(key=lambda pair: pair[0])
        for page_number, page_path in page_paths:
            rel_path = page_path.relative_to(image_root)
            path_with_prefix = f"orig-files-proc/{rel_path}"
            paths.append(path_with_prefix)

    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List iran-cia images in canonical order with orig-files-proc prefix."
    )
    parser.add_argument(
        "--image-root",
        type=Path,
        default=Path(__file__).parent,
        help="Directory containing iran-cia-* image subdirectories (default: script directory).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file (default: stdout).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    image_root = args.image_root.resolve()
    if not image_root.exists() or not image_root.is_dir():
        print(f"✗ Error: image root directory not found: {image_root}", file=sys.stderr)
        return 1

    paths = collect_images(image_root)
    if not paths:
        print(f"✗ Error: no page_*.png files found under {image_root}/iran-cia-*", file=sys.stderr)
        return 1

    output_text = "\n".join(paths) + "\n"

    if args.output:
        output_file = Path(args.output)
        output_file.write_text(output_text, encoding="utf-8")
        print(f"✓ Wrote {len(paths)} image paths to {output_file}", file=sys.stderr)
    else:
        sys.stdout.write(output_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
