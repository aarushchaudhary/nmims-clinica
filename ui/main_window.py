"""
main_window.py
--------------
The root application window.
  - Sidebar navigation
  - QStackedWidget holding all module pages
  - Global stylesheet (applied once here, inherited everywhere)
  - Status bar helper used by child widgets
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame,
    QStatusBar, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QColor

# ── Module pages ──────────────────────────────────────────────────────────────
from ui.dashboard_page              import DashboardWidget
from ui.patients.patient_list       import PatientListWidget
from ui.inventory.medicine_list     import MedicineListWidget
from ui.reports_page                import ReportsWidget


# ─────────────────────────────────────────────────────────────────────────────
#  GLOBAL STYLESHEET
#  Define once here — all child widgets inherit it automatically.
# ─────────────────────────────────────────────────────────────────────────────
APP_STYLESHEET = """
/* ── Base ── */
QWidget {
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
    color: #1e293b;
}

QLabel, QCheckBox, QRadioButton {
    background-color: transparent;
}

/* ── Sidebar ── */
#Sidebar {
    background-color: #0f172a;
    border-right: 1px solid #1e293b;
}
#AppTitle {
    color: #38bdf8;
    font-size: 15px;
    font-weight: bold;
    padding: 0 12px;
}
#AppSubtitle {
    color: #64748b;
    font-size: 10px;
    padding: 0 12px;
}
#NavButton {
    color: #94a3b8;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
}
#NavButton:hover {
    background-color: #1e293b;
    color: #e2e8f0;
}
#NavButton[active="true"] {
    background-color: #0d9488;
    color: #ffffff;
    font-weight: bold;
}
#SidebarDivider {
    background-color: #1e293b;
    max-height: 1px;
    margin: 4px 12px;
}

/* ── Content area ── */
#ContentArea {
    background-color: #f1f5f9;
}
#PageTitle {
    font-size: 20px;
    font-weight: bold;
    color: #0f172a;
}
#PageSubtitle {
    font-size: 12px;
    color: #64748b;
}

/* ── Cards / Panels ── */
#Card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}

/* ── Tables ── */
QTableView, QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    gridline-color: #f1f5f9;
    selection-background-color: #e0f2fe;
    selection-color: #0f172a;
    alternate-background-color: #f8fafc;
}
QTableView::item, QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #f1f5f9;
}
QTableView::item:selected, QTableWidget::item:selected {
    background-color: #e0f2fe;
    color: #0f172a;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    font-weight: bold;
    font-size: 12px;
    padding: 8px 8px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
}
QHeaderView::section:last {
    border-right: none;
}

/* ── Inputs ── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDateEdit, QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px 10px;
    color: #1e293b;
    selection-background-color: #bae6fd;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDateEdit:focus, QComboBox:focus {
    border: 1.5px solid #0d9488;
    outline: none;
}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
    subcontrol-origin: padding;
    subcontrol-position: right center;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #64748b;
}
QComboBox:on {
    border: 1.5px solid #0d9488;
}
QDateEdit::drop-down {
    border: none;
    width: 28px;
    subcontrol-origin: padding;
    subcontrol-position: right center;
}
QDateEdit::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #64748b;
}
QDateEdit::up-button, QDateEdit::down-button,
QSpinBox::up-button, QSpinBox::down-button {
    width: 16px;
}
QComboBox QAbstractItemView, QComboBox QListView {
    background: #ffffff;
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    selection-background-color: #0d9488;
    selection-color: #ffffff;
    outline: none;
}
QComboBox QAbstractItemView::item, QComboBox QListView::item {
    min-height: 28px;
    padding: 4px 8px;
    color: #1e293b;
}
QComboBox QAbstractItemView::item:selected, QComboBox QListView::item:selected {
    background-color: #0d9488;
    color: #ffffff;
}


/* ── Buttons ── */
QPushButton {
    background-color: #e2e8f0;
    color: #475569;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover   { background-color: #cbd5e1; }
QPushButton:pressed { background-color: #94a3b8; }
QPushButton:disabled { background-color: #f1f5f9; color: #94a3b8; }

#BtnPrimary {
    background-color: #0d9488;
    color: #ffffff;
}
#BtnPrimary:hover   { background-color: #0f766e; }
#BtnPrimary:pressed { background-color: #115e59; }

#BtnDanger {
    background-color: #fee2e2;
    color: #dc2626;
}
#BtnDanger:hover   { background-color: #fecaca; }
#BtnDanger:pressed { background-color: #fca5a5; }

#BtnWarning {
    background-color: #fef3c7;
    color: #d97706;
}
#BtnWarning:hover   { background-color: #fde68a; }

#BtnSuccess {
    background-color: #dcfce7;
    color: #16a34a;
}
#BtnSuccess:hover { background-color: #bbf7d0; }

/* ── Search bar ── */
#SearchBar {
    font-size: 13px;
    padding: 8px 12px;
    border-radius: 20px;
    border: 1.5px solid #cbd5e1;
    background-color: #ffffff;
    min-width: 240px;
}
#SearchBar:focus { border-color: #0d9488; }

/* ── Labels ── */
QLabel#FieldLabel {
    color: #475569;
    font-size: 12px;
    font-weight: 600;
}
QLabel#SectionHeader {
    font-size: 14px;
    font-weight: bold;
    color: #0f172a;
    padding: 4px 0;
    border-bottom: 2px solid #e2e8f0;
}

/* ── Status Badge Labels ── */
QLabel#BadgeExpired {
    background-color: #fee2e2;
    color: #dc2626;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}
QLabel#BadgeWarning {
    background-color: #fef3c7;
    color: #d97706;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}
QLabel#BadgeOk {
    background-color: #dcfce7;
    color: #16a34a;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

/* ── Scrollbars ── */
QScrollBar:vertical {
    background: #f1f5f9;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── Tabs ── */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 0 6px 6px 6px;
    background: #ffffff;
}
QTabBar::tab {
    background-color: #f1f5f9;
    color: #64748b;
    padding: 8px 20px;
    margin-right: 2px;
    border-radius: 6px 6px 0 0;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0d9488;
    font-weight: bold;
    border-top: 2px solid #0d9488;
}
QTabBar::tab:hover:!selected { background-color: #e2e8f0; }

/* ── Dialog ── */
QDialog {
    background-color: #f8fafc;
}

/* ── GroupBox ── */
QGroupBox {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    margin-top: 12px;
    padding: 8px;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #0d9488;
    font-weight: bold;
    font-size: 12px;
}

/* ── Status bar ── */
QStatusBar {
    background-color: #0f172a;
    color: #94a3b8;
    font-size: 11px;
    padding: 2px 8px;
}

/* ── Checkboxes ── */
QCheckBox {
    spacing: 8px;
    color: #1e293b;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid #94a3b8;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #0d9488;
    border-color: #0d9488;
}

/* ── Calendar ── */
QCalendarWidget {
    min-width: 300px;
    min-height: 240px;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #f1f5f9;
    border-bottom: 1px solid #cbd5e1;
    min-height: 36px;
}
QCalendarWidget QToolButton {
    color: #1e293b;
    background-color: transparent;
    font-weight: bold;
    font-size: 13px;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 28px;
    min-height: 28px;
}
QCalendarWidget QToolButton:hover {
    background-color: #cbd5e1;
}
QCalendarWidget QMenu {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
}
QCalendarWidget QSpinBox {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    min-height: 24px;
    font-size: 13px;
}
QCalendarWidget QAbstractItemView {
    background-color: #ffffff;
    color: #1e293b;
    selection-background-color: #0d9488;
    selection-color: #ffffff;
    font-size: 13px;
    outline: none;
}
QCalendarWidget QAbstractItemView:enabled {
    color: #1e293b;
}
QCalendarWidget QAbstractItemView:disabled {
    color: #94a3b8;
}
QCalendarWidget QAbstractItemView::item {
    min-width: 34px;
    min-height: 28px;
    padding: 2px;
    text-align: center;
}
QCalendarWidget QAbstractItemView::item:selected {
    background-color: #0d9488;
    color: #ffffff;
    border-radius: 4px;
}
QCalendarWidget QAbstractItemView::item:hover {
    background-color: #e0f2fe;
    border-radius: 4px;
}
/* Day-of-week header row */
QCalendarWidget QWidget { 
    alternate-background-color: #f8fafc;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  NAV BUTTON
# ─────────────────────────────────────────────────────────────────────────────

class NavButton(QPushButton):
    def __init__(self, label: str, page_index: int, parent=None):
        super().__init__(label, parent)
        self.setObjectName("NavButton")
        self.page_index = page_index
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(False)

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NMIMS Clinica - Clinic Management Software")
        self.setMinimumSize(1280, 780)
        self.resize(1400, 860)
        self.setStyleSheet(APP_STYLESHEET)

        self._nav_buttons: list[NavButton] = []
        self._build_ui()
        self._navigate(0)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_content(), stretch=1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready  •  NMIMS Clinica: Clinic Management Software")

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)
        vbox = QVBoxLayout(sidebar)
        vbox.setContentsMargins(10, 20, 10, 20)
        vbox.setSpacing(2)

        # App branding
        title = QLabel("🏥  NMIMS Clinica")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Clinic Management Software")
        subtitle.setObjectName("AppSubtitle")
        subtitle.setWordWrap(True)
        vbox.addWidget(title)
        vbox.addWidget(subtitle)
        vbox.addSpacing(16)

        # Divider
        div = QFrame()
        div.setObjectName("SidebarDivider")
        div.setFrameShape(QFrame.HLine)
        vbox.addWidget(div)
        vbox.addSpacing(8)

        # Nav items
        nav_items = [
            ("🚨  Alerts",        0),
            ("👤  Patients",      1),
            ("🗓  Consultations",  2),
            ("💊  Inventory",     3),
            ("📊  Reports",       4),
        ]
        for label, idx in nav_items:
            btn = NavButton(label, idx)
            btn.clicked.connect(lambda _, i=idx: self._navigate(i))
            self._nav_buttons.append(btn)
            vbox.addWidget(btn)

        vbox.addStretch()

        # Bottom divider + version
        div2 = QFrame()
        div2.setObjectName("SidebarDivider")
        div2.setFrameShape(QFrame.HLine)
        vbox.addWidget(div2)
        vbox.addSpacing(6)

        ver = QLabel("v1.0.0")
        ver.setObjectName("AppSubtitle")
        ver.setAlignment(Qt.AlignCenter)
        vbox.addWidget(ver)

        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        content.setObjectName("ContentArea")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.pages = QStackedWidget()
        self.pages.addWidget(DashboardWidget(self))            # 0 — Dashboard
        self.pages.addWidget(PatientListWidget(self))          # 1 — Patients
        self.pages.addWidget(self._placeholder("Consultations", "🗓"))  # 2
        self.pages.addWidget(MedicineListWidget(self))         # 3 — Inventory
        self.pages.addWidget(ReportsWidget(self))              # 4 — Reports

        layout.addWidget(self.pages)
        return content

    def _placeholder(self, title: str, icon: str = "") -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setAlignment(Qt.AlignCenter)
        lbl = QLabel(f"{icon}\n{title}")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setObjectName("PageTitle")
        lbl.setStyleSheet("font-size:28px; color:#94a3b8;")
        vbox.addWidget(lbl)
        return w

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _navigate(self, index: int):
        # 1. Memory Management: Clean up old page
        old_idx = self.pages.currentIndex()
        if old_idx >= 0:
            old_page = self.pages.widget(old_idx)
            if hasattr(old_page, 'cleanup'):
                old_page.cleanup()

        # 2. Switch page
        self.pages.setCurrentIndex(index)
        
        # 3. Refresh new page
        new_page = self.pages.widget(index)
        if hasattr(new_page, '_refresh'):
            new_page.current_page = 0
            new_page._refresh()
        elif hasattr(new_page, '_refresh_all'):
            new_page._refresh_all()

        for btn in self._nav_buttons:
            btn.set_active(btn.page_index == index)

    # ── Public helpers for child widgets ────────────────────────────────────────

    def show_status(self, message: str, timeout_ms: int = 4000):
        """Child widgets call this to show status bar messages."""
        self.status_bar.showMessage(message, timeout_ms)

    def navigate_to(self, index: int):
        """Child widgets can trigger navigation (e.g. go to consultations)."""
        self._navigate(index)