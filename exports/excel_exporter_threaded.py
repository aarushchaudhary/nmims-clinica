"""
exports/excel_exporter.py
--------------------------
All Excel export logic using openpyxl. Moved to QThread to prevent UI blocking.
Streams data dynamically in chunks.
"""

import os
from datetime import date, datetime
from typing import Optional

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter

from PySide6.QtCore import QThread, Signal

# ── DB query functions ────────────────────────────────────────────────────────
from database.db_manager      import get_connection

# ─────────────────────────────────────────────────────────────────────────────
#  DEFAULT OUTPUT DIRECTORY
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_EXPORT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "ClinicExports")

def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path

def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _output_path(filename: str, export_dir: str = None) -> str:
    directory = export_dir or DEFAULT_EXPORT_DIR
    _ensure_dir(directory)
    return os.path.join(directory, filename)

# ─────────────────────────────────────────────────────────────────────────────
#  STYLE CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

FONT_NAME = "Arial"
HEADER_FONT       = Font(name=FONT_NAME, bold=True, color="FFFFFF", size=10)
HEADER_FILL_BLUE  = PatternFill("solid", fgColor="0F4C81")
DATA_FONT         = Font(name=FONT_NAME, size=10)
ALT_FILL          = PatternFill("solid", fgColor="F8FAFC")
TITLE_FONT        = Font(name=FONT_NAME, bold=True, size=13, color="0F172A")
SUBTITLE_FONT     = Font(name=FONT_NAME, size=10, color="64748B")
CENTER_ALIGN      = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_ALIGN        = Alignment(horizontal="left",   vertical="center", wrap_text=True)
THIN_BORDER_SIDE  = Side(style="thin", color="E2E8F0")
THIN_BORDER       = Border(
    left=THIN_BORDER_SIDE, right=THIN_BORDER_SIDE,
    top=THIN_BORDER_SIDE,  bottom=THIN_BORDER_SIDE
)

class BaseExportThread(QThread):
    progress = Signal(int, str)  # percentage, message
    finished = Signal(str)       # file_path
    error = Signal(str)          # error message

    def __init__(self, export_dir=None):
        super().__init__()
        self.export_dir = export_dir
        self.chunk_size = 1000

    def _write_title_block(self, ws, title: str, subtitle: str, col_count: int):
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_count)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=col_count)
        t_cell = ws.cell(row=1, column=1, value=title)
        t_cell.font, t_cell.alignment, t_cell.fill = TITLE_FONT, LEFT_ALIGN, PatternFill("solid", fgColor="E0F2FE")
        s_cell = ws.cell(row=2, column=1, value=subtitle)
        s_cell.font, s_cell.alignment = SUBTITLE_FONT, LEFT_ALIGN
        ws.row_dimensions[1].height, ws.row_dimensions[2].height = 24, 16

    def _write_headers(self, ws, headers, row, fill):
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font, cell.fill, cell.alignment, cell.border = HEADER_FONT, fill, CENTER_ALIGN, THIN_BORDER
        ws.row_dimensions[row].height = 20

    def _autofit_columns(self, ws):
        for col_cells in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col_cells[0].column)
            for cell in col_cells:
                try:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                except Exception:
                    pass
            ws.column_dimensions[col_letter].width = max(10, min(max_len + 4, 50))


class ExportPatientsThread(BaseExportThread):
    def __init__(self, patient_type=None, export_dir=None):
        super().__init__(export_dir)
        self.patient_type = patient_type

    def run(self):
        conn = None
        try:
            self.progress.emit(0, "Initializing database...")
            conn = get_connection()
            
            # Count total
            count_query = "SELECT COUNT(*) FROM patients"
            params = []
            if self.patient_type:
                count_query += " WHERE type = ?"
                params.append(self.patient_type)
                
            total = conn.execute(count_query, params).fetchone()[0]
            if total == 0:
                self.error.emit("No patients found to export.")
                return

            self.progress.emit(5, f"Found {total} patients. Creating workbook...")
            wb = Workbook()
            ws = wb.active
            ws.title = "Patients"

            headers = ["ID", "SAP ID", "Name", "Type", "School", "Age", "Gender", "Blood Group", "Mobile", "Address", "Registered On"]
            
            label = self.patient_type or "All"
            self._write_title_block(ws, f"Patient Register — {label}", f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}  |  Total: {total}", len(headers))
            self._write_headers(ws, headers, row=3, fill=HEADER_FILL_BLUE)
            ws.freeze_panes = ws.cell(row=4, column=1)

            # Query data in chunks
            query = "SELECT id, sap_id, name, type, school, age, gender, blood_group, mobile, address, created_at FROM patients"
            if self.patient_type:
                query += " WHERE type = ?"
                
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            current_row = 4
            processed = 0
            
            while True:
                chunk = cursor.fetchmany(self.chunk_size)
                if not chunk:
                    break
                    
                for row in chunk:
                    for col, val in enumerate(row, start=1):
                        cell = ws.cell(row=current_row, column=col, value=val)
                        cell.font, cell.alignment, cell.border = DATA_FONT, LEFT_ALIGN, THIN_BORDER
                        if (current_row - 4) % 2 == 0:
                            cell.fill = ALT_FILL
                    current_row += 1
                    processed += 1
                    
                pct = int(5 + (processed / total) * 85)
                self.progress.emit(pct, f"Exported {processed}/{total} patients...")

            self.progress.emit(90, "Formatting columns...")
            self._autofit_columns(ws)
            ws.sheet_view.showGridLines = False

            self.progress.emit(95, "Saving file...")
            filename = f"Patients_{label}_{_timestamp()}.xlsx"
            path = _output_path(filename, self.export_dir)
            wb.save(path)
            
            self.progress.emit(100, "Done!")
            self.finished.emit(path)
            
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if conn:
                conn.close()
