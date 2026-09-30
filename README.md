# NMIMS Clinica

## Overview
NMIMS Clinica is a comprehensive, desktop-based Clinic Management System (CMS) designed specifically for the NMIMS campus clinic. Built with a modern technology stack (Python, PySide6, and SQLite), it provides an intuitive interface for managing patient records, clinical consultations, medical inventory, and generating detailed analytical reports.

## Key Features
- **Patient Management**: Complete demographic tracking (Students, Staff, Faculty), medical history, and clinical timelines.
- **Consultation Records**: Detailed visit logging, vital signs tracking, doctor/nurse diagnosis, and custom disease categorization.
- **Inventory & Pharmacy**: Real-time stock tracking for medicines and equipment, low-stock alerts, expiry monitoring, and automated dispensing logs.
- **Advanced Reporting**: Multi-threaded, Excel-based data exports for patients, visits, inventory, and clinic analytics (filtered by month and year, or all-time).
- **Medical Documentation**: Automated PDF generation and formatting for medical certificates and consultation records.

## Technology Stack
- **Language**: Python 3.10+
- **GUI Framework**: PySide6 (Qt for Python)
- **Database**: SQLite (with Write-Ahead Logging for high concurrency and safety)
- **Data Export & Reporting**: `openpyxl` (Excel), `PyMuPDF` (PDF generation)
- **Packaging**: PyInstaller

## Prerequisites
- **Python**: v3.10 or newer.
- **Operating System**: Windows 10/11, macOS, or Linux.
- **Hardware Requirements**: Minimum 512 MB RAM, ~200 MB disk space.

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd nmims-clinica
```

### 2. Environment Setup
It is highly recommended to use a Python virtual environment to manage dependencies.

**Windows:**
```cmd
python -m venv venv
.\venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Running the Application
To launch the application in development mode:
```bash
python main.py
```
Upon the first launch, the application will automatically initialize the database schema and seed default operational data (such as disease categories and medicine subtypes).

### Database Storage
For seamless operation across environments and to ensure data persistence through updates, the core database (`clinica.db`) is stored safely in the user's application data directory:
- **Windows**: `%APPDATA%\NmimsClinica\clinica.db`
- **macOS / Linux**: `~/.local/share/NmimsClinica/clinica.db` (or equivalent based on the host platform)

## Building for Production
To distribute the application as a standalone executable (without requiring a Python installation on the target machine), use PyInstaller.

**Using the spec file:**
```bash
pyinstaller "NMIMS Clinica.spec"
```
**Alternatively, using the command line:**
```bash
pyinstaller --noconfirm --onefile --windowed --name "NMIMS Clinica" --icon "assets/icons/logo.png" --add-data "assets;assets" main.py
```
The compiled standalone application will be generated in the `dist/` directory.

## Project Architecture
The codebase strictly adheres to the Model-View-Controller (MVC) paradigm and separation of concerns to ensure maintainability and scalability.

- `main.py` - Application entry point. Handles bootstrapping and window initialization.
- `database/` - Data Access Layer (DAL). Contains raw SQLite queries, connection pooling, and schema migrations.
- `models/` - Domain models (Python `dataclasses`) with built-in validation rules.
- `ui/` - Presentation Layer. Contains all PySide6 widgets, screens, and application windows.
- `exports/` - Dedicated module for handling asynchronous/threaded Excel exports and reporting, preventing UI freezes during large operations.
- `utils/` - Shared utilities, including PDF certificate generation and global input validators.
- `assets/` - Static resources (branding, logos, icons).

## Documentation & Terminology
- **SAP ID**: The unique identification number used for NMIMS Students and Staff. This acts as the primary lookup key.
- **Visit / Consultation**: Interchangeable terms referring to a single clinical encounter by a patient.
- **Dispense**: The act of issuing medication to a patient from the inventory. This action automatically deducts the quantity from the `current_stock` in the database.
- **Follow-up**: A scheduled subsequent visit flagged during a consultation. Follow-ups are tracked heavily on the main dashboard.
- **Medical Leave / Rest Days**: Clinical advice given to a patient, tracked strictly within the visit record, and fully exportable for university administration purposes.
- **Disease Category**: A grouping classification for illnesses (e.g., Respiratory, Gastrointestinal). Can be predefined or dynamically added during a consultation.

## License
Refer to the `LICENSE` file for distribution terms and conditions.

---
*Developed for NMIMS Clinic Operations.*
