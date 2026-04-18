"""
visit_queries.py
----------------
All SQL operations for Visits / Consultations.

Covers:
  - Creating and updating visit records
  - Fetching visit history per patient
  - Disease category management (including doctor-added categories)
  - Filtering visits across the whole system
  - Visit statistics for reports
"""

import sqlite3
import logging
from typing import Optional
from .db_manager import get_connection

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row) if row else {}


def _rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
#  DISEASE CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

def get_all_categories() -> list[dict]:
    """All disease categories (default + doctor-added), ordered by name."""
    sql = "SELECT * FROM disease_categories ORDER BY name COLLATE NOCASE"
    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql).fetchall())
    finally:
        conn.close()


def add_custom_category(name: str) -> int:
    """
    Doctor adds a new disease category at runtime.
    Returns new category id.
    Raises sqlite3.IntegrityError if name already exists.
    """
    sql = "INSERT INTO disease_categories (name, is_custom) VALUES (?, 1)"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (name.strip(),))
        conn.commit()
        logger.info(f"Custom category added: '{name}'")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"Category already exists: '{name}'")
        raise
    finally:
        conn.close()


def delete_custom_category(category_id: int) -> bool:
    """Delete a doctor-added category (cannot delete defaults where is_custom=0)."""
    sql = "DELETE FROM disease_categories WHERE id = ? AND is_custom = 1"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (category_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  CREATE VISIT
# ─────────────────────────────────────────────────────────────────────────────

def create_visit(
    patient_id: int,
    visit_type: str = "Walk-in",       # 'Walk-in' | 'Scheduled' | 'Emergency'
    chief_complaint: str = None,
    diagnosis: str = None,
    category_id: int = None,
    investigations: str = None,
    treatment: str = None,
    prescription: str = None,
    referral: str = None,              # None = no referral
    rest_days: int = 0,
    medical_leave: bool = False,
    ambulance_used: bool = False,
    follow_up_date: str = None,        # ISO string: 'YYYY-MM-DD'
    notes: str = None,
    visit_date: str = None,            # Override if needed; defaults to now()
) -> int:
    """
    Record a new consultation/visit. Returns the new visit id.
    """
    sql = """
        INSERT INTO visits (
            patient_id, visit_type, visit_date,
            chief_complaint, diagnosis, category_id,
            investigations, treatment, prescription,
            referral, rest_days, medical_leave, ambulance_used,
            follow_up_date, notes
        ) VALUES (
            ?, ?, COALESCE(?, datetime('now')),
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?
        )
    """
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (
            patient_id, visit_type, visit_date,
            chief_complaint, diagnosis, category_id,
            investigations, treatment, prescription,
            referral, rest_days,
            1 if medical_leave else 0,
            1 if ambulance_used else 0,
            follow_up_date, notes
        ))
        conn.commit()
        logger.info(f"Visit created: patient_id={patient_id}, visit_id={cursor.lastrowid}")
        return cursor.lastrowid
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  READ — single visit
# ─────────────────────────────────────────────────────────────────────────────

def get_visit_by_id(visit_id: int) -> Optional[dict]:
    """
    Fetch one visit with patient name and category name joined in.
    """
    sql = """
        SELECT
            v.*,
            p.name          AS patient_name,
            p.sap_id        AS patient_sap_id,
            p.type          AS patient_type,
            dc.name         AS category_name
        FROM visits v
        JOIN patients          p  ON p.id  = v.patient_id
        LEFT JOIN disease_categories dc ON dc.id = v.category_id
        WHERE v.id = ?
    """
    conn = get_connection()
    try:
        row = conn.execute(sql, (visit_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  READ — patient visit history
# ─────────────────────────────────────────────────────────────────────────────

def get_visits_by_patient(
    patient_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """All visits for one patient, newest first."""
    sql = """
        SELECT
            v.*,
            dc.name AS category_name
        FROM visits v
        LEFT JOIN disease_categories dc ON dc.id = v.category_id
        WHERE v.patient_id = ?
        ORDER BY v.visit_date DESC
        LIMIT ? OFFSET ?
    """
    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql, (patient_id, limit, offset)).fetchall())
    finally:
        conn.close()


def count_visits_by_patient(patient_id: int) -> int:
    sql = "SELECT COUNT(*) FROM visits WHERE patient_id = ?"
    conn = get_connection()
    try:
        return conn.execute(sql, (patient_id,)).fetchone()[0]
    finally:
        conn.close()


def get_last_visit(patient_id: int) -> Optional[dict]:
    """Fetch only the most recent visit for a patient."""
    sql = """
        SELECT v.*, dc.name AS category_name
        FROM visits v
        LEFT JOIN disease_categories dc ON dc.id = v.category_id
        WHERE v.patient_id = ?
        ORDER BY v.visit_date DESC
        LIMIT 1
    """
    conn = get_connection()
    try:
        row = conn.execute(sql, (patient_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_followups_for_date(date_str: str) -> list[dict]:
    """
    Fetch expected follow-ups for a specific date (e.g. today).
    Returns basic visit info + patient info.
    """
    sql = """
        SELECT
            v.id AS visit_id,
            v.visit_date,
            v.notes,
            p.id AS patient_id,
            p.name AS patient_name,
            p.sap_id AS patient_sap_id,
            dc.name AS category_name
        FROM visits v
        JOIN patients p ON p.id = v.patient_id
        LEFT JOIN disease_categories dc ON dc.id = v.category_id
        WHERE v.follow_up_date = ?
        ORDER BY p.name COLLATE NOCASE
    """
    conn = get_connection()
    try:
         return _rows_to_list(conn.execute(sql, (date_str,)).fetchall())
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  READ — filtered visit list (system-wide)
# ─────────────────────────────────────────────────────────────────────────────

def search_visits(
    patient_name: str = None,
    sap_id: str = None,
    patient_type: str = None,          # 'Student' | 'Staff'
    category_id: int = None,
    visit_type: str = None,            # 'Walk-in' | 'Scheduled' | 'Emergency'
    date_from: str = None,             # 'YYYY-MM-DD'
    date_to: str = None,               # 'YYYY-MM-DD'
    has_referral: bool = None,
    medical_leave: bool = None,
    ambulance_used: bool = None,
    diagnosis_keyword: str = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """
    System-wide visit filter — every param is optional.
    Returns visits with patient info and category name joined.
    """
    conditions = []
    params = []

    if patient_name:
        conditions.append("p.name LIKE ? COLLATE NOCASE")
        params.append(f"%{patient_name}%")

    if sap_id:
        conditions.append("p.sap_id LIKE ?")
        params.append(f"%{sap_id}%")

    if patient_type:
        conditions.append("p.type = ?")
        params.append(patient_type)

    if category_id is not None:
        conditions.append("v.category_id = ?")
        params.append(category_id)

    if visit_type:
        conditions.append("v.visit_type = ?")
        params.append(visit_type)

    if date_from:
        conditions.append("DATE(v.visit_date) >= ?")
        params.append(date_from)

    if date_to:
        conditions.append("DATE(v.visit_date) <= ?")
        params.append(date_to)

    if has_referral is not None:
        if has_referral:
            conditions.append("v.referral IS NOT NULL AND v.referral != ''")
        else:
            conditions.append("(v.referral IS NULL OR v.referral = '')")

    if medical_leave is not None:
        conditions.append("v.medical_leave = ?")
        params.append(1 if medical_leave else 0)

    if ambulance_used is not None:
        conditions.append("v.ambulance_used = ?")
        params.append(1 if ambulance_used else 0)

    if diagnosis_keyword:
        conditions.append("v.diagnosis LIKE ? COLLATE NOCASE")
        params.append(f"%{diagnosis_keyword}%")

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            v.*,
            p.name      AS patient_name,
            p.sap_id    AS patient_sap_id,
            p.type      AS patient_type,
            dc.name     AS category_name
        FROM visits v
        JOIN patients              p  ON p.id  = v.patient_id
        LEFT JOIN disease_categories dc ON dc.id = v.category_id
        {where_clause}
        ORDER BY v.visit_date DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  UPDATE
# ─────────────────────────────────────────────────────────────────────────────

def update_visit(
    visit_id: int,
    visit_type: str = None,
    chief_complaint: str = None,
    diagnosis: str = None,
    category_id: int = None,
    investigations: str = None,
    treatment: str = None,
    prescription: str = None,
    referral: str = None,
    rest_days: int = None,
    medical_leave: bool = None,
    ambulance_used: bool = None,
    follow_up_date: str = None,
    notes: str = None,
) -> bool:
    """Partial update of a visit. Returns True if row was modified."""
    fields = {}
    if visit_type      is not None: fields["visit_type"]      = visit_type
    if chief_complaint is not None: fields["chief_complaint"] = chief_complaint
    if diagnosis       is not None: fields["diagnosis"]       = diagnosis
    if category_id     is not None: fields["category_id"]     = category_id
    if investigations  is not None: fields["investigations"]  = investigations
    if treatment       is not None: fields["treatment"]       = treatment
    if prescription    is not None: fields["prescription"]    = prescription
    if referral        is not None: fields["referral"]        = referral
    if rest_days       is not None: fields["rest_days"]       = rest_days
    if medical_leave   is not None: fields["medical_leave"]   = 1 if medical_leave else 0
    if ambulance_used  is not None: fields["ambulance_used"]  = 1 if ambulance_used else 0
    if follow_up_date  is not None: fields["follow_up_date"]  = follow_up_date
    if notes           is not None: fields["notes"]           = notes

    if not fields:
        return False

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    sql = f"UPDATE visits SET {set_clause} WHERE id = ?"
    params = list(fields.values()) + [visit_id]

    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE
# ─────────────────────────────────────────────────────────────────────────────

def delete_visit(visit_id: int) -> bool:
    sql = "DELETE FROM visits WHERE id = ?"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (visit_id,))
        conn.commit()
        logger.info(f"Visit deleted: id={visit_id}")
        return cursor.rowcount > 0
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  STATS  (for reports / dashboard)
# ─────────────────────────────────────────────────────────────────────────────

def get_visit_stats(date_from: str = None, date_to: str = None) -> dict:
    """
    Summary counts for a given date range (or all time).
    {
        total_visits,
        walk_in, scheduled, emergency,
        with_referral, with_medical_leave, with_ambulance
    }
    """
    conditions = []
    params = []
    if date_from:
        conditions.append("DATE(visit_date) >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("DATE(visit_date) <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            COUNT(*)                                                  AS total_visits,
            SUM(CASE WHEN visit_type = 'Walk-in'    THEN 1 ELSE 0 END) AS walk_in,
            SUM(CASE WHEN visit_type = 'Scheduled'  THEN 1 ELSE 0 END) AS scheduled,
            SUM(CASE WHEN visit_type = 'Emergency'  THEN 1 ELSE 0 END) AS emergency,
            SUM(CASE WHEN referral IS NOT NULL AND referral != '' THEN 1 ELSE 0 END) AS with_referral,
            SUM(medical_leave)                                        AS with_medical_leave,
            SUM(ambulance_used)                                       AS with_ambulance
        FROM visits
        {where}
    """
    conn = get_connection()
    try:
        row = conn.execute(sql, params).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_disease_distribution(date_from: str = None, date_to: str = None) -> list[dict]:
    """
    Count of visits per disease category — for charts / reports.
    Returns: [{'category_name': ..., 'visit_count': ...}, ...]
    """
    conditions = []
    params = []
    if date_from:
        conditions.append("DATE(v.visit_date) >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("DATE(v.visit_date) <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            COALESCE(dc.name, 'Uncategorised') AS category_name,
            COUNT(v.id)                         AS visit_count
        FROM visits v
        LEFT JOIN disease_categories dc ON dc.id = v.category_id
        {where}
        GROUP BY v.category_id
        ORDER BY visit_count DESC
    """
    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


def get_visits_for_export(date_from: str = None, date_to: str = None) -> list[dict]:
    """
    Full visit data with all joined fields — used by excel_exporter.py.
    """
    conditions = []
    params = []
    if date_from:
        conditions.append("DATE(v.visit_date) >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("DATE(v.visit_date) <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            v.id,
            v.visit_date,
            v.visit_type,
            p.sap_id        AS patient_sap_id,
            p.name          AS patient_name,
            p.type          AS patient_type,
            p.school,
            p.age,
            p.gender,
            dc.name         AS disease_category,
            v.chief_complaint,
            v.diagnosis,
            v.investigations,
            v.treatment,
            v.prescription,
            v.referral,
            v.rest_days,
            v.medical_leave,
            v.ambulance_used,
            v.follow_up_date,
            v.notes
        FROM visits v
        JOIN patients              p  ON p.id  = v.patient_id
        LEFT JOIN disease_categories dc ON dc.id = v.category_id
        {where}
        ORDER BY v.visit_date DESC
    """
    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()