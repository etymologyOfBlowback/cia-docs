#!/usr/bin/env python3
"""
Run OCR on page PNG files and write sidecar text files next to each image.

Default target set:
    iran-cia-*/page_*.png

For each image such as:
    iran-cia-main.3/page_7.png
this script writes:
    iran-cia-main.3/page_7.ocr.txt

Usage examples:
    python batch_png_ocr.py
    python batch_png_ocr.py --limit 10
    python batch_png_ocr.py --pattern 'iran-cia-main.3/page_*.png' --overwrite
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List


PAGE_PATTERN = re.compile(r"page_(\d+)\.png$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OCR iran-cia page PNG files into sidecar .ocr.txt files."
    )
    parser.add_argument(
        "--image-root",
        type=Path,
        default=Path(__file__).parent,
        help="Root directory to scan (default: script directory).",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="iran-cia-*/page_*.png",
        help="Glob pattern under --image-root (default: iran-cia-*/page_*.png).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max number of images to process (0 means all).",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="eng",
        help="Tesseract language(s), e.g. eng or eng+fas (default: eng).",
    )
    parser.add_argument(
        "--psm",
        type=int,
        default=6,
        help="Tesseract page segmentation mode (default: 6).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .ocr.txt files.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimize per-file progress output.",
    )
    return parser.parse_args()


def ensure_tesseract_available() -> bool:
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("✗ Error: tesseract not found in PATH")
        return False

    if result.returncode != 0:
        print("✗ Error: failed to execute tesseract --version")
        return False

    version_line = result.stdout.splitlines()[0] if result.stdout else "tesseract"
    print(f"Using OCR engine: {version_line}")
    return True


def collect_images(image_root: Path, pattern: str, limit: int) -> List[Path]:
    paths = [path for path in image_root.glob(pattern) if path.is_file()]

    def image_sort_key(path: Path) -> tuple[str, int, str]:
        rel = path.relative_to(image_root)
        section_name = rel.parent.as_posix()
        match = PAGE_PATTERN.search(path.name)
        page_number = int(match.group(1)) if match else 10**9
        return (section_name, page_number, path.name)

    paths.sort(key=image_sort_key)

    if limit > 0:
        paths = paths[:limit]

    return paths


def sidecar_path_for(image_path: Path) -> Path:
    return image_path.with_suffix(".ocr.txt")


def run_ocr(image_path: Path, sidecar_path: Path, lang: str, psm: int) -> tuple[bool, str]:
    # tesseract writes to <output_base>.txt, so pass output base without extension.
    output_base = sidecar_path.parent / sidecar_path.stem

    cmd = [
        "tesseract",
        str(image_path),
        str(output_base),
        "-l",
        lang,
        "--psm",
        str(psm),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        error_text = result.stderr.strip() or result.stdout.strip() or "unknown error"
        return False, error_text

    if not sidecar_path.exists():
        return False, "tesseract completed but output text file not found"

    return True, ""


def main() -> int:
    args = parse_args()

    image_root = args.image_root.resolve()
    if not image_root.exists() or not image_root.is_dir():
        print(f"✗ Error: image root directory not found: {image_root}")
        return 1

    if not ensure_tesseract_available():
        return 1

    images = collect_images(image_root, args.pattern, args.limit)
    if not images:
        print(f"✗ Error: no images found for pattern '{args.pattern}' under {image_root}")
        return 1

    print(f"Found {len(images)} images to OCR")
    print(f"Pattern: {args.pattern}")
    print(f"Image root: {image_root}")
    print(f"Language: {args.lang}  PSM: {args.psm}")
    print()

    processed = 0
    skipped = 0
    failed = 0

    for index, image_path in enumerate(images, 1):
        sidecar = sidecar_path_for(image_path)

        if sidecar.exists() and not args.overwrite:
            skipped += 1
            if not args.quiet:
                print(f"[{index}/{len(images)}] - skip: {image_path.relative_to(image_root)} (exists)")
            continue

        ok, error_text = run_ocr(image_path, sidecar, args.lang, args.psm)
        if ok:
            processed += 1
            if not args.quiet:
                print(f"[{index}/{len(images)}] + ocr : {image_path.relative_to(image_root)} -> {sidecar.name}")
        else:
            failed += 1
            print(f"[{index}/{len(images)}] ✗ fail: {image_path.relative_to(image_root)}")
            print(f"             {error_text}")

    print()
    print("Summary:")
    print(f"  Processed: {processed}")
    print(f"  Skipped:   {skipped}")
    print(f"  Failed:    {failed}")
    print(f"  Total:     {len(images)}")

    if failed > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
