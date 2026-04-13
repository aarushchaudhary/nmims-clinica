"""
patient_queries.py
------------------
All SQL operations for the Patient module.

Functions return:
  - dict / list[dict]  →  for use in UI (converted from sqlite3.Row)
  - int                →  for IDs or row counts
  - None               →  for deletes / updates
"""

import sqlite3
import logging
from typing import Optional
from datetime import datetime, date
from .db_manager import get_connection

logger = logging.getLogger(__name__)

def calculate_age(dob_str: Optional[str]) -> Optional[int]:
    if not dob_str:
        return None
    try:
        born = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row) if row else {}


def _rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
#  CREATE
# ─────────────────────────────────────────────────────────────────────────────

def create_patient(
    sap_id: str,
    name: str,
    patient_type: str,       # 'Student' | 'Staff'
    school: str = None,
    mobile: str = None,
    dob: str = None,
    gender: str = None,      # 'Male' | 'Female' | 'Other'
    blood_group: str = None,
    address: str = None,
) -> int:
    """
    Insert a new patient. Returns the new patient's id.
    Raises sqlite3.IntegrityError if sap_id already exists.
    """
    age = calculate_age(dob)
    sql = """
        INSERT INTO patients
            (sap_id, name, type, school, mobile, dob, age, gender, blood_group, address)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (
            sap_id.strip(), name.strip(), patient_type,
            school, mobile, dob, age, gender, blood_group, address
        ))
        conn.commit()
        logger.info(f"Patient created: sap_id={sap_id}, id={cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"Duplicate SAP ID attempted: {sap_id}")
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  READ — single record
# ─────────────────────────────────────────────────────────────────────────────

def get_patient_by_id(patient_id: int) -> Optional[dict]:
    """Fetch a single patient by primary key."""
    sql = "SELECT * FROM patients WHERE id = ?"
    conn = get_connection()
    try:
        row = conn.execute(sql, (patient_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_patient_by_sap_id(sap_id: str) -> Optional[dict]:
    """Fetch a single patient by SAP ID."""
    sql = "SELECT * FROM patients WHERE sap_id = ?"
    conn = get_connection()
    try:
        row = conn.execute(sql, (sap_id.strip(),)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def sap_id_exists(sap_id: str, exclude_id: int = None) -> bool:
    """Check whether a SAP ID is already taken. Used for validation."""
    conn = get_connection()
    try:
        if exclude_id:
            row = conn.execute(
                "SELECT 1 FROM patients WHERE sap_id = ? AND id != ?",
                (sap_id.strip(), exclude_id)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT 1 FROM patients WHERE sap_id = ?",
                (sap_id.strip(),)
            ).fetchone()
        return row is not None
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  READ — lists + search + filters
# ─────────────────────────────────────────────────────────────────────────────

def get_all_patients(order_by: str = "name") -> list[dict]:
    """Return every patient, ordered by name or created_at."""
    allowed_orders = {"name", "created_at", "sap_id", "age"}
    order_by = order_by if order_by in allowed_orders else "name"
    sql = f"SELECT * FROM patients ORDER BY {order_by} COLLATE NOCASE"
    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql).fetchall())
    finally:
        conn.close()


def search_patients(
    query: str = "",
    patient_type: str = None,    # 'Student' | 'Staff' | None = all
    school: str = None,
    age_min: int = None,
    age_max: int = None,
    gender: str = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """
    Universal patient search + filter.
    `query` matches against: name, sap_id, mobile  (case-insensitive)
    All other params are optional filters.
    Returns up to `limit` rows starting at `offset` (for pagination).
    """
    conditions = []
    params = []

    if query:
        like = f"%{query.strip()}%"
        conditions.append(
            "(name LIKE ? COLLATE NOCASE OR sap_id LIKE ? OR mobile LIKE ?)"
        )
        params.extend([like, like, like])

    if patient_type:
        conditions.append("type = ?")
        params.append(patient_type)

    if school:
        conditions.append("school LIKE ? COLLATE NOCASE")
        params.append(f"%{school}%")

    if age_min is not None:
        conditions.append("age >= ?")
        params.append(age_min)

    if age_max is not None:
        conditions.append("age <= ?")
        params.append(age_max)

    if gender:
        conditions.append("gender = ?")
        params.append(gender)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT * FROM patients
        {where_clause}
        ORDER BY name COLLATE NOCASE
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


def count_patients(patient_type: str = None) -> int:
    """Total patient count, optionally filtered by type."""
    if patient_type:
        sql = "SELECT COUNT(*) FROM patients WHERE type = ?"
        params = (patient_type,)
    else:
        sql = "SELECT COUNT(*) FROM patients"
        params = ()
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchone()[0]
    finally:
        conn.close()


def get_distinct_schools() -> list[str]:
    """All unique school names — for filter dropdowns."""
    sql = "SELECT DISTINCT school FROM patients WHERE school IS NOT NULL ORDER BY school"
    conn = get_connection()
    try:
        return [r[0] for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  UPDATE
# ─────────────────────────────────────────────────────────────────────────────

def update_patient(
    patient_id: int,
    name: str = None,
    patient_type: str = None,
    school: str = None,
    mobile: str = None,
    dob: str = None,
    gender: str = None,
    blood_group: str = None,
    address: str = None,
) -> bool:
    """
    Partial update — only non-None values are changed.
    Returns True if a row was actually modified.
    """
    fields = {}
    if name        is not None: fields["name"]        = name.strip()
    if patient_type is not None: fields["type"]        = patient_type
    if school      is not None: fields["school"]       = school
    if mobile      is not None: fields["mobile"]       = mobile
    if dob         is not None: 
        fields["dob"] = dob
        fields["age"] = calculate_age(dob)
    if gender      is not None: fields["gender"]       = gender
    if blood_group is not None: fields["blood_group"]  = blood_group
    if address     is not None: fields["address"]      = address

    if not fields:
        return False

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    sql = f"UPDATE patients SET {set_clause} WHERE id = ?"
    params = list(fields.values()) + [patient_id]

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

def delete_patient(patient_id: int) -> bool:
    """
    Hard-delete a patient.
    Cascades to their visits (ON DELETE CASCADE defined in schema).
    Returns True if a row was deleted.
    """
    sql = "DELETE FROM patients WHERE id = ?"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (patient_id,))
        conn.commit()
        logger.info(f"Patient deleted: id={patient_id}")
        return cursor.rowcount > 0
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  STATS (for dashboard / reports)
# ─────────────────────────────────────────────────────────────────────────────

def get_patient_stats() -> dict:
    """
    Returns summary counts useful for a dashboard widget.
    {
        total, students, staff,
        male, female, other_gender
    }
    """
    sql = """
        SELECT
            COUNT(*)                                AS total,
            SUM(CASE WHEN type = 'Student' THEN 1 ELSE 0 END) AS students,
            SUM(CASE WHEN type = 'Staff'   THEN 1 ELSE 0 END) AS staff,
            SUM(CASE WHEN gender = 'Male'  THEN 1 ELSE 0 END) AS male,
            SUM(CASE WHEN gender = 'Female' THEN 1 ELSE 0 END) AS female
        FROM patients
    """
    conn = get_connection()
    try:
        row = conn.execute(sql).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()