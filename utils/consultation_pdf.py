"""
consultation_pdf.py
-------------------
PyMuPDF helper for exporting a consultation note to PDF in a 3-page format.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
import os
import sys
import fitz

def _find_asset(filename: str) -> Path | None:
    """Resolve asset paths reliably across dev environments and PyInstaller bundles."""
    candidates = [
        Path(__file__).resolve().parents[1] / "assets" / filename,
        Path.cwd() / "assets" / filename,
        Path.cwd() / filename,
    ]
    if getattr(sys, 'frozen', False):
        base = Path(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))
        candidates.insert(0, base / "assets" / filename)
        candidates.insert(1, base / filename)
    for c in candidates:
        if c.exists():
            return c
    return None

def _line(page, x0, y0, x1, y1, color=(0.7, 0.7, 0.7), width=0.8):
    page.draw_line(fitz.Point(x0, y0), fitz.Point(x1, y1), color=color, width=width)

def _rect(page, rect, color=(0.7, 0.7, 0.7), fill=None, width=0.8):
    page.draw_rect(rect, color=color, fill=fill, width=width)

def _safe_text(value) -> str:
    return "" if value is None else str(value).strip()

def _val_or_dots(val, dots_count=20) -> str:
    cleaned = _safe_text(val)
    if not cleaned:
        return "." * dots_count
    return cleaned

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

def _text(page, x, y, text, fontname="helv", fontsize=9.5, color=(0.1, 0.1, 0.1), bold=False):
    fname = "hebo" if bold else "helv"
    page.insert_text(fitz.Point(x, y), str(text), fontname=fname, fontsize=fontsize, color=color)

def _textbox(page, rect, text, fontname="helv", fontsize=9.5, color=(0.1, 0.1, 0.1), bold=False, align=0):
    fname = "hebo" if bold else "helv"
    page.insert_textbox(rect, str(text), fontname=fname, fontsize=fontsize, color=color, align=align)

def _draw_header_footer(page, left_logo_path, right_logo_path, page_num):
    # Left logo: SVKM's NMIMS
    if left_logo_path and Path(left_logo_path).exists():
        page.insert_image(fitz.Rect(40, 15, 250, 94), filename=str(left_logo_path))
    else:
        _text(page, 40, 35, "SVKM'S", fontsize=10, bold=True, color=(0.725, 0.11, 0.11))
        _text(page, 40, 50, "NMIMS", fontsize=15, bold=True, color=(0.1, 0.1, 0.1))
        _text(page, 40, 60, "Deemed to be UNIVERSITY", fontsize=7.5, color=(0.4, 0.4, 0.4))

    # Right logo placeholder: SUNRIDGES HEALTH XI
    if right_logo_path and Path(right_logo_path).exists():
        page.insert_image(fitz.Rect(340, 15, 550, 103), filename=str(right_logo_path))
    else:
        _text(page, 435, 35, "Inspired Healthcare", fontsize=7.5, color=(0.4, 0.4, 0.4))
        _text(page, 435, 48, "SUNRIDGES", fontsize=12, bold=True, color=(0.1, 0.3, 0.6))
        _text(page, 435, 60, "HEALTH XI", fontsize=10, bold=True, color=(0.1, 0.3, 0.6))

    # Decorative bottom bar (NMIMS red)
    page.draw_rect(fitz.Rect(0, 825, 595, 842), color=(0.725, 0.11, 0.11), fill=(0.725, 0.11, 0.11), width=0)

    # Footer texts
    _text(page, 40, 785, "SVKM's", fontsize=9.5, bold=True, color=(0.1, 0.1, 0.1))
    _text(page, 40, 798, "Narsee Monjee Institute of Management Studies, Hyderabad", fontsize=11.5, bold=True, color=(0.725, 0.11, 0.11))
    _text(page, 40, 810, "Deemed to be UNIVERSITY", fontsize=8.5, color=(0.3, 0.3, 0.3))
    _textbox(page, fitz.Rect(40, 814, 555, 825), 
              "Jadcherla Campus: Plot No.- B4, Green Industrial Park, TSIIC, Polepally SEZ, Jadcherla, Mahabubnagar District, Telangana - 509301. India. Ph: 08542350062",
              fontsize=8, color=(0.4, 0.4, 0.4))

def export_consultation_pdf(
    output_path: str | Path,
    patient: dict,
    visit: dict = None,
    only_prescription_page: bool | None = None,
) -> str:
    """
    Create consultation PDF.
    - First prescription / 1st visit: 3-page format (Case Paper + Physical Exam + Prescription).
    - Subsequent prescriptions / 2nd+ visits: 1-page format (3rd page / Prescription Letterhead only).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()
    a4_width = 595
    a4_height = 842

    left_logo_path = _find_asset("stmelogo.png") or _find_asset("icons/logo.png")
    right_logo_path = _find_asset("logo2.png")

    if only_prescription_page is None:
        patient_id = patient.get("id")
        if patient_id:
            try:
                from database.visit_queries import get_visits_by_patient
                patient_visits = get_visits_by_patient(patient_id)
                patient_visits = sorted(patient_visits, key=lambda v: v.get("id") or 0)
                if len(patient_visits) <= 1:
                    # First prescription ever for this patient
                    only_prescription_page = False
                elif visit and visit.get("id"):
                    # Check if this visit is the earliest visit recorded for the patient
                    first_visit_id = patient_visits[0].get("id")
                    only_prescription_page = (visit.get("id") != first_visit_id)
                else:
                    # Subsequent prescription
                    only_prescription_page = True
            except Exception:
                only_prescription_page = False
        else:
            only_prescription_page = False

    if not only_prescription_page:
        # ==================== PAGE 1 ====================
        page1 = doc.new_page(width=a4_width, height=a4_height)
        _draw_header_footer(page1, left_logo_path, right_logo_path, 1)

        # Clinic reg details
        _text(page1, 40, 95, f"CLINIC REG. NO.: {_val_or_dots(patient.get('clinic_reg_no'), 25)}")
        _text(page1, 330, 95, f"DAY CARE REG. NO.: {_val_or_dots(patient.get('day_care_reg_no'), 25)}")

        # Notice
        _text(page1, 40, 112, "NOTICE: Preserve this paper carefully and bring for your further visits. Hospital does not have duplicate copy of this Case Paper", fontsize=7.5, bold=True, color=(0.2, 0.2, 0.2))
        _text(page1, 40, 124, "Suggestion to store as records as Efiling", fontsize=7.5, color=(0.4, 0.4, 0.4))

        # OPD Grid Table
        _rect(page1, fitz.Rect(40, 140, 555, 300))
        # Horizontal lines
        for y in [160, 180, 200, 220, 240, 260, 280]:
            _line(page1, 40, y, 555, y)
        # Vertical dividers
        _line(page1, 300, 140, 300, 160) # row 1
        _line(page1, 300, 180, 300, 200) # row 3
        _line(page1, 140, 200, 140, 220) # row 4
        _line(page1, 290, 200, 290, 220) # row 4
        _line(page1, 410, 200, 410, 220) # row 4
        _line(page1, 300, 260, 300, 280) # row 7

        # Populate OPD Table values
        _text(page1, 45, 153, "OPD TIMING:  " + _val_or_dots(patient.get("opd_timing"), 15))
        _text(page1, 305, 153, "O.P.D. REG. NO :  " + _val_or_dots(patient.get("opd_reg_no"), 15))
        _text(page1, 45, 173, "NAME:  " + _val_or_dots(patient.get("name"), 45), bold=True)
        _text(page1, 45, 193, "EMPLOYEE ID — SAP - ID :  " + _val_or_dots(patient.get("sap_id"), 20), bold=True)
        p_type = patient.get("type") or patient.get("patient_type") or "Student"
        school_label = "SCHOOL:" if p_type == "Student" else "DEPT:"
        school_val = patient.get("school") or ""
        if p_type == "Student" and patient.get("year"):
            school_val += f" ({patient.get('year')} Yr)"
        _text(page1, 305, 193, f"{school_label}  " + _val_or_dots(school_val, 18), bold=True)

        _text(page1, 45, 213, "SEX: M / F:  " + _val_or_dots(patient.get("sex") or patient.get("gender"), 5))
        _text(page1, 145, 213, f"AGE:  {_val_or_dots(patient.get('age'), 4)} YRS.  {_val_or_dots(patient.get('age_months'), 4)} MTHS")
        _text(page1, 295, 213, "HEIGHT:  " + _val_or_dots(patient.get("height"), 8))
        _text(page1, 415, 213, "WEIGHT Kg/ lb:  " + _val_or_dots(patient.get("weight"), 8))

        _text(page1, 45, 233, "ADDRESS:  " + _val_or_dots(patient.get("address"), 60))
        _text(page1, 45, 253, "TEL.:  " + _val_or_dots(patient.get("tel") or patient.get("mobile"), 20))

        _text(page1, 45, 273, "BROUGHT BY:  " + _val_or_dots(patient.get("brought_by"), 20))
        _text(page1, 305, 273, "RELATION:  " + _val_or_dots(patient.get("relation"), 15))
        _text(page1, 45, 293, "NAME:  " + _val_or_dots(patient.get("brought_by_name"), 45))

        # Chief Complaints
        _text(page1, 40, 318, "CHIEF COMPLAINTS & HISTORY", bold=True, fontsize=11)
        complaints = [
            patient.get("chief_complaint_1"),
            patient.get("chief_complaint_2"),
            patient.get("chief_complaint_3"),
            patient.get("chief_complaint_4"),
        ]
        if not any(complaints) and visit and visit.get("chief_complaint"):
            lines = _wrap_lines(visit.get("chief_complaint"), 60)
            for i in range(min(len(lines), 4)):
                complaints[i] = lines[i]

        _text(page1, 40, 336, "1)  " + _val_or_dots(complaints[0], 65))
        _text(page1, 40, 356, "2)  " + _val_or_dots(complaints[1], 65))
        _text(page1, 40, 376, "3)  " + _val_or_dots(complaints[2], 65))
        _text(page1, 40, 396, "4)  " + _val_or_dots(complaints[3], 65))

        # Past History
        _text(page1, 40, 422, "ANY PAST / HISTORY OF:-(if yes, fill details)", bold=True, fontsize=11)
        _rect(page1, fitz.Rect(40, 432, 555, 512))
        for y in [452, 472, 492]:
            _line(page1, 40, y, 555, y)
        _line(page1, 300, 432, 300, 492)

        _text(page1, 45, 446, "HIGH BLOOD PRESSURE:  " + _val_or_dots(patient.get("past_high_blood_pressure"), 12))
        _text(page1, 305, 446, "CHEST.PAIN:  " + _val_or_dots(patient.get("past_chest_pain"), 12))
        _text(page1, 45, 466, "SHORTNESS OF BREATH:  " + _val_or_dots(patient.get("past_shortness_of_breath"), 12))
        _text(page1, 305, 466, "ASTHAMA:  " + _val_or_dots(patient.get("past_asthma"), 12))
        _text(page1, 45, 486, "ULCER (PEPTIC):  " + _val_or_dots(patient.get("past_ulcer_peptic"), 12))
        _text(page1, 305, 486, "DIABETES:  " + _val_or_dots(patient.get("past_diabetes"), 12))
        _text(page1, 45, 506, "ANY MAJOR ILLNESS/SURGERY:  " + _val_or_dots(patient.get("past_major_illness_surgery"), 40))

        # Family History
        fam_rel = patient.get("family_relation")
        fam_header = f"FAMILY HISTORY OF ({fam_rel}):-" if fam_rel and fam_rel != "Nill" else "FAMILY HISTORY OF:-"
        _text(page1, 40, 534, fam_header, bold=True, fontsize=11)
        _rect(page1, fitz.Rect(40, 544, 555, 604))
        for y in [564, 584]:
            _line(page1, 40, y, 555, y)
        _line(page1, 300, 544, 300, 584)

        _text(page1, 45, 558, "HIGH BLOOD PRESSURE:  " + _val_or_dots(patient.get("family_high_blood_pressure"), 12))
        _text(page1, 305, 558, "DIABETES:  " + _val_or_dots(patient.get("family_diabetes"), 12))
        _text(page1, 45, 578, "CARDIAC DISORDER:  " + _val_or_dots(patient.get("family_cardiac_disorder"), 12))
        _text(page1, 305, 578, "GENETIC DISORDER, if known,:  " + _val_or_dots(patient.get("family_genetic_disorder"), 12))
        _text(page1, 45, 598, "OTHER RELEVANT HISTORY:  " + _val_or_dots(patient.get("other_relevant_history"), 40))

        # ==================== PAGE 2 ====================
        page2 = doc.new_page(width=a4_width, height=a4_height)
        _draw_header_footer(page2, left_logo_path, right_logo_path, 2)

        # Title block
        page2.draw_rect(fitz.Rect(197, 95, 397, 115), color=(0.1, 0.1, 0.1), fill=(0.1, 0.1, 0.1), width=0)
        _text(page2, 238, 109, "PHYSICAL EXAMINATION", bold=True, fontsize=10, color=(1, 1, 1))

        # BP & Vitals
        _text(page2, 40, 134, "BLOOD PRESSURE mm.of Hg:  " + _val_or_dots(patient.get("blood_pressure"), 20))
        _text(page2, 40, 154, "PULSE PM/:  " + _val_or_dots(patient.get("pulse"), 15))
        _text(page2, 280, 154, "RESP RATE PM:  " + _val_or_dots(patient.get("resp_rate"), 15))
        _text(page2, 40, 174, "GENERAL APPERANCE:  " + _val_or_dots(patient.get("general_appearance"), 40))

        # Exam Grid Table
        _rect(page2, fitz.Rect(40, 195, 555, 335))
        h_y = [195, 218, 241, 264, 287, 310, 335]
        for y in h_y[1:-1]:
            _line(page2, 40, y, 555, y)
        _line(page2, 120, 195, 120, 218)
        _line(page2, 200, 195, 200, 218)
        _line(page2, 280, 195, 280, 218)
        _line(page2, 380, 195, 380, 218)
        _line(page2, 440, 195, 440, 218)
        _line(page2, 120, 241, 120, 264)

        _text(page2, 45, 210, "EYES:")
        _text(page2, 125, 210, "RIGHT: " + _val_or_dots(patient.get("eyes_right"), 8))
        _text(page2, 205, 210, "LEFT: " + _val_or_dots(patient.get("eyes_left"), 8))
        _text(page2, 285, 210, "Colour Vision")
        _text(page2, 385, 210, "Right: " + _val_or_dots(patient.get("colour_vision_right"), 5))
        _text(page2, 445, 210, "Left: " + _val_or_dots(patient.get("colour_vision_left"), 5))

        _text(page2, 45, 233, "EARS:")
        _text(page2, 45, 256, "Inspection: " + _val_or_dots(patient.get("ears_inspection"), 8))
        _text(page2, 125, 256, "Hearing: " + _val_or_dots(patient.get("ears_hearing"), 30))

        _text(page2, 45, 279, "CVS:  " + _val_or_dots(patient.get("cvs"), 45))
        _text(page2, 45, 302, "Per Abdomen:  " + _val_or_dots(patient.get("per_abdomen"), 45))
        _text(page2, 45, 325, "Chest:  " + _val_or_dots(patient.get("chest"), 45))

        _text(page2, 40, 355, "DATE:  " + _val_or_dots(patient.get("exam_date"), 15))
        _text(page2, 280, 355, "NAME OF DOCTOR:  " + _val_or_dots(patient.get("doctor_name"), 25))

        p_diag = visit.get("diagnosis") if (visit and visit.get("diagnosis")) else patient.get("diagnosis")
        _text(page2, 40, 385, "DIAGNOSIS:  " + _val_or_dots(p_diag, 50))

        p_ref = visit.get("referral") if (visit and visit.get("referral")) else patient.get("admission_referral_date")
        _text(page2, 40, 415, "ADMISSION referral? DATE:  " + _val_or_dots(p_ref, 40))

        _text(page2, 40, 445, "ADVISE:", bold=True)
        _rect(page2, fitz.Rect(40, 458, 555, 775))

        advise_text = ""
        if visit and (visit.get("treatment") or visit.get("advise")):
            treatment = _safe_text(visit.get("treatment"))
            advise = _safe_text(visit.get("advise"))
            parts = [p for p in [treatment, advise] if p]
            advise_text = "\n\n".join(parts)
        else:
            advise_text = _safe_text(patient.get("advise"))

        if advise_text:
            _textbox(page2, fitz.Rect(48, 466, 547, 765), advise_text, fontsize=9.5)

    # ==================== PAGE 3 (Prescription Letterhead) ====================
    page3 = doc.new_page(width=a4_width, height=a4_height)
    _draw_header_footer(page3, left_logo_path, right_logo_path, 1 if only_prescription_page else 3)

    p_date = visit.get("visit_date")[:10] if (visit and visit.get("visit_date")) else patient.get("letter_date")
    if p_date:
        try:
            p_date = datetime.strptime(p_date, "%Y-%m-%d").strftime("%d %b %Y")
        except ValueError:
            pass
    else:
        p_date = datetime.now().strftime("%d %b %Y")
    _text(page3, 380, 95, "Date:  " + _val_or_dots(p_date, 15))
    _text(page3, 40, 118, "Emp. Name:  " + _val_or_dots(patient.get("emp_name") or patient.get("name"), 25))
    _text(page3, 380, 118, "Emp. Code:  " + _val_or_dots(patient.get("emp_code") or patient.get("sap_id"), 15))

    p_type = patient.get("type") or patient.get("patient_type") or "Student"
    school_lbl = "School:  " if p_type == "Student" else "Dept:  "
    school_v = patient.get("school") or ""
    if p_type == "Student" and patient.get("year"):
        school_v += f" ({patient.get('year')} Yr)"
    _text(page3, 40, 134, school_lbl + _val_or_dots(school_v, 20))

    line_x = 149
    _line(page3, line_x, 140, line_x, 780)

    rx_x = line_x + 10
    _text(page3, rx_x, 160, "Rx", bold=True, fontsize=20, color=(0.1, 0.1, 0.1))

    prescription_text = ""
    if visit and visit.get("prescription"):
        prescription_text = visit.get("prescription")

    if prescription_text:
        lines = []
        for chunk in prescription_text.split(";"):
            clean_chunk = chunk.strip()
            if clean_chunk:
                lines.append(clean_chunk)

        y_pos = 190
        for idx, line in enumerate(lines, 1):
            _text(page3, rx_x + 15, y_pos, f"{idx}. {line}", fontsize=11)
            y_pos += 22

    doc.save(str(output_path))
    doc.close()
    return str(output_path)