"""
reports_page.py
---------------
Dedicated screen for triggering threaded Excel exports.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QMessageBox, QFileDialog, QLineEdit,
    QComboBox
)
import os
import datetime
from PySide6.QtCore import Qt

class ReportsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("📊  Reports & Exports")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        self.card = QFrame()
        self.card.setObjectName("Card")
        cv = QVBoxLayout(self.card)
        cv.setContentsMargins(24, 24, 24, 24)
        cv.setSpacing(16)

        desc = QLabel("Generate comprehensive Excel reports in the background without freezing the application.")
        desc.setObjectName("PageSubtitle")
        cv.addWidget(desc)

        
        # Month/Year Selection
        date_h = QHBoxLayout()
        date_lbl = QLabel("Filter by Month (Optional):")
        date_lbl.setStyleSheet("font-weight: bold; color: #1e293b;")
        
        self.month_combo = QComboBox()
        self.month_combo.addItem("All Time", None)
        for i in range(1, 13):
            self.month_combo.addItem(datetime.date(2000, i, 1).strftime('%B'), i)
            
        self.year_combo = QComboBox()
        self.year_combo.addItem("Any Year", None)
        current_year = datetime.datetime.now().year
        for y in range(current_year, current_year - 10, -1):
            self.year_combo.addItem(str(y), y)
            
        date_h.addWidget(date_lbl)
        date_h.addWidget(self.month_combo)
        date_h.addWidget(self.year_combo)
        date_h.addStretch()
        cv.addLayout(date_h)
        cv.addSpacing(10)
        
        # Directory selection
        dir_h = QHBoxLayout()
        dir_lbl = QLabel("Export Directory:")
        dir_lbl.setStyleSheet("font-weight: bold; color: #1e293b;")
        
        self.dir_input = QLineEdit()
        default_dir = os.path.join(os.path.expanduser("~"), "Documents", "ClinicExports")
        self.dir_input.setText(default_dir)
        self.dir_input.setReadOnly(True)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_dir)
        
        dir_h.addWidget(dir_lbl)
        dir_h.addWidget(self.dir_input)
        dir_h.addWidget(btn_browse)
        cv.addLayout(dir_h)
        
        cv.addSpacing(10)


        h = QHBoxLayout()
        self.btn_pat = QPushButton("Export Patients")
        self.btn_pat.clicked.connect(self._export_patients)
        
        self.btn_inv = QPushButton("Export Inventory")
        self.btn_inv.clicked.connect(self._export_inventory)
        
        self.btn_vis = QPushButton("Export Visits")
        self.btn_vis.clicked.connect(self._export_visits)

        h.addWidget(self.btn_pat)
        h.addWidget(self.btn_inv)
        h.addWidget(self.btn_vis)
        
        h2 = QHBoxLayout()
        self.btn_analytics = QPushButton("📊 Export Analytics")
        self.btn_analytics.clicked.connect(self._export_analytics)
        
        self.btn_all = QPushButton("⭐ Export All Data")
        self.btn_all.setObjectName("BtnPrimary")
        self.btn_all.clicked.connect(self._export_all)
        
        h2.addWidget(self.btn_analytics)
        h2.addStretch()
        h2.addWidget(self.btn_all)
        
        cv.addLayout(h)
        cv.addLayout(h2)


        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        cv.addWidget(self.progress_bar)

        self.progress_lbl = QLabel("")
        self.progress_lbl.hide()
        cv.addWidget(self.progress_lbl)

        root.addWidget(self.card)
        root.addStretch()

    def _set_ui_blocked(self, blocked: bool):
        self.btn_pat.setEnabled(not blocked)
        self.btn_inv.setEnabled(not blocked)
        self.btn_vis.setEnabled(not blocked)
        self.btn_all.setEnabled(not blocked)
        self.btn_analytics.setEnabled(not blocked)
        self.month_combo.setEnabled(not blocked)
        self.year_combo.setEnabled(not blocked)
        self.progress_bar.setVisible(blocked)
        self.progress_lbl.setVisible(blocked)
        if blocked:
            self.progress_bar.setValue(0)
            self.progress_lbl.setText("Starting export...")

    def _browse_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory", self.dir_input.text())
        if dir_path:
            self.dir_input.setText(dir_path)

    def _start_export_thread(self, thread_obj):
        self._set_ui_blocked(True)
        try:
            self._thread = thread_obj
            self._thread.progress.connect(self._on_progress)
            self._thread.error.connect(self._on_error)
            self._thread.finished.connect(self._on_finished)
            self._thread.start()
        except Exception as e:
            self._on_error(str(e))


    def _get_selected_date(self):
        m = self.month_combo.currentData()
        y = self.year_combo.currentData()
        if m and not y:
            y = datetime.datetime.now().year
        return m, y


    def _export_patients(self):
        try:
            from exports.excel_exporter_threaded import ExportPatientsThread
        except ModuleNotFoundError as exc:
            QMessageBox.warning(
                self,
                "Export Unavailable",
                f"Excel export is not available because '{exc.name}' is missing."
            )
            return
        m, y = self._get_selected_date()
        self._start_export_thread(ExportPatientsThread(export_dir=self.dir_input.text(), target_month=m, target_year=y))

    def _export_visits(self):
        try:
            from exports.excel_exporter_threaded import ExportVisitsThread
        except ModuleNotFoundError as exc:
            QMessageBox.warning(
                self,
                "Export Unavailable",
                f"Excel export is not available because '{exc.name}' is missing."
            )
            return
        m, y = self._get_selected_date()
        self._start_export_thread(ExportVisitsThread(export_dir=self.dir_input.text(), target_month=m, target_year=y))

    def _export_inventory(self):
        try:
            from exports.excel_exporter_threaded import ExportInventoryThread
        except ModuleNotFoundError as exc:
            QMessageBox.warning(
                self,
                "Export Unavailable",
                f"Excel export is not available because '{exc.name}' is missing."
            )
            return
        m, y = self._get_selected_date()
        self._start_export_thread(ExportInventoryThread(export_dir=self.dir_input.text(), target_month=m, target_year=y))

    def _export_all(self):
        try:
            from exports.excel_exporter_threaded import ExportAllDataThread
        except ModuleNotFoundError as exc:
            QMessageBox.warning(
                self,
                "Export Unavailable",
                f"Excel export is not available because '{exc.name}' is missing."
            )
            return
        m, y = self._get_selected_date()
        self._start_export_thread(ExportAllDataThread(export_dir=self.dir_input.text(), target_month=m, target_year=y))

    def _export_analytics(self):
        try:
            from exports.excel_exporter_threaded import ExportAnalyticsThread
        except ModuleNotFoundError as exc:
            QMessageBox.warning(self, "Export Unavailable", "Missing module.")
            return
        m, y = self._get_selected_date()
        self._start_export_thread(ExportAnalyticsThread(export_dir=self.dir_input.text(), target_month=m, target_year=y))


    def _on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.progress_lbl.setText(msg)

    def _on_error(self, err: str):
        self._set_ui_blocked(False)
        QMessageBox.critical(self, "Export Failed", f"Failed to export data:\n{err}")
        if self._thread:
            self._thread.deleteLater()
            self._thread = None

    def _on_finished(self, path: str):
        self._set_ui_blocked(False)
        QMessageBox.information(self, "Export Complete", f"Successfully exported to:\n{path}")
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
