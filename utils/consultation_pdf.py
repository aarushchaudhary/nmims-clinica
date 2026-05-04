"""
consultation_pdf.py
-------------------
PyMuPDF helper for exporting a consultation note to PDF.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os

import fitz


def _line(page, x0, y0, x1, y1, color=(0, 0, 0), width=1):
    page.draw_line(fitz.Point(x0, y0), fitz.Point(x1, y1), color=color, width=width)


def _safe_text(value) -> str:
    return "" if value is None else str(value).strip()


def _windows_font_path(filename: str) -> str | None:
    fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    font_path = fonts_dir / filename
    return str(font_path) if font_path.exists() else None


def _wrap_lines(text: str, max_chars: int) -> list[str]:
    words = _safe_text(text).split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def export_consultation_pdf(
    output_path: str | Path,
    *,
    patient_name: str,
    age: str | int | None,
    sex: str,
    sap_id: str,
    phone: str,
    date_text: str,
    complaints: str,
    diagnosis: str,
) -> str:
    """Create a one-page consultation PDF and return the saved path."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()
    page = doc.new_page(width=842, height=595)  # landscape A4

    margin_x = 32
    page_width = page.rect.width
    page_height = page.rect.height
    center_x = page_width / 2

    regular_fontfile = _windows_font_path("segoeui.ttf")
    bold_fontfile = _windows_font_path("segoeuib.ttf") or regular_fontfile
    rx_fontfile = _windows_font_path("timesbd.ttf") or bold_fontfile

    # Header block
    header_y = 28
    header_items = [
        f"Name: {_safe_text(patient_name)}",
        f"Age: {_safe_text(age) or '—'}",
        f"Sex: {_safe_text(sex) or '—'}",
        f"SAP ID: {_safe_text(sap_id) or '—'}",
        f"Phone: {_safe_text(phone) or '—'}",
    ]
    header_xs = [32, 230, 305, 390, 560]
    for x, item in zip(header_xs, header_items, strict=False):
        if bold_fontfile:
            page.insert_text((x, header_y), item, fontfile=bold_fontfile, fontsize=12.5, color=(0, 0, 0))
        else:
            page.insert_text((x, header_y), item, fontname="helv", fontsize=12.5, color=(0, 0, 0))

    # Divider below header
    _line(page, margin_x, 52, page_width - margin_x, 52, width=1.2)

    # Date row and central divider start just below the line
    date_value = f"Date: {_safe_text(date_text) or datetime.now().strftime('%d-%b-%Y')}"
    if bold_fontfile:
        page.insert_text((margin_x, 74), date_value, fontfile=bold_fontfile, fontsize=12)
    else:
        page.insert_text((margin_x, 74), date_value, fontname="helv", fontsize=12)
    _line(page, center_x, 64, center_x, page_height - 34, width=1)

    # Rx symbol on right side
    if rx_fontfile:
        page.insert_text((page_width - 118, 82), "Rx", fontfile=rx_fontfile, fontsize=34, color=(0, 0, 0))
    else:
        page.insert_text((page_width - 118, 82), "Rx", fontname="helv", fontsize=34, color=(0, 0, 0))

    left_x = margin_x
    right_x = center_x + 18
    content_top = 112

    if bold_fontfile:
        page.insert_text((left_x, content_top), "Complaints", fontfile=bold_fontfile, fontsize=14)
        page.insert_text((right_x, content_top), "Diagnosis", fontfile=bold_fontfile, fontsize=14)
    else:
        page.insert_text((left_x, content_top), "Complaints", fontname="helv", fontsize=14)
        page.insert_text((right_x, content_top), "Diagnosis", fontname="helv", fontsize=14)

    # Leave blank space in left column for handwritten additions.
    y = content_top + 120
    _line(page, left_x, y, center_x - 20, y, color=(0.75, 0.75, 0.75), width=0.7)

    # Leave blank space in right column for handwritten additions.
    y2 = content_top + 120
    _line(page, right_x, y2, page_width - margin_x, y2, color=(0.75, 0.75, 0.75), width=0.7)

    doc.save(str(output_path))
    doc.close()
    return str(output_path)