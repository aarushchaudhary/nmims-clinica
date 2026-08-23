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
import shutil
import sys

logger = logging.getLogger(__name__)

# ── DB path handling ──────────────────────────────────────────────────────────

def get_db_path():
    if sys.platform == 'win32':
        # Get the user's AppData/Roaming directory
        base_dir = os.getenv('APPDATA')
        if not base_dir:
            base_dir = os.path.expanduser("~")
    else:
        # For Linux and macOS, store in Documents folder
        base_dir = os.path.join(os.path.expanduser("~"), "Documents")
        
    app_dir = os.path.join(base_dir, 'NmimsClinica')
    
    # Create the directory if it doesn't exist
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)
        
    db_path = os.path.join(app_dir, 'clinica.db')
    
    # If the database doesn't exist in AppData, copy the blank one from your installation folder
    if not os.path.exists(db_path):
        # Determine if running as a script or a frozen PyInstaller executable
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        initial_db = os.path.join(base_dir, 'database', 'clinica.db')
        if os.path.exists(initial_db):
            shutil.copy2(initial_db, db_path)
            
    return db_path


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
    conn = sqlite3.connect(os.path.normpath(get_db_path()))
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
    clinic_reg_no TEXT,
    day_care_reg_no TEXT,
    opd_timing TEXT,
    opd_reg_no TEXT,
    employee_id TEXT,
    emp_code TEXT,
    emp_name TEXT,
    name        TEXT    NOT NULL,
    type        TEXT    NOT NULL CHECK(type IN ('Student', 'Staff')),
    school      TEXT,
    mobile      TEXT,
    tel         TEXT,
    dob         TEXT,
    age         INTEGER, -- Legacy, kept for backwards compatibility
    age_months  INTEGER,
    gender      TEXT    CHECK(gender IN ('Male', 'Female', 'Other')),
    sex         TEXT,
    blood_group TEXT,
    height      TEXT,
    weight      TEXT,
    address     TEXT,
    brought_by  TEXT,
    relation    TEXT,
    brought_by_name TEXT,
    chief_complaint_1 TEXT,
    chief_complaint_2 TEXT,
    chief_complaint_3 TEXT,
    chief_complaint_4 TEXT,
    past_high_blood_pressure TEXT,
    past_chest_pain TEXT,
    past_shortness_of_breath TEXT,
    past_asthma TEXT,
    past_ulcer_peptic TEXT,
    past_diabetes TEXT,
    past_major_illness_surgery TEXT,
    family_high_blood_pressure TEXT,
    family_diabetes TEXT,
    family_cardiac_disorder TEXT,
    family_genetic_disorder TEXT,
    other_relevant_history TEXT,
    blood_pressure TEXT,
    pulse TEXT,
    resp_rate TEXT,
    general_appearance TEXT,
    eyes_right TEXT,
    eyes_left TEXT,
    colour_vision_right TEXT,
    colour_vision_left TEXT,
    ears_inspection TEXT,
    ears_hearing TEXT,
    cvs TEXT,
    per_abdomen TEXT,
    chest TEXT,
    exam_date TEXT,
    doctor_name TEXT,
    diagnosis TEXT,
    admission_referral_date TEXT,
    advise TEXT,
    letter_date TEXT,
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
    dosage                  TEXT,
    strength_mg             INTEGER,

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
    visit_id        INTEGER REFERENCES visits(id) ON DELETE CASCADE,
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
]


PATIENT_EXTRA_COLUMNS = {
    "clinic_reg_no": "TEXT",
    "day_care_reg_no": "TEXT",
    "opd_timing": "TEXT",
    "opd_reg_no": "TEXT",
    "employee_id": "TEXT",
    "emp_code": "TEXT",
    "emp_name": "TEXT",
    "tel": "TEXT",
    "age_months": "INTEGER",
    "sex": "TEXT",
    "height": "TEXT",
    "weight": "TEXT",
    "brought_by": "TEXT",
    "relation": "TEXT",
    "brought_by_name": "TEXT",
    "chief_complaint_1": "TEXT",
    "chief_complaint_2": "TEXT",
    "chief_complaint_3": "TEXT",
    "chief_complaint_4": "TEXT",
    "past_high_blood_pressure": "TEXT",
    "past_chest_pain": "TEXT",
    "past_shortness_of_breath": "TEXT",
    "past_asthma": "TEXT",
    "past_ulcer_peptic": "TEXT",
    "past_diabetes": "TEXT",
    "past_major_illness_surgery": "TEXT",
    "family_high_blood_pressure": "TEXT",
    "family_diabetes": "TEXT",
    "family_cardiac_disorder": "TEXT",
    "family_genetic_disorder": "TEXT",
    "other_relevant_history": "TEXT",
    "blood_pressure": "TEXT",
    "pulse": "TEXT",
    "resp_rate": "TEXT",
    "general_appearance": "TEXT",
    "eyes_right": "TEXT",
    "eyes_left": "TEXT",
    "colour_vision_right": "TEXT",
    "colour_vision_left": "TEXT",
    "ears_inspection": "TEXT",
    "ears_hearing": "TEXT",
    "cvs": "TEXT",
    "per_abdomen": "TEXT",
    "chest": "TEXT",
    "exam_date": "TEXT",
    "doctor_name": "TEXT",
    "diagnosis": "TEXT",
    "admission_referral_date": "TEXT",
    "advise": "TEXT",
    "letter_date": "TEXT",
    "has_past_history": "TEXT",
    "has_family_history": "TEXT",
    "family_relation": "TEXT",
    "year": "TEXT",
}


def _ensure_patient_extra_columns(conn: sqlite3.Connection):
    existing = {
        row["name"] for row in conn.execute("PRAGMA table_info(patients)").fetchall()
    }
    for column, col_type in PATIENT_EXTRA_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE patients ADD COLUMN {column} {col_type}")


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
    logger.info(f"Initializing database at: {os.path.normpath(get_db_path())}")
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        _ensure_patient_extra_columns(conn)
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
