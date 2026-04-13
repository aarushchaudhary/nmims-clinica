import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from database.db_manager import initialize_db
from ui.main_window import MainWindow

def main():
    initialize_db()  # Creates DB + tables on first run
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Consistent cross-platform look
    
    app.setWindowIcon(QIcon("assets/icons/logo.png"))
    
    window = MainWindow()
    window.setWindowIcon(QIcon("assets/icons/logo.png"))
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()