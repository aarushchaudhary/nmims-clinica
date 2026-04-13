"""
db_manager.py
-------------
Central database manager.
Handles:
  - Connection creation
  - Full schema initialization
  - Default data seeding
  - Schema migration support
"""

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

# ── DB file lives next to the running executable (or project root in dev) ──────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'clinic.db')


# ─────────────────────────────────────────────
#  CONNECTION
# ─────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """
    Returns a new SQLite connection.
    - row_factory = sqlite3.Row  →  access columns by name (row['name'])
    - foreign keys enforced
    - WAL mode for better concurrent read performance
    """
    conn = sqlite3.connect(os.path.normpath(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ─────────────────────────────────────────────
#  SCHEMA
# ─────────────────────────────────────────────

SCHEMA_SQL = """
-- ── META ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT DEFAULT (datetime('now'))
);

-- ── PATIENTS ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sap_id      TEXT    UNIQUE NOT NULL,
    name        TEXT    NOT NULL,
    type        TEXT    NOT NULL CHECK(type IN ('Student', 'Staff')),
    school      TEXT,
    mobile      TEXT,
    dob         TEXT,
    age         INTEGER, -- Legacy, kept for backwards compatibility
    gender      TEXT    CHECK(gender IN ('Male', 'Female', 'Other')),
    blood_group TEXT,
    address     TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_patients_sap_id ON patients(sap_id);
CREATE INDEX IF NOT EXISTS idx_patients_name   ON patients(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_patients_type   ON patients(type);

-- ── DISEASE CATEGORIES ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS disease_categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    UNIQUE NOT NULL,
    is_custom   INTEGER NOT NULL DEFAULT 0,   -- 1 = added by doctor at runtime
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── VISITS / CONSULTATIONS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS visits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    visit_date      TEXT    NOT NULL DEFAULT (datetime('now')),
    visit_type      TEXT    NOT NULL DEFAULT 'Walk-in'
                    CHECK(visit_type IN ('Walk-in', 'Scheduled', 'Emergency')),

    -- Clinical data
    chief_complaint     TEXT,
    diagnosis           TEXT,
    category_id         INTEGER REFERENCES disease_categories(id),
    investigations      TEXT,
    treatment           TEXT,
    prescription        TEXT,

    -- Outcomes
    referral            TEXT,           -- NULL = no referral, else 'Hospital / Specialist name'
    rest_days           INTEGER DEFAULT 0,
    medical_leave       INTEGER NOT NULL DEFAULT 0 CHECK(medical_leave IN (0, 1)),
    ambulance_used      INTEGER NOT NULL DEFAULT 0 CHECK(ambulance_used IN (0, 1)),
    
    diagnosed_by        TEXT NOT NULL DEFAULT 'Doctor' CHECK(diagnosed_by IN ('Doctor', 'Nurse')),

    follow_up_date      TEXT,
    notes               TEXT,

    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_visits_patient_id  ON visits(patient_id);
CREATE INDEX IF NOT EXISTS idx_visits_visit_date  ON visits(visit_date);
CREATE INDEX IF NOT EXISTS idx_visits_category_id ON visits(category_id);

-- ── MEDICINE SUBTYPES (lookup) ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS medicine_subtypes (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    UNIQUE NOT NULL
);

-- ── MEDICINES ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS medicines (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT    NOT NULL,
    subtype_id              INTEGER REFERENCES medicine_subtypes(id),
    batch_number            TEXT,

    -- Stock lifecycle
    stock_received          INTEGER NOT NULL DEFAULT 0 CHECK(stock_received >= 0),
    current_stock           INTEGER NOT NULL DEFAULT 0 CHECK(current_stock >= 0),
    minimum_stock_alert     INTEGER NOT NULL DEFAULT 10,

    -- Dates
    mfg_date                TEXT,
    expiry_date             TEXT    NOT NULL,

    -- Safety tracking
    dispensed_after_expiry  INTEGER NOT NULL DEFAULT 0 CHECK(dispensed_after_expiry >= 0),

    -- Audit
    supplier                TEXT,
    notes                   TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_medicines_name        ON medicines(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_medicines_expiry_date ON medicines(expiry_date);
CREATE INDEX IF NOT EXISTS idx_medicines_subtype_id  ON medicines(subtype_id);

-- ── MEDICINE DISPENSING LOG ───────────────────────────────────────────────
-- Tracks every time medicine is given out (links to a visit optionally)
CREATE TABLE IF NOT EXISTS medicine_dispenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id     INTEGER NOT NULL REFERENCES medicines(id),
    visit_id        INTEGER REFERENCES visits(id),
    quantity        INTEGER NOT NULL CHECK(quantity > 0),
    dispensed_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    dispensed_by    TEXT,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_dispenses_medicine_id ON medicine_dispenses(medicine_id);
CREATE INDEX IF NOT EXISTS idx_dispenses_visit_id    ON medicine_dispenses(visit_id);

-- ── EQUIPMENT / INSTRUMENTS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS equipment (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL,
    category            TEXT    DEFAULT 'Instrument'
                        CHECK(category IN ('Instrument', 'Equipment', 'Miscellaneous')),
    quantity            INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    disposal_required   INTEGER NOT NULL DEFAULT 0 CHECK(disposal_required IN (0, 1)),
    purchase_date       TEXT,
    last_serviced_date  TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── TRIGGERS: keep updated_at current ─────────────────────────────────────
CREATE TRIGGER IF NOT EXISTS trg_patients_updated
    AFTER UPDATE ON patients
    BEGIN
        UPDATE patients SET updated_at = datetime('now') WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS trg_visits_updated
    AFTER UPDATE ON visits
    BEGIN
        UPDATE visits SET updated_at = datetime('now') WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS trg_medicines_updated
    AFTER UPDATE ON medicines
    BEGIN
        UPDATE medicines SET updated_at = datetime('now') WHERE id = NEW.id;
    END;

-- ── TRIGGER: auto-deduct stock on dispense ────────────────────────────────
CREATE TRIGGER IF NOT EXISTS trg_deduct_stock_on_dispense
    AFTER INSERT ON medicine_dispenses
    BEGIN
        UPDATE medicines
        SET current_stock = current_stock - NEW.quantity
        WHERE id = NEW.medicine_id;
    END;
"""


# ─────────────────────────────────────────────
#  SEED DATA
# ─────────────────────────────────────────────

DEFAULT_DISEASE_CATEGORIES = [
    'Abdominal Disease',
    'Chest Disease',
    'Bones/Joint',
    'Infectious Disease',
    'Neurological Disease',
    'Liver Disease',
    'Kidney Disease',
    'Systemic Disease',
    'Hypertension',
    'Diabetes',
    'Gastroenteritis',
    'Sore Throat & Bronchitis',
    'Eye & ENT',
    'Orthopaedics',
    'Gynaecology',
    'Skin Disease',
    'Psychiatric',
    'Dental',
    'General / Other',
]

DEFAULT_MEDICINE_SUBTYPES = [
    'Tablet',
    'Capsule',
    'Injection',
    'Sachet',
    'Powder',
    'Liquid / Syrup',
    'Drops',
    'Ointment',
    'Cream',
    'Band-Aid / Dressing',
    'IV Drip',
    'Inhaler',
    'Suppository',
]


def _seed_defaults(conn: sqlite3.Connection):
    cursor = conn.cursor()

    for cat in DEFAULT_DISEASE_CATEGORIES:
        cursor.execute(
            "INSERT OR IGNORE INTO disease_categories (name, is_custom) VALUES (?, 0)",
            (cat,)
        )

    for subtype in DEFAULT_MEDICINE_SUBTYPES:
        cursor.execute(
            "INSERT OR IGNORE INTO medicine_subtypes (name) VALUES (?)",
            (subtype,)
        )


# ─────────────────────────────────────────────
#  MIGRATIONS
# ─────────────────────────────────────────────
# Add new migrations here as the app evolves.
# Each entry: (version_number, sql_string)
# initialize_db() applies any migration whose version
# is not yet recorded in schema_version.

MIGRATIONS = [
    # (1, "ALTER TABLE patients ADD COLUMN email TEXT;"),
]


def _apply_migrations(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_version")
    applied = {row[0] for row in cursor.fetchall()}

    for version, sql in MIGRATIONS:
        if version not in applied:
            try:
                cursor.executescript(sql)
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (version,)
                )
                conn.commit()
                logger.info(f"Migration v{version} applied.")
            except Exception as exc:
                conn.rollback()
                logger.error(f"Migration v{version} failed: {exc}")
                raise


# ─────────────────────────────────────────────
#  PUBLIC ENTRY POINT
# ─────────────────────────────────────────────

def initialize_db():
    """
    Call once at app startup (main.py).
    Creates all tables, seeds defaults, applies any pending migrations.
    Safe to call multiple times — all statements are CREATE IF NOT EXISTS.
    """
    logger.info(f"Initializing database at: {os.path.normpath(DB_PATH)}")
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        _seed_defaults(conn)
        conn.commit()
        _apply_migrations(conn)
        logger.info("Database initialized successfully.")
    except Exception as exc:
        conn.rollback()
        logger.critical(f"Database initialization failed: {exc}")
        raise
    finally:
        conn.close()

def run_background_optimizations():
    """
    🔁 BACKGROUND OPTIMISATION TASKS
    - Rebuild indexes (REINDEX)
    - Clean old logs if needed
    - Optimize DB (VACUUM / ANALYZE)
    """
    conn = get_connection()
    try:
        conn.execute("PRAGMA optimize")
        conn.execute("VACUUM")
    except Exception as e:
        logger.error(f"DB Optimisation failed: {e}")
    finally:
        conn.close()
