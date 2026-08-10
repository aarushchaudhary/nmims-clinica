import sys
import os
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

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from database.db_manager import initialize_db
from database.inventory_queries import expire_medicines_stock
from ui.main_window import MainWindow

def verify_system_requirements():
    """Verify runtime environment, directories, and assets."""
    # Ensure assets directory exists
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir, exist_ok=True)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Consistent cross-platform look

    try:
        verify_system_requirements()
        initialize_db()  # Creates DB + tables on first run
        expire_medicines_stock()
    except Exception as exc:
        QMessageBox.critical(
            None,
            "NMIMS Clinica — Startup Error",
            f"Failed to initialize application requirements:\n{exc}"
        )

    # Set Application & Window Icons
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "assets", "icons", "logo.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_dir, "assets", "stmelogo.png")

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()