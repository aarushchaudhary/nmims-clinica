"""
inventory_queries.py
--------------------
All SQL operations for the Inventory module.

Covers:
  - Medicines (CRUD, stock updates, expiry tracking)
  - Dispense log (per visit or manual)
  - Equipment / Instruments
  - Inventory statistics and export helpers
"""

import sqlite3
import logging
from datetime import date, timedelta
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


def _today_str() -> str:
    return date.today().isoformat()


def _expiry_threshold(months: int) -> str:
    """ISO date string `months` months from today."""
    approx_days = months * 30
    return (date.today() + timedelta(days=approx_days)).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
#  MEDICINE SUBTYPES  (read-only lookups for dropdowns)
# ─────────────────────────────────────────────────────────────────────────────

def get_medicine_subtypes() -> list[dict]:
    sql = "SELECT * FROM medicine_subtypes ORDER BY name"
    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql).fetchall())
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  MEDICINES — CREATE
# ─────────────────────────────────────────────────────────────────────────────

def add_medicine(
    name: str,
    expiry_date: str,              # Required — 'YYYY-MM-DD'
    subtype_id: int = None,
    batch_number: str = None,
    stock_received: int = 0,
    mfg_date: str = None,          # 'YYYY-MM-DD'
    minimum_stock_alert: int = 10,
    supplier: str = None,
    notes: str = None,
) -> int:
    """
    Add a new medicine to inventory.
    current_stock is set equal to stock_received on creation.
    Returns new medicine id.
    """
    sql = """
        INSERT INTO medicines (
            name, subtype_id, batch_number,
            stock_received, current_stock, minimum_stock_alert,
            mfg_date, expiry_date,
            supplier, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (
            name.strip(), subtype_id, batch_number,
            stock_received, stock_received, minimum_stock_alert,
            mfg_date, expiry_date,
            supplier, notes
        ))
        conn.commit()
        logger.info(f"Medicine added: '{name}', id={cursor.lastrowid}")
        return cursor.lastrowid
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  MEDICINES — READ
# ─────────────────────────────────────────────────────────────────────────────

def get_medicine_by_id(medicine_id: int) -> Optional[dict]:
    sql = """
        SELECT m.*, s.name AS subtype_name
        FROM medicines m
        LEFT JOIN medicine_subtypes s ON s.id = m.subtype_id
        WHERE m.id = ?
    """
    conn = get_connection()
    try:
        row = conn.execute(sql, (medicine_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_all_medicines(order_by: str = "name") -> list[dict]:
    """All medicines with subtype name joined, no expiry filter."""
    allowed = {"name", "expiry_date", "current_stock", "created_at"}
    order_by = order_by if order_by in allowed else "name"
    sql = f"""
        SELECT m.*, s.name AS subtype_name
        FROM medicines m
        LEFT JOIN medicine_subtypes s ON s.id = m.subtype_id
        ORDER BY m.{order_by} COLLATE NOCASE
    """
    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql).fetchall())
    finally:
        conn.close()


def search_medicines(
    query: str = None,
    subtype_id: int = None,
    low_stock_only: bool = False,
    expiring_in_months: int = None,    # e.g. 2 → expiring within 2 months
    expired_only: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """
    Filterable medicine list.
    `query` matches against name and batch_number.
    Expiry filters are exclusive — use one at a time or combine carefully.
    """
    conditions = []
    params = []

    if query:
        like = f"%{query.strip()}%"
        conditions.append(
            "(m.name LIKE ? COLLATE NOCASE OR m.batch_number LIKE ?)"
        )
        params.extend([like, like])

    if subtype_id is not None:
        conditions.append("m.subtype_id = ?")
        params.append(subtype_id)

    if low_stock_only:
        conditions.append("m.current_stock <= m.minimum_stock_alert")

    if expired_only:
        conditions.append("m.expiry_date < ?")
        params.append(_today_str())
    elif expiring_in_months is not None:
        threshold = _expiry_threshold(expiring_in_months)
        conditions.append("m.expiry_date >= ? AND m.expiry_date <= ?")
        params.extend([_today_str(), threshold])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT m.*, s.name AS subtype_name
        FROM medicines m
        LEFT JOIN medicine_subtypes s ON s.id = m.subtype_id
        {where}
        ORDER BY m.expiry_date ASC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  MEDICINES — EXPIRY INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────

def get_expiring_soon(months: int = 2) -> list[dict]:
    """
    Medicines expiring within `months` months from today (but not yet expired).
    Default: 2 months (matching your spec).
    """
    return search_medicines(expiring_in_months=months)


def get_expired_medicines() -> list[dict]:
    """All medicines whose expiry_date has already passed."""
    return search_medicines(expired_only=True)


def get_low_stock_medicines() -> list[dict]:
    """Medicines at or below their minimum_stock_alert threshold."""
    return search_medicines(low_stock_only=True)


# ─────────────────────────────────────────────────────────────────────────────
#  MEDICINES — UPDATE
# ─────────────────────────────────────────────────────────────────────────────

def update_medicine(
    medicine_id: int,
    name: str = None,
    subtype_id: int = None,
    batch_number: str = None,
    stock_received: int = None,
    current_stock: int = None,
    minimum_stock_alert: int = None,
    mfg_date: str = None,
    expiry_date: str = None,
    supplier: str = None,
    notes: str = None,
) -> bool:
    """Partial update. Returns True if a row was modified."""
    fields = {}
    if name                 is not None: fields["name"]                 = name.strip()
    if subtype_id           is not None: fields["subtype_id"]           = subtype_id
    if batch_number         is not None: fields["batch_number"]         = batch_number
    if stock_received       is not None: fields["stock_received"]       = stock_received
    if current_stock        is not None: fields["current_stock"]        = current_stock
    if minimum_stock_alert  is not None: fields["minimum_stock_alert"]  = minimum_stock_alert
    if mfg_date             is not None: fields["mfg_date"]             = mfg_date
    if expiry_date          is not None: fields["expiry_date"]          = expiry_date
    if supplier             is not None: fields["supplier"]             = supplier
    if notes                is not None: fields["notes"]                = notes

    if not fields:
        return False

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    sql = f"UPDATE medicines SET {set_clause} WHERE id = ?"
    params = list(fields.values()) + [medicine_id]

    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def restock_medicine(medicine_id: int, quantity_added: int) -> bool:
    """
    Add stock to an existing medicine entry.
    Updates both stock_received total and current_stock.
    """
    sql = """
        UPDATE medicines
        SET stock_received  = stock_received  + ?,
            current_stock   = current_stock   + ?
        WHERE id = ?
    """
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (quantity_added, quantity_added, medicine_id))
        conn.commit()
        logger.info(f"Restocked medicine id={medicine_id} by {quantity_added}")
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_medicine(medicine_id: int) -> bool:
    sql = "DELETE FROM medicines WHERE id = ?"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (medicine_id,))
        conn.commit()
        logger.info(f"Medicine deleted: id={medicine_id}")
        return cursor.rowcount > 0
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  DISPENSE LOG
# ─────────────────────────────────────────────────────────────────────────────

def dispense_medicine(
    medicine_id: int,
    quantity: int,
    visit_id: int = None,
    dispensed_by: str = None,
    notes: str = None,
    is_post_expiry: bool = False,      # Safety flag
) -> int:
    """
    Log a dispense event.
    The DB trigger automatically deducts `quantity` from medicines.current_stock.
    If is_post_expiry=True, increments medicines.dispensed_after_expiry.
    Returns dispense log id.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO medicine_dispenses
                (medicine_id, visit_id, quantity, dispensed_by, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (medicine_id, visit_id, quantity, dispensed_by, notes)
        )

        if is_post_expiry:
            conn.execute(
                "UPDATE medicines SET dispensed_after_expiry = dispensed_after_expiry + ? WHERE id = ?",
                (quantity, medicine_id)
            )

        conn.commit()
        logger.info(
            f"Dispensed medicine id={medicine_id}, qty={quantity}, "
            f"visit_id={visit_id}, post_expiry={is_post_expiry}"
        )
        return cursor.lastrowid
    finally:
        conn.close()


def get_dispense_log(
    medicine_id: int = None,
    visit_id: int = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """Filterable dispense history with medicine name and patient joined."""
    conditions = []
    params = []

    if medicine_id is not None:
        conditions.append("d.medicine_id = ?")
        params.append(medicine_id)

    if visit_id is not None:
        conditions.append("d.visit_id = ?")
        params.append(visit_id)

    if date_from:
        conditions.append("DATE(d.dispensed_at) >= ?")
        params.append(date_from)

    if date_to:
        conditions.append("DATE(d.dispensed_at) <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            d.*,
            m.name          AS medicine_name,
            p.name          AS patient_name,
            p.sap_id        AS patient_sap_id
        FROM medicine_dispenses d
        JOIN medicines  m ON m.id = d.medicine_id
        LEFT JOIN visits     v ON v.id = d.visit_id
        LEFT JOIN patients   p ON p.id = v.patient_id
        {where}
        ORDER BY d.dispensed_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  EQUIPMENT
# ─────────────────────────────────────────────────────────────────────────────

def add_equipment(
    name: str,
    category: str = "Instrument",     # 'Instrument' | 'Equipment' | 'Miscellaneous'
    quantity: int = 0,
    disposal_required: bool = False,
    purchase_date: str = None,
    last_serviced_date: str = None,
    notes: str = None,
) -> int:
    """Add a new equipment/instrument record. Returns new id."""
    sql = """
        INSERT INTO equipment
            (name, category, quantity, disposal_required,
             purchase_date, last_serviced_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (
            name.strip(), category, quantity,
            1 if disposal_required else 0,
            purchase_date, last_serviced_date, notes
        ))
        conn.commit()
        logger.info(f"Equipment added: '{name}', id={cursor.lastrowid}")
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_equipment(category: str = None) -> list[dict]:
    """All equipment, optionally filtered by category."""
    if category:
        sql = "SELECT * FROM equipment WHERE category = ? ORDER BY name COLLATE NOCASE"
        params = (category,)
    else:
        sql = "SELECT * FROM equipment ORDER BY name COLLATE NOCASE"
        params = ()
    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


def search_equipment(
    query: str = None,
    category: str = None,
    disposal_required: bool = None,
    low_quantity_threshold: int = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """Filter equipment by name, category, disposal flag, or low quantity."""
    conditions = []
    params = []

    if query:
        conditions.append("name LIKE ? COLLATE NOCASE")
        params.append(f"%{query.strip()}%")

    if category:
        conditions.append("category = ?")
        params.append(category)

    if disposal_required is not None:
        conditions.append("disposal_required = ?")
        params.append(1 if disposal_required else 0)

    if low_quantity_threshold is not None:
        conditions.append("quantity <= ?")
        params.append(low_quantity_threshold)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM equipment {where} ORDER BY name COLLATE NOCASE"

    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


def update_equipment(
    equipment_id: int,
    name: str = None,
    category: str = None,
    quantity: int = None,
    disposal_required: bool = None,
    purchase_date: str = None,
    last_serviced_date: str = None,
    notes: str = None,
) -> bool:
    fields = {}
    if name               is not None: fields["name"]               = name.strip()
    if category           is not None: fields["category"]           = category
    if quantity           is not None: fields["quantity"]           = quantity
    if disposal_required  is not None: fields["disposal_required"]  = 1 if disposal_required else 0
    if purchase_date      is not None: fields["purchase_date"]      = purchase_date
    if last_serviced_date is not None: fields["last_serviced_date"] = last_serviced_date
    if notes              is not None: fields["notes"]              = notes

    if not fields:
        return False

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    sql = f"UPDATE equipment SET {set_clause} WHERE id = ?"
    params = list(fields.values()) + [equipment_id]

    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_equipment(equipment_id: int) -> bool:
    sql = "DELETE FROM equipment WHERE id = ?"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, (equipment_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  INVENTORY STATS  (for dashboard / reports)
# ─────────────────────────────────────────────────────────────────────────────

def get_inventory_stats() -> dict:
    """
    Summary for a dashboard widget.
    {
        total_medicines, expired_count, expiring_soon_count,
        low_stock_count, total_equipment, disposal_needed_count
    }
    """
    today = _today_str()
    threshold = _expiry_threshold(2)

    sql = """
        SELECT
            (SELECT COUNT(*) FROM medicines)                           AS total_medicines,
            (SELECT COUNT(*) FROM medicines WHERE expiry_date < ?)    AS expired_count,
            (SELECT COUNT(*) FROM medicines
             WHERE expiry_date >= ? AND expiry_date <= ?)              AS expiring_soon_count,
            (SELECT COUNT(*) FROM medicines
             WHERE current_stock <= minimum_stock_alert)               AS low_stock_count,
            (SELECT COUNT(*) FROM equipment)                           AS total_equipment,
            (SELECT COUNT(*) FROM equipment WHERE disposal_required=1) AS disposal_needed_count
    """
    conn = get_connection()
    try:
        row = conn.execute(sql, (today, today, threshold)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_medicines_for_export(
    expired_only: bool = False,
    expiring_in_months: int = None,
) -> list[dict]:
    """
    Full medicine data for Excel export.
    Can be filtered or return everything.
    """
    conditions = []
    params = []

    if expired_only:
        conditions.append("m.expiry_date < ?")
        params.append(_today_str())
    elif expiring_in_months is not None:
        threshold = _expiry_threshold(expiring_in_months)
        conditions.append("m.expiry_date >= ? AND m.expiry_date <= ?")
        params.extend([_today_str(), threshold])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            m.id,
            m.name,
            s.name          AS subtype,
            m.batch_number,
            m.stock_received,
            m.current_stock,
            m.minimum_stock_alert,
            m.mfg_date,
            m.expiry_date,
            m.dispensed_after_expiry,
            m.supplier,
            m.notes,
            m.created_at
        FROM medicines m
        LEFT JOIN medicine_subtypes s ON s.id = m.subtype_id
        {where}
        ORDER BY m.expiry_date ASC
    """
    conn = get_connection()
    try:
        return _rows_to_list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()