#!/usr/bin/env python3
"""
Generate LaTeX include files for Operation TPAJAX image pages.

Current scope:
- Target page format: 8.5x11 (uses \textwidth/\textheight of host document)
- Layout: 4-up images per LaTeX page (default)

Usage examples:
    python generate_tpajax_images_latex.py
    python generate_tpajax_images_latex.py --layouts 4
    python generate_tpajax_images_latex.py \
        --image-root /path/to/orig-files-proc \
        --output-dir /path/to/common

Outputs (by default):
    part_tpajax_images_8p5x11_4up.tex

Each output file contains only include content (no preamble), intended to be
input or included from part_tpajax_images.tex.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


PAGE_PATTERN = re.compile(r"page_(\d+)\.png$")


@dataclass(frozen=True)
class ImageItem:
    section_dir: Path
    page_path: Path
    page_number: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate LaTeX pages from TPAJAX PNG images (8.5x11, default 4-up)."
    )
    parser.add_argument(
        "--image-root",
        type=Path,
        default=Path(__file__).parent,
        help="Directory containing iran-cia-* image subdirectories (default: script directory).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Directory where generated .tex files are written (default: script directory).",
    )
    parser.add_argument(
        "--layouts",
        type=int,
        nargs="+",
        default=[4],
        help="Images per LaTeX page to generate (allowed values: 2, 4).",
    )
    parser.add_argument(
        "--path-prefix",
        type=str,
        default="orig-files-proc",
        help=(
            "Prefix prepended to image paths in LaTeX "
            "(default: orig-files-proc)."
        ),
    )
    return parser.parse_args()


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


def collect_images(image_root: Path) -> List[ImageItem]:
    section_dirs = [p for p in image_root.glob("iran-cia-*") if p.is_dir()]
    section_dirs.sort(key=lambda path: section_sort_key(path.name))

    items: List[ImageItem] = []
    for section_dir in section_dirs:
        page_paths = []
        for png in section_dir.glob("page_*.png"):
            match = PAGE_PATTERN.search(png.name)
            if not match:
                continue
            page_paths.append((int(match.group(1)), png))

        page_paths.sort(key=lambda pair: pair[0])
        for page_number, page_path in page_paths:
            items.append(
                ImageItem(
                    section_dir=section_dir,
                    page_path=page_path,
                    page_number=page_number,
                )
            )

    return items


def latex_escape_path(path_text: str) -> str:
    # Keep this minimal; most of our paths are safe for \includegraphics.
    return path_text.replace("\\", "/")


def image_path_for_latex(item: ImageItem, image_root: Path, path_prefix: str) -> str:
    rel_from_root = item.page_path.relative_to(image_root)
    if path_prefix:
        combined = Path(path_prefix) / rel_from_root
    else:
        combined = rel_from_root
    return latex_escape_path(str(combined))


def chunked(seq: Sequence[ImageItem], chunk_size: int) -> Iterable[List[ImageItem]]:
    for index in range(0, len(seq), chunk_size):
        yield list(seq[index : index + chunk_size])


def make_label(item: ImageItem) -> str:
    """Derive a stable \\label key directly from the image filename."""
    return f"img:{item.section_dir.name}:{item.page_path.stem}"


def render_cell(image_rel_path: str, fit_width: str, fit_height: str, label: str = "") -> str:
    prefix = f"\\phantomsection\\label{{{label}}}%\n" if label else ""
    return (
        prefix
        + f"\\includegraphics[width={fit_width},height={fit_height},keepaspectratio]"
        + f"{{{image_rel_path}}}"
    )


def render_page_2up(items: List[ImageItem], image_root: Path, path_prefix: str) -> List[str]:
    lines: List[str] = [
        "\\begin{center}",
    ]

    for index, item in enumerate(items):
        image_rel_path = image_path_for_latex(item, image_root, path_prefix)
        lines.append(render_cell(image_rel_path, "\\textwidth", "0.47\\textheight", make_label(item)))
        if index < len(items) - 1:
            lines.append("\\vfill")

    lines.extend(
        [
            "\\end{center}",
            "\\clearpage",
        ]
    )
    return lines


def render_page_4up(items: List[ImageItem], image_root: Path, path_prefix: str) -> List[str]:
    cells: List[str] = []
    for item in items:
        image_rel_path = image_path_for_latex(item, image_root, path_prefix)
        cells.append(render_cell(image_rel_path, "0.48\\textwidth", "0.45\\textheight", make_label(item)))

    # pad incomplete last page
    while len(cells) < 4:
        cells.append("\\mbox{}")

    lines: List[str] = [
        "\\begin{center}",
        "\\setlength{\\tabcolsep}{0pt}",
        "\\renewcommand{\\arraystretch}{1.0}",
        "\\begin{tabular}{|c|c|}",
        "\\hline",
        f"{cells[0]} & {cells[1]} \\\\\\hline",
        f"{cells[2]} & {cells[3]} \\\\\\hline",
        "\\end{tabular}",
        "\\end{center}",
        "\\clearpage",
    ]
    return lines


def generate_tex_content(
    items: List[ImageItem],
    layout: int,
    image_root: Path,
    path_prefix: str,
) -> str:
    lines: List[str] = [
        "% Auto-generated by generate_tpajax_images_latex.py",
        "% Target page size: 8.5x11 (host document geometry)",
        f"% Layout: {layout} images per LaTeX page",
        "%",
        "% Label format: img:<section-dir>:<stem>  e.g. img:iran-cia-intro:page_1",
        "% Use \\pageref{img:iran-cia-intro:page_1} to reference by PDF page number",
        "",
    ]

    renderer = render_page_2up if layout == 2 else render_page_4up

    for group in chunked(items, layout):
        lines.extend(renderer(group, image_root, path_prefix))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def validate_layouts(layouts: Sequence[int]) -> List[int]:
    valid = []
    for value in layouts:
        if value not in (2, 4):
            raise ValueError(f"Unsupported layout '{value}'. Allowed values are 2 or 4.")
        valid.append(value)
    return sorted(set(valid))


def main() -> int:
    args = parse_args()

    image_root = args.image_root.resolve()
    output_dir = args.output_dir.resolve()

    if not image_root.exists() or not image_root.is_dir():
        print(f"✗ Error: image root directory not found: {image_root}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        layouts = validate_layouts(args.layouts)
    except ValueError as error:
        print(f"✗ Error: {error}")
        return 1

    items = collect_images(image_root)
    if not items:
        print(f"✗ Error: no page_*.png files found under {image_root}/iran-cia-*")
        return 1

    print(f"Found {len(items)} images across iran-cia-* directories")

    for layout in layouts:
        output_file = output_dir / f"part_tpajax_images_8p5x11_{layout}up.tex"
        content = generate_tex_content(items, layout, image_root, args.path_prefix)
        output_file.write_text(content, encoding="utf-8")

        page_count = (len(items) + layout - 1) // layout
        print(f"✓ Wrote {output_file}")
        print(f"  - layout: {layout}-up")
        print(f"  - source images: {len(items)}")
        print(f"  - generated LaTeX pages: {page_count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
