# NMIMS Clinica - Clinic Management Software

A comprehensive Python desktop application for managing clinical operations, patient records, and medical inventory at NMIMS campus clinic. Built with **PySide6** for a modern native GUI and **SQLite** for reliable data persistence.

**Status**: Production-ready desktop application with multi-module architecture.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Feature Modules](#feature-modules)
- [Database Schema](#database-schema)
- [Export & Reporting](#export--reporting)
- [Development](#development)
- [Building Standalone Executable](#building-standalone-executable)
- [Troubleshooting](#troubleshooting)

---

## Features

### 🏥 **Patient Management**
- Complete patient registration with SAP ID, demographic data, and medical history
- Track patient type (Student/Staff) and school affiliation
- Explicit Date of Birth (DOB) support with automatic age calculation
- Full-text patient search and filtering by type/school
- Patient history timeline with all consultations and follow-ups
- Blood group and allergies documentation

### 📋 **Consultation Management**
- Record consultations with flexible diagnosis types:
  - Diagnosed by Doctor
  - Diagnosed by Nurse
  - Walk-in / Scheduled / Emergency visit types
- Disease category system with predefined categories and custom category creation
- Clinical notes and follow-up tracking
- Vital signs recording (temperature, blood pressure, etc.)
- Inline medicine prescription and inventory dispense tracking
- Real-time consultation history per patient

### 💊 **Inventory System**
- Medicine inventory tracking with batch/lot management
- Equipment & disposables catalog
- Direct linkage between medicines prescribed and inventory depletion
- Expiry date tracking with automatic alerts
- Low stock notifications
- Expiring soon medicine alerts (30-day window)
- Dispense log with audit trail
- Stock reorder recommendations

### 📊 **Dashboard & Alerts**
- Real-time system alerts dashboard
- Critical alerts: Low stock medicines, expiring medications, pending follow-ups
- Quick health overview of clinic operations
- Visual status indicators

### 📈 **Reports & Export**
- **Excel Export Capabilities:**
  - Patient register (all patients with demographics)
  - Consultation records (date-range filterable)
  - Disease summary (visit counts per category)
  - Inventory status (medicines & equipment on separate sheets)
  - Expiry reports (expired + expiring soon)
  - Weekly activity reports
  - Dispense audit logs
- Multi-sheet Excel workbooks with professional formatting
- Date-range filtering for all reports
- Automatic file path generation with timestamps

---

## Prerequisites

- **Python:** 3.10 or higher ([Download](https://www.python.org/downloads/))
- **OS:** Windows, macOS, or Linux
- **Disk Space:** ~200 MB (including Python dependencies)
- **RAM:** 512 MB minimum

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone <repo-url>
cd cms
```

### 2. Create Virtual Environment

**Windows:**
```bash
py -m venv venv
.\venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `PySide6` - Modern Qt GUI framework
- `openpyxl` - Excel file generation
- `Pillow` - Image processing
- `pipinstaller` - Package building utilities

---

## Running the Application

### Development Mode

```bash
py main.py
```

**First Run:**
- The database (`clinica.db`) is automatically initialized
- Database is stored in `%APPDATA%\NmimsClinica\` directory (Windows)
- Schema and tables are created automatically
- Default disease categories and medicine subtypes are seeded
- Application is ready for immediate use

### Database Location

The database file is stored in the user's AppData directory for proper Windows app behavior:
- **Windows:** `C:\Users\<YourUsername>\AppData\Roaming\NmimsClinica\clinica.db`
- **Portable Usage:** If database doesn't exist in AppData, it's copied from the installation directory

### Production Deployment

See [Building Standalone Executable](#building-standalone-executable) for creating a distributable .exe file.

---

## Project Structure

```
cms/
├── main.py                      # Entry point - initializes DB and launches GUI
├── requirements.txt             # Python dependencies
├── LICENSE                      # License file
├── README.md                    # This file
├── NMIMS Clinica.spec          # PyInstaller build configuration
│
├── database/                    # Data layer - queries and connection management
│   ├── __init__.py             # Package initialization
│   ├── db_manager.py           # Connection pooling, schema init, migrations, get_db_path()
│   ├── patient_queries.py       # Patient CRUD, search, statistics queries
│   ├── visit_queries.py         # Consultation/visit queries, disease tracking
│   └── inventory_queries.py     # Medicine, equipment, expiry, stock alert queries
│
├── models/                      # Data models - dataclasses for type safety
│   ├── __init__.py             # Package initialization
│   ├── patient.py              # Patient dataclass with validation
│   ├── visit.py                # Consultation/visit dataclass
│   └── inventory.py            # Medicine, Equipment, DispenseRecord dataclasses
│
├── ui/                         # User interface - PySide6 GUI components
│   ├── __init__.py             # Package initialization
│   ├── main_window.py          # Root application window, navigation sidebar
│   ├── dashboard_page.py       # System alerts and operational overview (HOMEPAGE)
│   ├── reports_page.py         # Report generation and export UI
│   ├── widgets.py              # Reusable styled components (ComboBox, DateEdit, etc.)
│   │
│   ├── patients/               # Patient management module
│   │   ├── patient_list.py     # Searchable patient list with CRUD actions
│   │   ├── patient_form.py     # Add/edit patient dialog with validation
│   │   └── patient_history.py  # Patient history/timeline view
│   │
│   ├── consultations/          # Consultation/visit management module
│   │   ├── consultation_list.py # View and manage consultations
│   │   └── consultation_form.py # Record new consultation with disease/medicine
│   │
│   └── inventory/              # Inventory management module
│       ├── medicine_list.py    # Medicine catalog with stock levels and alerts
│       └── inventory_form.py   # Add/edit medicine and equipment
│
├── exports/                    # Report generation and Excel export
│   ├── excel_exporter.py       # Core export functions (patients, visits, inventory)
│   └── excel_exporter_threaded.py # Multi-threaded export for large datasets
│
├── utils/                      # Utility functions - validation, helpers
│   ├── __init__.py             # Package initialization
│   ├── validators.py           # Form validation with structured error reporting
│   └── consultation_pdf.py     # PDF generation for consultation records
│
├── assets/                     # Static resources
│   └── icons/                  # Application icons and logos
│       └── logo.png           # NMIMS Clinica branding/logo
│
└── build/                      # Build artifacts (created by PyInstaller)
    ├── main/                   # Build intermediate files
    └── NMIMS Clinica/          # Build intermediate files
```

---

## Feature Modules

### 📝 Patient Management

**Files:** `ui/patients/`, `database/patient_queries.py`, `models/patient.py`

**Operations:**
- **Add Patient:** SAP ID, name, type (Student/Staff), school, contact, DOB, gender, blood group
- **Edit Patient:** Update any patient field with validation
- **Search:** Full-text search by name, SAP ID, type, school
- **View History:** Complete consultation history with dates and notes
- **Validation:** SAP ID uniqueness, required fields, data format checks

**Database Tables:**
- `patients` - Core patient records
- `disease_categories` - Disease classification system

### 🏥 Consultation Management

**Files:** `ui/consultations/`, `database/visit_queries.py`, `models/visit.py`

**Operations:**
- **Record Consultation:** Select patient, set visit type, record diagnosis, assign category
- **Add Custom Disease:** Create disease categories on-the-fly during consultation
- **Prescribe Medicine:** Link medicines to consultation and adjust inventory
- **Follow-up Tracking:** Schedule and track follow-up dates
- **View Consultation History:** Complete audit trail of all consultations

**Features:**
- Support for multiple diagnosis types (Doctor-diagnosed, Nurse-diagnosed)
- Dynamic disease category selection with custom additions
- Clinical notes with character limits for compliance
- Vital signs recording (temperature, BP, etc.)

### 💊 Inventory Management

**Files:** `ui/inventory/`, `database/inventory_queries.py`, `models/inventory.py`

**Operations:**
- **Add Medicine:** Name, dosage, batch/lot number, expiry date, quantity, cost
- **Add Equipment:** Equipment name, quantity, cost, category
- **Track Dispense:** Automatic depletion when medicines prescribed in consultations
- **Monitor Expiry:** Alerts for medicines expiring within 30 days
- **Low Stock Alerts:** Configurable low-stock thresholds with email/SMS ready

**Database Tables:**
- `medicines` - Medicine catalog with batch tracking
- `equipment` - Equipment and disposables
- `dispense_log` - Audit trail of all inventory usage
- `medicine_expiry_alerts` - Expiry tracking

### 📊 Reports & Export

**Files:** `exports/excel_exporter.py`, `ui/reports_page.py`

**Available Reports:**

1. **Patient Register** - All patients with full demographics
2. **Consultation Report** - Date-range filtered consultation records
3. **Disease Summary** - Visit counts per disease category
4. **Inventory Status** - Current medicines and equipment (separate sheets)
5. **Expiry Report** - Expired medicines and expiring soon (30-day window)
6. **Weekly Report** - Combined activity summary for a week
7. **Dispense Audit Log** - Complete medicine usage history

**Features:**
- Professional Excel formatting with headers and styles
- Date-range selection for all date-based reports
- Multi-sheet workbooks for complex data
- Automatic file naming with timestamps
- File path generation for opening in Explorer

---

## Database Schema

The application uses **SQLite** with automatic schema initialization in `%APPDATA%\NmimsClinica\clinica.db`.

### Database Initialization

The `db_manager.py` module handles:
- **get_db_path()** - Returns AppData path and ensures directory exists
- **initialize_db()** - Creates schema, tables, indexes on first run
- **_seed_defaults()** - Populates predefined disease categories and medicine subtypes
- **_apply_migrations()** - Applies schema migrations safely
- **get_connection()** - Returns SQLite connection with WAL mode enabled

### Key Tables

**patients**
```
- id (INTEGER PRIMARY KEY)
- sap_id (TEXT UNIQUE) - Student/Staff ID
- name (TEXT) - Full name
- type (TEXT) - 'Student' | 'Staff'
- school (TEXT) - School affiliation
- mobile (TEXT) - Contact number
- dob (TEXT) - Date of birth
- gender (TEXT) - 'Male' | → patients(id) ON DELETE CASCADE
- visit_date (TEXT) - Default: now()
- visit_type (TEXT) - 'Walk-in' | 'Scheduled' | 'Emergency'
- chief_complaint (TEXT)
- diagnosis (TEXT)
- category_id (FOREIGN KEY) → disease_categories(id)
- investigations (TEXT)
- treatment (TEXT)
- prescription (TEXT)
- referral (TEXT) - Hospital/Specialist name or NULL
- rest_days (INTEGER)
- medical_leave (INTEGER) - Boolean
- ambulance_used (INTEGER) - Boolean
- diagnosed_by (TEXT) - 'Doctor' | 'Nurse'
- follow_up_date (TEXT)
- notes (TEXT)
- created_at, updated_at (TEXT)
```

**disease_categories**
```
- id (INTEGER PRIMARY KEY)
- name (TEXT UNIQUE NOT NULL)
- is_custom (INTEGER) - 0 for predefined, 1 for user-added
- created_at (TEXT)
- id (INTEGER PRIMARY KEY)
- patient_id (FOREIGN KEY)
- date (TEXT)
- visit_type (TEXT) - 'Walk-in' | 'Scheduled' | 'Emergency'
- diagnosis_type (TEXT) - 'Diagnosed by Doctor' | 'Diagnosed by Nurse'
- disease_id (FOREIGN KEY)
- clinical_notes (TEXT)
- temperature, blood_pressure, etc. - Vital signs
- follow_up_date (TEXT) - Optional
```

**medicines**
```
- id (INTEGER PRIMARY KEY)
- name (TEXT NOT NULL)
- subtype_id (FOREIGN KEY) → medicine_subtypes(id)
- batch_number (TEXT)
- dosage (TEXT)
- strength_mg (INTEGER)
- stock_received (INTEGER)
- current_stock (INTEGER)
- minimum_stock_alert (INTEGER) - Default: 10
- mfg_date (TEXT)
- expiry_date (TEXT NOT NULL)
- dispensed_after_expiry (INTEGER) - Safety tracking
- supplier (TEXT)
- notes (TEXT)
- created_at, updated_at (TEXT)
```

**medicine_subtypes**
```
- id (INTEGER PRIMARY KEY)
- name (TEXT UNIQUE) - e.g., Tablet, Capsule, Injection, Ointment, etc.
```

**medicine_dispenses**
```
- id (INTEGER PRIMARY KEY)
- medicine_id (FOREIGN KEY) - Links to medicines table
- visit_id (FOREIGN KEY) - Links to visits table (optional)
- quantity (INTEGER)
- dispensed_at (TEXT), expiry_date)
- WAL (Write-Ahead Logging) mode for concurrent access
- Automatic timestamps (created_at, updated_at) with triggers
- Auto-deduction of stock on medicine dispense (trigger)
- Schema versioning for safe migrations
- Check constraints for data integrity

**equipment**
```
- id (INTEGER PRIMARY KEY)
- name (TEXT NOT NULL)
- category (TEXT) - 'Instrument' | 'Equipment' | 'Miscellaneous'
- quantity (INTEGER)
- disposal_required (INTEGER) - Boolean flag
- purchase_date (TEXT)
- last_serviced_date (TEXT)
- notes (TEXT)
- created_at, updated_at (TEXT)
```

**schema_version**
```
- version (INTEGER PRIMARY KEY)
- applied_at (TEXT) - Migration timestamp
```

**Database Features:**
- Foreign key constraints enforced
- Indexes on frequently searched columns (sap_id, name, type)
- WAL (Write-Ahead Logging) mode for concurrent access
- Automatic timestamps (created_at, updated_at)
- Schema versioning for migrations

---

## Export & Reporting

### Exporting Data

All exports are Excel-based with professional formatting:

```python
# Example: Export patients
from exports.excel_exporter import export_patients
path = export_patients()
# Returns: "C:\\Users\\...\\exports\\patients_2026-04-29.xlsx"

# Example: Export consultations with date filter
from exports.excel_exporter import export_visits
path = export_visits(date_from="2026-01-01", date_to="2026-04-29")
```

### Excel Output Features
- Styled headers with professional colors
- Proper column sizing
- Frozen panes for easy scrolling
- Number formatting (currency, dates)
- Multiple sheets for complex reports
- Automatic sheet naming

---

## Development

### Code Organization Principles

1. **Separation of Concerns:**
   - `database/` - Pure SQL queries, no UI logic
   - `models/` - Data containers with validation
   - `ui/` - GUI components only
   - `utils/` - Reusable validation and helpers
   - `exports/` - Report generation

2. **Data Flow:**
   - UI Form → Validation → DB Query → Model → Display/Export
   - Models are never imported by DB layer
   - DB layer returns sqlite3.Row objects, UI converts to Models

3. **Validation Strategy:**
   - All form inputs validated before DB write
   - ValidationResult dataclass returns structured errors
   - Field-level error highlighting in forms
   - Database constraints as secondary safety net

### Adding a New Feature

1. **Database:** Add queries to `database/` module
2. **Model:** Create dataclass in `models/`
3. **Validation:** Add to `utils/validators.py`
4. **UI:** Create form/list widget in `ui/`
5. **Export:** Add export function to `exports/excel_exporter.py` if needed

### Running Tests (Future)

```bash
# Install test dependencies
pip install pytest pytest-qt

# Run tests
pytest tests/
```

---

## Building Standalone Executable

Create a single .exe file for distribution using **PyInstaller** (included in dependencies).

### Build Steps

1. **Ensure all dependencies installed:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Build executable using PyInstaller:**

   **Option A: Using spec file (if main.spec exists):**
   ```bash
   pyinstaller main.spec
   ```

   **Option B: Using command line (Recommended for latest build):**
   ```bash
   pyinstaller --noconfirm --onedir --windowed --name "NMIMS Clinica" --icon "assets/icons/logo.png" --add-data "assets;assets" --add-data "database;database" main.py
   ```

   **Command flags explained:**
   - `--noconfirm` - Skip confirmation prompts
   - `--onedir` - Create executable in a directory (not single file)
   - `--windowed` - Hide console window on startup
   - `--name` - Application name (shown in taskbar/shortcuts)
   - `--icon` - Path to icon file (.png or .ico)
   - `--add-data` - Include non-Python files (assets, database template)

3. **Distribute:**
   - Application .exe located in `dist/NMIMS Clinica/NMIMS Clinica.exe`
   - No Python installation required on target machine
   - Database is created in user's AppData on first run
   - All required assets bundled with executable

### Build Configuration

If using `main.spec` file, it controls:
- Single-file vs. directory output
- Icon embedding
- Hidden imports
- Runtime hooks

### Distribution Checklist
- [ ] Test .exe on clean Windows machine
- [ ] Verify database initialization on first run (`%APPDATA%\NmimsClinica\`)
- [ ] Test all export functions
- [ ] Confirm file dialogs work correctly
- [ ] Check icon displays properly in taskbar

---

## Troubleshooting

### Application Won't Start

**Error: "No module named 'PySide6'"**
```bash
# Solution: Activate virtual environment and install dependencies
.\venv\Scripts\activate
pip install -r requirements.txt
```

**Error: "clinic.db locked"**
```bash
# Solution: Close all instances of the application
# Delete clinic.db-wal and clinic.db-shm files if they exist
# Restart application
```

### Database Issues

**"Foreign key constraint failed"**
- Ensure patient exists before creating consultation
- Check referential integrity in database
- Solution: Run `python -c "from database.db_manager import initialize_db; initialize_db()"`

**"Disk I/O error"**
- Check disk space availability
- Verify database file permissions
- Solution: Move database to different drive or check antivirus blocking

### UI Issues

**Window won't resize / looks cut off**
- Solution: Delete Qt cache: `rm -rf ~/.config/Qt` (Linux) or check screen scaling

**Icons not displaying**
- Solution: Verify `assets/icons/logo.png` exists
- Rebuild executable with correct asset paths

### Export Issues

**"Permission denied" when saving Excel**
- Solution: Ensure write permissions in export folder
- Close any open Excel files

**"No space left on device"**
- Solution: Free disk space or change export location

### Performance

**Application laggy with large patient lists**
- Solution: Add pagination (implement in patient_list.py)
- Index database: Rebuild with `VACUUM` and `ANALYZE`

---

## Support & Contribution

- **Bug Reports:** Document steps to reproduce and include error messages
- **Feature Requests:** Describe use case and expected behavior
- **Pull Requests:** Ensure code follows project structure and includes validation

---

## License

See LICENSE file for terms and conditions.
May 2026  
**Version:** 1.0 (Production with AppData Integra

**Last Updated:** April 2026  
**Version:** 1.0 (Production)
