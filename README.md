# NMIMS Clinica - Clinic Management Software

A custom-built Python GUI application for campus clinical management using **PySide6** and **SQLite**.

## Features

- **Consultations:** Record diagnosis ('Diagnosed by Doctor', 'Diagnosed by Nurse'), prescribed items, and clinical notes.
- **Patient Management:** Track patient history with demographic records including explicit Date of Birth (DOB).
- **Inventory System:** Direct linkage between the campus pharmacy/disposables and the actual clinic visits.

## Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- Windows, macOS, or Linux.

## Installation

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd cms
   ```

2. Setup virtual environment:
   ```bash
   py -m venv venv
   .\venv\Scripts\activate  # On Windows
   # source venv/bin/activate # On Unix/MacOS
   ```

3. Install requirements
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Execute the entry point module:

```bash
py main.py
```

The database (`clinic.db`) is automatically initialized locally upon first execution. 

## Structure
- \`main.py\`: Application entry-point and UI initialization
- \`database/\`: SQLite database connection pools and queries
- \`ui/\`: PySide6 GUI models
- \`assets/\`: Brand elements and icons
