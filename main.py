import sys
import subprocess
import importlib.util

# Check if running as a compiled standalone executable (frozen)
is_frozen = getattr(sys, 'frozen', False)

if not is_frozen:
    # Dictionary mapping import names to their pip package names
    required_packages = {
        "PySide6": "PySide6",
        "openpyxl": "openpyxl",
        "PIL": "Pillow",
        "fitz": "pymupdf"
    }
    
    missing_packages = []
    for import_name, pip_name in required_packages.items():
        if importlib.util.find_spec(import_name) is None:
            missing_packages.append(pip_name)
            
    if missing_packages:
        print("------------------------------------------------------------")
        print("NMIMS Clinica: Missing required libraries!")
        print(f"Missing: {', '.join(missing_packages)}")
        print("Attempting to install missing requirements automatically...")
        print("------------------------------------------------------------")
        try:
            # Execute pip install inside the active Python environment
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing_packages])
            print("Dependencies installed successfully! Launching application...\n")
        except Exception as e:
            print(f"\nFailed to install dependencies automatically: {e}", file=sys.stderr)
            print("Please run manually: pip install -r requirements.txt", file=sys.stderr)
            sys.exit(1)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from database.db_manager import initialize_db
from database.inventory_queries import expire_medicines_stock
from ui.main_window import MainWindow

def main():
    initialize_db()  # Creates DB + tables on first run
    expire_medicines_stock()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Consistent cross-platform look
    
    app.setWindowIcon(QIcon("assets/icons/logo.png"))
    
    window = MainWindow()
    window.setWindowIcon(QIcon("assets/icons/logo.png"))
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()