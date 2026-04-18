"""
reports_page.py
---------------
Dedicated screen for triggering threaded Excel exports.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QMessageBox, QFileDialog, QLineEdit
)
import os
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

        # Buttons
        h = QHBoxLayout()
        self.btn_pat = QPushButton("Export Patients")
        self.btn_pat.clicked.connect(self._export_patients)
        
        self.btn_inv = QPushButton("Export Inventory")
        self.btn_inv.clicked.connect(self._export_inventory)
        
        self.btn_vis = QPushButton("Export Visits")
        self.btn_vis.clicked.connect(self._export_visits)

        self.btn_all = QPushButton("⭐ Export All Data")
        self.btn_all.setObjectName("BtnPrimary")
        self.btn_all.clicked.connect(self._export_all)

        h.addWidget(self.btn_pat)
        h.addWidget(self.btn_inv)
        h.addWidget(self.btn_vis)
        h.addStretch()
        h.addWidget(self.btn_all)
        cv.addLayout(h)

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

    def _export_patients(self):
        from exports.excel_exporter_threaded import ExportPatientsThread
        self._start_export_thread(ExportPatientsThread(export_dir=self.dir_input.text()))

    def _export_visits(self):
        from exports.excel_exporter_threaded import ExportVisitsThread
        self._start_export_thread(ExportVisitsThread(export_dir=self.dir_input.text()))

    def _export_inventory(self):
        from exports.excel_exporter_threaded import ExportInventoryThread
        self._start_export_thread(ExportInventoryThread(export_dir=self.dir_input.text()))

    def _export_all(self):
        from exports.excel_exporter_threaded import ExportAllDataThread
        self._start_export_thread(ExportAllDataThread(export_dir=self.dir_input.text()))

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
