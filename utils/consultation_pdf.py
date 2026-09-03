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

def _text(page, x, y, text, fontname="helv", fontsize=9.5, color=(0.1, 0.1, 0.1), bold=True):
    fname = "hebo" if bold else "helv"
    page.insert_text(fitz.Point(x, y), str(text), fontname=fname, fontsize=fontsize, color=color)

def _textbox(page, rect, text, fontname="helv", fontsize=9.5, color=(0.1, 0.1, 0.1), bold=True, align=0):
    fname = "hebo" if bold else "helv"
    page.insert_textbox(rect, str(text), fontname=fname, fontsize=fontsize, color=color, align=align)

def _draw_header_footer(page, left_logo_path, right_logo_path, page_num):
    h = 105
    w_left = h * (355 / 422)   # ~88.3
    w_right = h * (507 / 492)  # ~108.2

    # Left logo: SVKM's NMIMS
    if left_logo_path and Path(left_logo_path).exists():
        page.insert_image(fitz.Rect(40, 10, 40 + w_left, 10 + h), filename=str(left_logo_path))
    else:
        _text(page, 40, 35, "SVKM'S", fontsize=10, bold=True, color=(0.725, 0.11, 0.11))
        _text(page, 40, 50, "NMIMS", fontsize=15, bold=True, color=(0.1, 0.1, 0.1))
        _text(page, 40, 60, "Deemed to be UNIVERSITY", fontsize=7.5, color=(0.4, 0.4, 0.4))

    # Right logo: SUNRIDGES HEALTH XI
    if right_logo_path and Path(right_logo_path).exists():
        page.insert_image(fitz.Rect(555 - w_right, 10, 555, 10 + h), filename=str(right_logo_path))
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
        only_prescription_page = True

    if not only_prescription_page:
        # ==================== PAGE 1 ====================
        page1 = doc.new_page(width=a4_width, height=a4_height)
        _draw_header_footer(page1, left_logo_path, right_logo_path, 1)

        # Clinic reg details
        _text(page1, 40, 130, f"CLINIC REG. NO.: {_val_or_dots(patient.get('clinic_reg_no'), 25)}")
        _text(page1, 330, 130, f"DAY CARE REG. NO.: {_val_or_dots(patient.get('day_care_reg_no'), 25)}")

        # Notice
        _text(page1, 40, 146, "NOTICE: Preserve this paper carefully and bring for your further visits. Hospital does not have duplicate copy of this Case Paper", fontsize=7.5, bold=True, color=(0.2, 0.2, 0.2))
        _text(page1, 40, 158, "Suggestion to store as records as Efiling", fontsize=7.5, color=(0.4, 0.4, 0.4))

        # OPD Grid Table
        _rect(page1, fitz.Rect(40, 172, 555, 332))
        # Horizontal lines
        for y in [192, 212, 232, 252, 272, 292, 312]:
            _line(page1, 40, y, 555, y)
        # Vertical dividers
        _line(page1, 300, 172, 300, 192) # row 1
        _line(page1, 300, 212, 300, 232) # row 3
        _line(page1, 140, 232, 140, 252) # row 4
        _line(page1, 290, 232, 290, 252) # row 4
        _line(page1, 410, 232, 410, 252) # row 4
        _line(page1, 300, 292, 300, 312) # row 7

        # Populate OPD Table values
        _text(page1, 45, 185, "OPD TIMING:  " + _val_or_dots(patient.get("opd_timing"), 15))
        _text(page1, 305, 185, "O.P.D. REG. NO :  " + _val_or_dots(patient.get("opd_reg_no"), 15))
        _text(page1, 45, 205, "NAME:  " + _val_or_dots(patient.get("name"), 45), bold=True)
        _text(page1, 45, 225, "EMPLOYEE ID — SAP - ID :  " + _val_or_dots(patient.get("sap_id"), 20), bold=True)
        p_type = patient.get("type") or patient.get("patient_type") or "Student"
        school_label = "SCHOOL:" if p_type == "Student" else "DEPT:"
        school_val = patient.get("school") or ""
        if p_type == "Student" and patient.get("year"):
            school_val += f" ({patient.get('year')} Yr)"
        _text(page1, 305, 225, f"{school_label}  " + _val_or_dots(school_val, 18), bold=True)

        phone_val_p1 = (
            patient.get("mobile")
            or patient.get("phone")
            or patient.get("tel")
            or patient.get("contact")
            or patient.get("phone_no")
            or patient.get("mobile_no")
            or (visit.get("mobile") if visit else None)
            or (visit.get("phone") if visit else None)
            or (visit.get("tel") if visit else None)
            or ""
        )
        _text(page1, 45, 245, "SEX: M / F:  " + _val_or_dots(patient.get("sex") or patient.get("gender"), 5))
        _text(page1, 145, 245, f"AGE:  {_val_or_dots(patient.get('age'), 4)} YRS.  {_val_or_dots(patient.get('age_months'), 4)} MTHS")
        _text(page1, 295, 245, "HEIGHT:  " + _val_or_dots(patient.get("height"), 8))
        _text(page1, 415, 245, "PHONE:  " + _val_or_dots(phone_val_p1, 12))

        _text(page1, 45, 265, "ADDRESS:  " + _val_or_dots(patient.get("address"), 60))
        _text(page1, 45, 285, "TEL.:  " + _val_or_dots(patient.get("tel") or patient.get("mobile"), 20))

        _text(page1, 45, 305, "BROUGHT BY:  " + _val_or_dots(patient.get("brought_by"), 20))
        _text(page1, 305, 305, "RELATION:  " + _val_or_dots(patient.get("relation"), 15))
        _text(page1, 45, 325, "NAME:  " + _val_or_dots(patient.get("brought_by_name"), 45))

        # Chief Complaints
        _text(page1, 40, 350, "CHIEF COMPLAINTS & HISTORY", bold=True, fontsize=11)
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

        _text(page1, 40, 368, "1)  " + _val_or_dots(complaints[0], 65))
        _text(page1, 40, 388, "2)  " + _val_or_dots(complaints[1], 65))
        _text(page1, 40, 408, "3)  " + _val_or_dots(complaints[2], 65))
        _text(page1, 40, 428, "4)  " + _val_or_dots(complaints[3], 65))

        # Past History
        _text(page1, 40, 454, "ANY PAST / HISTORY OF:-(if yes, fill details)", bold=True, fontsize=11)
        _rect(page1, fitz.Rect(40, 464, 555, 544))
        for y in [484, 504, 524]:
            _line(page1, 40, y, 555, y)
        _line(page1, 300, 464, 300, 524)

        _text(page1, 45, 478, "HIGH BLOOD PRESSURE:  " + _val_or_dots(patient.get("past_high_blood_pressure"), 12))
        _text(page1, 305, 478, "CHEST.PAIN:  " + _val_or_dots(patient.get("past_chest_pain"), 12))
        _text(page1, 45, 498, "SHORTNESS OF BREATH:  " + _val_or_dots(patient.get("past_shortness_of_breath"), 12))
        _text(page1, 305, 498, "ASTHAMA:  " + _val_or_dots(patient.get("past_asthma"), 12))
        _text(page1, 45, 518, "ULCER (PEPTIC):  " + _val_or_dots(patient.get("past_ulcer_peptic"), 12))
        _text(page1, 305, 518, "DIABETES:  " + _val_or_dots(patient.get("past_diabetes"), 12))
        _text(page1, 45, 538, "ANY MAJOR ILLNESS/SURGERY:  " + _val_or_dots(patient.get("past_major_illness_surgery"), 40))

        # Family History
        fam_rel = patient.get("family_relation")
        fam_header = f"FAMILY HISTORY OF ({fam_rel}):-" if fam_rel and fam_rel != "Nill" else "FAMILY HISTORY OF:-"
        _text(page1, 40, 566, fam_header, bold=True, fontsize=11)
        _rect(page1, fitz.Rect(40, 576, 555, 636))
        for y in [596, 616]:
            _line(page1, 40, y, 555, y)
        _line(page1, 300, 576, 300, 616)

        _text(page1, 45, 590, "HIGH BLOOD PRESSURE:  " + _val_or_dots(patient.get("family_high_blood_pressure"), 12))
        _text(page1, 305, 590, "DIABETES:  " + _val_or_dots(patient.get("family_diabetes"), 12))
        _text(page1, 45, 610, "CARDIAC DISORDER:  " + _val_or_dots(patient.get("family_cardiac_disorder"), 12))
        _text(page1, 305, 610, "GENETIC DISORDER, if known,:  " + _val_or_dots(patient.get("family_genetic_disorder"), 12))
        _text(page1, 45, 630, "OTHER RELEVANT HISTORY:  " + _val_or_dots(patient.get("other_relevant_history"), 40))

        # ==================== PAGE 2 ====================
        page2 = doc.new_page(width=a4_width, height=a4_height)
        _draw_header_footer(page2, left_logo_path, right_logo_path, 2)

        # Title block
        page2.draw_rect(fitz.Rect(197, 115, 397, 135), color=(0.1, 0.1, 0.1), fill=(0.1, 0.1, 0.1), width=0)
        _text(page2, 238, 129, "PHYSICAL EXAMINATION", bold=True, fontsize=10, color=(1, 1, 1))

        # BP & Vitals
        _text(page2, 40, 154, "BLOOD PRESSURE mm.of Hg:  " + _val_or_dots(patient.get("blood_pressure"), 20))
        _text(page2, 40, 174, "PULSE PM/:  " + _val_or_dots(patient.get("pulse"), 15))
        _text(page2, 280, 174, "RESP RATE PM:  " + _val_or_dots(patient.get("resp_rate"), 15))
        _text(page2, 40, 194, "GENERAL APPERANCE:  " + _val_or_dots(patient.get("general_appearance"), 40))

        # Exam Grid Table
        _rect(page2, fitz.Rect(40, 215, 555, 355))
        h_y = [215, 238, 261, 284, 307, 330, 355]
        for y in h_y[1:-1]:
            _line(page2, 40, y, 555, y)
        _line(page2, 120, 215, 120, 238)
        _line(page2, 200, 215, 200, 238)
        _line(page2, 280, 215, 280, 238)
        _line(page2, 380, 215, 380, 238)
        _line(page2, 440, 215, 440, 238)
        _line(page2, 120, 261, 120, 284)

        _text(page2, 45, 230, "EYES:")
        _text(page2, 125, 230, "RIGHT: " + _val_or_dots(patient.get("eyes_right"), 8))
        _text(page2, 205, 230, "LEFT: " + _val_or_dots(patient.get("eyes_left"), 8))
        _text(page2, 285, 230, "Colour Vision")
        _text(page2, 385, 230, "Right: " + _val_or_dots(patient.get("colour_vision_right"), 5))
        _text(page2, 445, 230, "Left: " + _val_or_dots(patient.get("colour_vision_left"), 5))

        _text(page2, 45, 253, "EARS:")
        _text(page2, 45, 276, "Inspection: " + _val_or_dots(patient.get("ears_inspection"), 8))
        _text(page2, 125, 276, "Hearing: " + _val_or_dots(patient.get("ears_hearing"), 30))

        _text(page2, 45, 299, "CVS:  " + _val_or_dots(patient.get("cvs"), 45))
        _text(page2, 45, 322, "Per Abdomen:  " + _val_or_dots(patient.get("per_abdomen"), 45))
        _text(page2, 45, 345, "Chest:  " + _val_or_dots(patient.get("chest"), 45))

        _text(page2, 40, 375, "DATE:  " + _val_or_dots(patient.get("exam_date"), 15))
        _text(page2, 280, 375, "NAME OF DOCTOR:  " + _val_or_dots(patient.get("doctor_name"), 25))

        p_diag = visit.get("diagnosis") if (visit and visit.get("diagnosis")) else patient.get("diagnosis")
        _text(page2, 40, 405, "DIAGNOSIS:  " + _val_or_dots(p_diag, 50))

        p_ref = visit.get("referral") if (visit and visit.get("referral")) else patient.get("admission_referral_date")
        _text(page2, 40, 435, "ADMISSION referral? DATE:  " + _val_or_dots(p_ref, 40))

        _text(page2, 40, 465, "ADVISE:", bold=True)
        _rect(page2, fitz.Rect(40, 478, 555, 775))

        advise_text = ""
        if visit and (visit.get("treatment") or visit.get("advise")):
            treatment = _safe_text(visit.get("treatment"))
            advise = _safe_text(visit.get("advise"))
            parts = [p for p in [treatment, advise] if p]
            advise_text = "\n\n".join(parts)
        else:
            advise_text = _safe_text(patient.get("advise"))

        if advise_text:
            _textbox(page2, fitz.Rect(48, 486, 547, 765), advise_text, fontsize=9.5)

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

    # Extract Patient Details
    p_name = patient.get("emp_name") or patient.get("name")
    p_sap_id = patient.get("sap_id") or patient.get("emp_code")

    age_val = patient.get("age")
    if age_val is None and patient.get("dob"):
        try:
            from database.patient_queries import calculate_age
            age_val = calculate_age(patient.get("dob"))
        except Exception:
            pass

    age_str = ""
    if age_val is not None and str(age_val).strip():
        age_str = f"{age_val} Yrs"
        if patient.get("age_months"):
            age_str += f" {patient.get('age_months')} Mths"

    sex_str = patient.get("sex") or patient.get("gender") or ""

    phone_val = (
        patient.get("mobile")
        or patient.get("phone")
        or patient.get("tel")
        or patient.get("contact")
        or patient.get("phone_no")
        or patient.get("mobile_no")
        or (visit.get("mobile") if visit else None)
        or (visit.get("phone") if visit else None)
        or (visit.get("tel") if visit else None)
        or ""
    )
    phone_str = str(phone_val).strip() if phone_val else ""

    p_type = patient.get("type") or patient.get("patient_type") or "Student"
    school_lbl = "School:  " if p_type == "Student" else "Dept:  "
    school_v = patient.get("school") or ""
    if p_type == "Student" and patient.get("year"):
        school_v += f" ({patient.get('year')} Yr)"

    # Draw Header (Left & Right)
    y_hdr = 130
    # Right column
    _text(page3, 360, y_hdr, "Date:  " + _val_or_dots(p_date, 15))
    _text(page3, 360, y_hdr + 15, "Age:  " + _val_or_dots(age_str, 8) + "    Sex:  " + _val_or_dots(sex_str, 6))
    _text(page3, 360, y_hdr + 30, "Phone:  " + _val_or_dots(phone_str, 15))

    # Left column
    _text(page3, 40, y_hdr, "Emp. Name:  " + _val_or_dots(p_name, 25))
    _text(page3, 40, y_hdr + 15, "SAP ID:  " + _val_or_dots(p_sap_id, 18))
    _text(page3, 40, y_hdr + 30, school_lbl + _val_or_dots(school_v, 20))

    # Vitals & clinical parameters for left column
    sat_val = (
        (visit.get("saturation") if visit else None)
        or (visit.get("spo2") if visit else None)
        or patient.get("saturation")
        or patient.get("spo2")
        or ""
    )
    pulse_val = (
        (visit.get("pulse") if visit else None)
        or patient.get("pulse")
        or ""
    )
    temp_val = (
        (visit.get("temperature") if visit else None)
        or (visit.get("temp") if visit else None)
        or patient.get("temperature")
        or ""
    )
    bp_val = (
        (visit.get("blood_pressure") if visit else None)
        or (visit.get("bp") if visit else None)
        or patient.get("blood_pressure")
        or ""
    )
    inv_val = (
        (visit.get("investigations") if visit else None)
        or (visit.get("investigation") if visit else None)
        or patient.get("investigations")
        or ""
    )

    line_x = 150
    _line(page3, line_x, y_hdr + 45, line_x, 780, color=(0.7, 0.7, 0.7), width=0.8)

    # Left side items from sketch
    _text(page3, 40, 205, "SATURATION", fontsize=9.5)
    if sat_val:
        _text(page3, 40, 222, str(sat_val), fontsize=9.5)

    _text(page3, 40, 265, "PULSE", fontsize=9.5)
    if pulse_val:
        _text(page3, 40, 282, str(pulse_val), fontsize=9.5)

    _text(page3, 40, 325, "TEMPERATURE", fontsize=9.5)
    if temp_val:
        _text(page3, 40, 342, str(temp_val), fontsize=9.5)

    _text(page3, 40, 385, "BP", fontsize=9.5)
    if bp_val:
        _text(page3, 40, 402, str(bp_val), fontsize=9.5)

    # Horizontal divider between BP and INVESTIGATION
    _line(page3, 40, 430, line_x, 430, color=(0.7, 0.7, 0.7), width=0.8)

    _text(page3, 40, 455, "INVESTIGATION", fontsize=9.5)
    if inv_val:
        cleaned_inv = str(inv_val).strip()
        if cleaned_inv.lower() in ["x-ray", "x ray", "xray"]:
            cleaned_inv = ""
        else:
            import re
            cleaned_inv = re.sub(r'(?i)\bX-?Ray\b', '', cleaned_inv).strip(' ,;')
        if cleaned_inv:
            _textbox(page3, fitz.Rect(40, 472, line_x - 10, 760), cleaned_inv, fontsize=9.5)

    # Right side: Rx
    rx_logo = _find_asset("icons/rx.png") or _find_asset("rx.png")
    rx_x = line_x + 12
    if rx_logo and Path(rx_logo).exists():
        page3.insert_image(fitz.Rect(rx_x, 185, rx_x + 32, 185 + 38), filename=str(rx_logo))
    else:
        _text(page3, rx_x, 210, "Rx", bold=True, fontsize=24, color=(0.1, 0.1, 0.1))

    prescription_text = ""
    if visit and visit.get("prescription"):
        prescription_text = visit.get("prescription")

    if prescription_text:
        lines = []
        for chunk in prescription_text.split(";"):
            clean_chunk = chunk.strip()
            if clean_chunk:
                lines.append(clean_chunk)

        y_pos = 245
        for idx, line in enumerate(lines, 1):
            _text(page3, rx_x + 15, y_pos, f"{idx}. {line}", fontsize=11)
            y_pos += 22

    doc.save(str(output_path))
    doc.close()
    return str(output_path)


def export_medical_leave_pdf(
    output_path: str | Path,
    patient: dict,
    visit: dict = None,
) -> str:
    """
    Generate a 1-page Medical Certificate PDF matching the clinic's standard format.
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    left_logo = _find_asset("stmelogo.png") or _find_asset("icons/logo.png")
    right_logo = _find_asset("logo2.png")
    _draw_header_footer(page, left_logo, right_logo, page_num=1)

    p_name = patient.get("name") or patient.get("emp_name") or ""
    p_sap_id = patient.get("sap_id") or patient.get("employee_id") or ""

    # Date
    p_date = ""
    if visit and visit.get("visit_date"):
        raw_d = str(visit.get("visit_date")).strip()
        from datetime import datetime
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                p_date = datetime.strptime(raw_d[:19], fmt).strftime("%d %b %Y")
                break
            except ValueError:
                pass
        if not p_date:
            p_date = raw_d[:10]
    else:
        from datetime import datetime
        p_date = datetime.now().strftime("%d %b %Y")

    # Age & Sex
    age_v = patient.get("age")
    age_m = patient.get("age_months")
    age_str = ""
    if age_v is not None and str(age_v).strip():
        age_str = f"{age_v} Yrs"
        if age_m is not None and str(age_m).strip():
            age_str += f" {age_m} Mths"
    elif age_m is not None and str(age_m).strip():
        age_str = f"{age_m} Mths"

    sex_val = str(patient.get("sex") or patient.get("gender") or "").strip()
    if sex_val.lower().startswith("m"):
        sex_str = "M"
    elif sex_val.lower().startswith("f"):
        sex_str = "F"
    else:
        sex_str = sex_val

    phone_val = (
        patient.get("mobile")
        or patient.get("phone")
        or patient.get("tel")
        or patient.get("contact")
        or (visit.get("phone") if visit else None)
        or (visit.get("mobile") if visit else None)
        or ""
    )
    phone_str = str(phone_val).strip() if phone_val else "..............."

    p_type = patient.get("type") or patient.get("patient_type") or "Student"
    school_lbl = "School:  " if p_type == "Student" else "Dept:  "
    school_v = patient.get("school") or ""
    if p_type == "Student" and patient.get("year"):
        school_v += f" ({patient.get('year')} Yr)"

    # Draw Header (Left & Right)
    y_hdr = 130
    _text(page, 40, y_hdr, "Emp. Name:  " + _val_or_dots(p_name, 25))
    _text(page, 40, y_hdr + 15, "SAP ID:  " + _val_or_dots(p_sap_id, 18))
    _text(page, 40, y_hdr + 30, school_lbl + _val_or_dots(school_v, 20))

    _text(page, 360, y_hdr, "Date:  " + _val_or_dots(p_date, 15))
    _text(page, 360, y_hdr + 15, "Age:  " + _val_or_dots(age_str, 8) + "    Sex:  " + _val_or_dots(sex_str, 6))
    _text(page, 360, y_hdr + 30, "Phone:  " + phone_str)

    # Title
    title_text = "MEDICAL CERTIFICATE"
    title_fs = 24
    title_w = fitz.get_text_length(title_text, fontname="hebo", fontsize=title_fs)
    title_x = (595 - title_w) / 2
    title_y = 420

    _text(page, title_x, title_y, title_text, fontsize=title_fs, bold=True)
    _line(page, title_x, title_y + 4, title_x + title_w, title_y + 4, color=(0, 0, 0), width=1.5)

    # Body
    y_body = title_y + 60
    _text(page, 40, y_body, "TO WHO SO EVER IT MAY CONCERN", fontsize=11, bold=True)
    _text(page, 40, y_body + 20, "Certified that the above named is/was under my treatment w.e.f. _____ to _____.", fontsize=11, bold=True)
    _text(page, 40, y_body + 40, "He/She is/was suffering from _____. He/She is/was advised Rest in Bed for ___ days from ___ to ___.", fontsize=11, bold=True)

    # Doctor signature
    _text(page, 400, 650, "Signature and Stamp of Doctor", fontsize=10, bold=True)

    doc.save(str(output_path))
    doc.close()
    return str(output_path)