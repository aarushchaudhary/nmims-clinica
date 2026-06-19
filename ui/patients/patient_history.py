"""
patient_history.py
------------------
Shows a patient's full profile + chronological visit history.
Accessible as:
  - PatientHistoryWidget  (embeddable in a page)
  - PatientHistoryDialog  (modal popup — used from patient_list.py)
"""

from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QGroupBox, QScrollArea,
    QSizePolicy, QTextEdit, QSplitter, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QColor, QFont, QDesktopServices

from database.patient_queries import get_patient_by_id
from database.visit_queries   import (
    get_visits_by_patient, count_visits_by_patient
)

# Visit table columns
VCOL_ID        = 0
VCOL_DATE      = 1
VCOL_TYPE      = 2
VCOL_CATEGORY  = 3
VCOL_DIAGNOSIS = 4
VCOL_TREATMENT = 5
VCOL_REFERRAL  = 6
VCOL_MED_LEAVE = 7
VCOL_AMBULANCE = 8

VISIT_COLS = [
    "ID", "Date", "Type", "Category",
    "Diagnosis", "Treatment", "Referral",
    "Med Leave", "Ambulance"
]

VISIT_TYPE_COLORS = {
    "Walk-in":   "#0d9488",
    "Scheduled": "#7c3aed",
    "Emergency": "#dc2626",
}


def _fmt_visit_date(raw: str) -> str:
    """Format 'YYYY-MM-DD HH:MM:SS' → '29 Apr 2026  14:32'."""
    if not raw:
        return "—"
    from datetime import datetime
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw[:19], fmt)
            return dt.strftime("%d %b %Y  %H:%M")
        except ValueError:
            continue
    # Fallback: just return the date part
    return raw[:10]

class PatientInfoCard(QFrame):
    """Top card showing patient profile summary."""

    def __init__(self, patient: dict, visit_count: int, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._build(patient, visit_count)

    def _build(self, p: dict, visit_count: int):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(32)

        # Avatar / initials circle placeholder
        initials = "".join(
            w[0].upper() for w in (p.get("name") or "?").split()[:2]
        )
        avatar = QLabel(initials)
        avatar.setFixedSize(56, 56)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            "background-color:#0d9488; color:white; "
            "border-radius:28px; font-size:20px; font-weight:bold;"
        )

        # Name / type
        name_lbl = QLabel(p.get("name", "Unknown"))
        name_lbl.setStyleSheet("font-size:18px; font-weight:bold; color:#0f172a;")
        type_badge = QLabel(p.get("type", ""))
        type_badge.setStyleSheet(
            "background:#e0f2fe; color:#0369a1; border-radius:10px; "
            "padding:2px 10px; font-size:11px; font-weight:bold;"
        )
        name_col = QVBoxLayout()
        name_col.setSpacing(4)
        name_col.addWidget(name_lbl)
        name_col.addWidget(type_badge, alignment=Qt.AlignLeft)

        root.addWidget(avatar)
        root.addLayout(name_col)
        root.addStretch()

        # Stats
        stats = [
            ("SAP ID",   p.get("employee_id") or p.get("sap_id", "—")),
            ("School",   p.get("school") or "—"),
            ("Age",      str(p.get("age") or "—")),
            ("Sex",      p.get("sex") or p.get("gender") or "—"),
            ("Blood",    p.get("blood_group") or "—"),
            ("Tel.",     p.get("tel") or p.get("mobile") or "—"),
            ("Visits",   str(visit_count)),
        ]
        for label, value in stats:
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl_v = QLabel(value)
            lbl_v.setStyleSheet("font-size:14px; font-weight:600; color:#1e293b;")
            lbl_l = QLabel(label)
            lbl_l.setStyleSheet("font-size:10px; color:#94a3b8;")
            col.addWidget(lbl_v)
            col.addWidget(lbl_l)
            root.addLayout(col)


class VisitDetailPane(QFrame):
    """Right-side panel showing full details of the selected visit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumWidth(300)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        title = QLabel("Visit Details")
        title.setObjectName("SectionHeader")
        root.addWidget(title)

        self.detail_area = QTextEdit()
        self.detail_area.setReadOnly(True)
        self.detail_area.setStyleSheet(
            "border:none; background:transparent; font-size:13px;"
        )
        root.addWidget(self.detail_area, stretch=1)

    def show_visit(self, visit: dict):
        def yn(val):
            return "✅ Yes" if val else "No"

        lines = [
            f"<b>Date:</b> {visit.get('visit_date', '—')}",
            f"<b>Type:</b> {visit.get('visit_type', '—')}",
            f"<b>Category:</b> {visit.get('category_name') or '—'}",
            "",
            f"<b>Chief Complaint:</b><br>{visit.get('chief_complaint') or '—'}",
            f"<b>Diagnosis:</b><br>{visit.get('diagnosis') or '—'}",
            f"<b>Investigations:</b><br>{visit.get('investigations') or '—'}",
            f"<b>Treatment:</b><br>{visit.get('treatment') or '—'}",
            f"<b>Prescription:</b><br>{visit.get('prescription') or '—'}",
            "",
            f"<b>Referral:</b> {visit.get('referral') or 'None'}",
            f"<b>Rest Days:</b> {visit.get('rest_days') or 0}",
            f"<b>Medical Leave:</b> {yn(visit.get('medical_leave'))}",
            f"<b>Ambulance Used:</b> {yn(visit.get('ambulance_used'))}",
        ]
        if visit.get("follow_up_date"):
            lines.append(f"<b>Follow-up:</b> {visit['follow_up_date']}")
        if visit.get("notes"):
            lines.append(f"<br><b>Notes:</b><br>{visit['notes']}")

        self.detail_area.setHtml("<br>".join(lines))

    def clear(self):
        self.detail_area.setHtml(
            "<span style='color:#94a3b8;'>Select a visit to see details.</span>"
        )


class PatientHistoryWidget(QWidget):
    """
    Embeddable widget. Shows patient card + visit table + detail pane.
    Emits `back_requested` so a parent can navigate away.
    """
    back_requested   = Signal()
    consult_requested = Signal(int)   # emits patient_id

    def __init__(self, patient_id: int, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self._visits: list[dict] = []

        self._patient = get_patient_by_id(patient_id) or {}
        self._visit_count = count_visits_by_patient(patient_id)

        self._build_ui()
        self._load_visits()

    # ── Build ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # Header row
        hdr = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setFixedWidth(90)
        btn_back.clicked.connect(self.back_requested.emit)

        self.btn_new_consult = QPushButton("🩺  New Consultation")
        self.btn_new_consult.setObjectName("BtnPrimary")
        self.btn_new_consult.setFixedHeight(36)
        self.btn_new_consult.clicked.connect(
            lambda: self.consult_requested.emit(self.patient_id)
        )
        hdr.addWidget(btn_back)
        hdr.addStretch()

        self.btn_edit_consult = QPushButton("✏️  Edit Consultation")
        self.btn_edit_consult.setObjectName("BtnWarning")
        self.btn_edit_consult.setFixedHeight(36)
        self.btn_edit_consult.setEnabled(False)
        self.btn_edit_consult.clicked.connect(self._open_edit_consultation)

        self.btn_print_pdf = QPushButton("🖨  Print PDF")
        self.btn_print_pdf.setObjectName("BtnSecondary")
        self.btn_print_pdf.setFixedHeight(36)
        self.btn_print_pdf.setEnabled(False)
        self.btn_print_pdf.clicked.connect(self._on_print_pdf)

        self.btn_new_consult = QPushButton("🩺  New Consultation")
        self.btn_new_consult.setObjectName("BtnPrimary")
        self.btn_new_consult.setFixedHeight(36)
        self.btn_new_consult.clicked.connect(
            lambda: self.consult_requested.emit(self.patient_id)
        )
        hdr.addWidget(self.btn_edit_consult)
        hdr.addSpacing(8)
        hdr.addWidget(self.btn_print_pdf)
        hdr.addSpacing(8)
        hdr.addWidget(self.btn_new_consult)
        root.addLayout(hdr)

        # Patient card
        root.addWidget(
            PatientInfoCard(self._patient, self._visit_count)
        )

        # Splitter: visit table | detail pane
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(8)

        lbl = QLabel("Visit History")
        lbl.setObjectName("SectionHeader")
        lv.addWidget(lbl)
        lv.addWidget(self._build_visit_table())
        splitter.addWidget(left)

        self.detail_pane = VisitDetailPane()
        self.detail_pane.clear()
        splitter.addWidget(self.detail_pane)
        splitter.setSizes([650, 340])

        root.addWidget(splitter, stretch=1)

    def _build_visit_table(self) -> QTableWidget:
        self.table = QTableWidget()
        self.table.setColumnCount(len(VISIT_COLS))
        self.table.setHorizontalHeaderLabels(VISIT_COLS)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setColumnHidden(VCOL_ID, True)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(VCOL_DIAGNOSIS, QHeaderView.Stretch)
        hdr.setSectionResizeMode(VCOL_TREATMENT, QHeaderView.Stretch)
        for col in (VCOL_DATE, VCOL_TYPE, VCOL_CATEGORY,
                    VCOL_REFERRAL, VCOL_MED_LEAVE, VCOL_AMBULANCE):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self.table.itemSelectionChanged.connect(self._on_visit_selected)
        return self.table

    # ── Data ─────────────────────────────────────────────────────────────────────

    def _load_visits(self):
        self._visits = get_visits_by_patient(self.patient_id)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for r, v in enumerate(self._visits):
            self.table.insertRow(r)
            vtype = v.get("visit_type", "Walk-in")

            cells = [
                str(v.get("id", "")),
                _fmt_visit_date(v.get("visit_date") or ""),
                vtype,
                v.get("category_name") or "—",
                v.get("diagnosis") or "—",
                v.get("treatment") or "—",
                v.get("referral") or "—",
                "✅" if v.get("medical_leave") else "—",
                "🚑" if v.get("ambulance_used") else "—",
            ]
            for col, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if col == VCOL_TYPE:
                    color = VISIT_TYPE_COLORS.get(vtype, "#475569")
                    item.setForeground(QColor(color))
                self.table.setItem(r, col, item)

        self.table.setSortingEnabled(True)
        self.detail_pane.clear()

    # ── Slots ─────────────────────────────────────────────────────────────────────

    def _on_visit_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visits):
            self.detail_pane.clear()
            self.btn_edit_consult.setEnabled(False)
            self.btn_print_pdf.setEnabled(False)
            return
        # Match by ID to be safe
        visit_id = int(self.table.item(row, VCOL_ID).text())
        visit = next((v for v in self._visits if v["id"] == visit_id), None)
        if visit:
            self.detail_pane.show_visit(visit)
            self.btn_edit_consult.setEnabled(True)
            self.btn_print_pdf.setEnabled(True)

    def _open_edit_consultation(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return

        row = sel[0].row()
        item = self.table.item(row, VCOL_ID)
        if item is None:
            return

        visit_id = int(item.text())
        visit = next((v for v in self._visits if v["id"] == visit_id), None)
        if not visit:
            return
        try:
            from ui.consultations.consultation_form import ConsultationFormDialog
            dlg = ConsultationFormDialog(
                patient_id=self.patient_id,
                visit_id=visit_id,
                parent=self.window()
            )
            if dlg.exec():
                self._load_visits()  # refresh table + detail pane
        except Exception as exc:
            QMessageBox.critical(self, "Edit Consultation Error", str(exc))

    def _on_print_pdf(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return

        row = sel[0].row()
        item = self.table.item(row, VCOL_ID)
        if item is None:
            return

        visit_id = int(item.text())
        visit = next((v for v in self._visits if v["id"] == visit_id), None)
        if not visit:
            return

        try:
            from utils.consultation_pdf import export_consultation_pdf
        except ModuleNotFoundError:
            QMessageBox.warning(
                self,
                "PDF Unavailable",
                "PDF export is not available because PyMuPDF is not installed."
            )
            return

        patient = self._patient or {}
        visit_date = visit.get("visit_date") or ""
        date_str = visit_date[:10] if visit_date else ""
        date_text = date_str
        if date_str:
            from datetime import datetime
            try:
                date_text = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b %Y")
            except ValueError:
                pass

        default_name = f"Consultation_{patient.get('sap_id','')}_{date_str or 'date'}.pdf"
        default_path = default_name.replace("/", "_")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Consultation PDF",
            default_path,
            "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            saved_path = export_consultation_pdf(
                file_path,
                patient=patient,
                visit=visit,
            )
            QMessageBox.information(self, "PDF Created", f"Consultation PDF saved to:\n{saved_path}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(saved_path))
        except Exception as exc:
            QMessageBox.critical(self, "PDF Error", f"Could not create PDF:\n{exc}")


# ─────────────────────────────────────────────────────────────────────────────
#  DIALOG WRAPPER
# ─────────────────────────────────────────────────────────────────────────────

class PatientHistoryDialog(QDialog):
    """Modal dialog wrapping PatientHistoryWidget."""

    def __init__(self, patient_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Patient History")
        self.setMinimumSize(1060, 640)
        self.resize(1100, 700)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.widget = PatientHistoryWidget(patient_id, parent=self)
        self.widget.back_requested.connect(self.reject)
        self.widget.consult_requested.connect(self._open_consultation)
        root.addWidget(self.widget)

    def _open_consultation(self, patient_id: int):
        from ui.consultations.consultation_form import ConsultationFormDialog
        dlg = ConsultationFormDialog(patient_id=patient_id, parent=self)
        if dlg.exec():
            self.widget._load_visits()   # refresh on save