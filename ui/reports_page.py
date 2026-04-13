"""
reports_page.py
---------------
Dedicated screen for triggering threaded Excel exports.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QMessageBox, QFileDialog
)
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

        # Buttons
        h = QHBoxLayout()
        self.btn_pat = QPushButton("Export All Patients")
        self.btn_pat.setObjectName("BtnPrimary")
        self.btn_pat.clicked.connect(self._export_patients)
        
        self.btn_inv = QPushButton("Export Inventory")
        self.btn_inv.setEnabled(False) # Placeholder until backend added
        
        self.btn_vis = QPushButton("Export Visits")
        self.btn_vis.setEnabled(False) # Placeholder until backend added

        h.addWidget(self.btn_pat)
        h.addWidget(self.btn_inv)
        h.addWidget(self.btn_vis)
        h.addStretch()
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
        self.progress_bar.setVisible(blocked)
        self.progress_lbl.setVisible(blocked)
        if blocked:
            self.progress_bar.setValue(0)
            self.progress_lbl.setText("Starting export...")

    def _export_patients(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if not dir_path: return

        self._set_ui_blocked(True)
        try:
            from exports.excel_exporter_threaded import ExportPatientsThread, ExportVisitsThread, ExportInventoryThread, ExportVisitsThread, ExportInventoryThread
            self._thread = ExportPatientsThread(export_dir=dir_path)
            self._thread.progress.connect(self._on_progress)
            self._thread.error.connect(self._on_error)
            self._thread.finished.connect(self._on_finished)
            self._thread.start()
        except Exception as e:
            self._on_error(str(e))

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

    def _export_visits(self):
        dir_path = QFileDialog.getExistingDirectory(self, 'Select Export Directory')
        if dir_path:
            self._start_export(ExportVisitsThread(export_dir=dir_path))

    def _export_inventory(self):
        dir_path = QFileDialog.getExistingDirectory(self, 'Select Export Directory')
        if dir_path:
            self._start_export(ExportInventoryThread(export_dir=dir_path))
