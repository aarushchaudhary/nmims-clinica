"""
consultation_form.py
--------------------
Dialog for recording a new consultation / visit.
  - Patient info shown at top (read-only)
  - All clinical fields
  - Disease category selector with inline "Add New" button
  - Optional medicine dispense section
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QPushButton,
    QGroupBox, QTextEdit, QDialogButtonBox, QMessageBox,
    QDateEdit, QFrame, QWidget, QSizePolicy, QScrollArea
)
from ui.widgets import StyledComboBox
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from database.patient_queries import get_patient_by_id
from database.visit_queries   import (
    create_visit, get_all_categories, add_custom_category
)


VISIT_TYPES = ["Walk-in", "Scheduled", "Emergency"]


class ConsultationFormDialog(QDialog):
    """
    patient_id  → required (patient must exist)
    visit_id    → optional; if provided, opens in Edit mode (not implemented
                  in this version — extension point for future)
    """

    def __init__(self, patient_id: int, visit_id: int = None, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.visit_id   = visit_id
        self.is_edit    = visit_id is not None

        self.setWindowTitle("New Consultation" if not self.is_edit else "Edit Consultation")
        self.setMinimumWidth(620)
        self.setMinimumHeight(700)
        self.setModal(True)

        self._patient    = get_patient_by_id(patient_id) or {}
        self._categories = []

        self._build_ui()
        self._load_categories()

    # ── Build UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Content Widget for Scroll Area
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        root = QVBoxLayout(scroll_content)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        root.addWidget(self._build_patient_banner())
        root.addWidget(self._build_visit_meta_group())
        root.addWidget(self._build_clinical_group())
        root.addWidget(self._build_outcomes_group())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(scroll_content)
        
        main_layout.addWidget(scroll)

        # Buttons at bottom
        btn_container = self._build_buttons()
        main_layout.addWidget(btn_container)

    def _build_patient_banner(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        frame.setStyleSheet(
            "#Card { background:#e0f2fe; border:1px solid #bae6fd; border-radius:8px; }"
        )
        h = QHBoxLayout(frame)
        h.setContentsMargins(16, 10, 16, 10)

        p = self._patient
        name = QLabel(f"<b>{p.get('name', '—')}</b>")
        name.setStyleSheet("font-size:15px; color:#0369a1;")
        sap  = QLabel(f"SAP: {p.get('sap_id', '—')}")
        sap.setStyleSheet("color:#0369a1; font-size:12px;")
        age  = QLabel(f"Age: {p.get('age') or '—'}")
        age.setStyleSheet("color:#0369a1; font-size:12px;")
        ptype = QLabel(p.get("type", ""))
        ptype.setStyleSheet(
            "background:#0369a1; color:white; border-radius:10px; "
            "padding:2px 10px; font-size:11px;"
        )
        h.addWidget(name)
        h.addWidget(sap)
        h.addWidget(age)
        h.addStretch()
        h.addWidget(ptype)
        return frame

    def _build_visit_meta_group(self) -> QGroupBox:
        grp = QGroupBox("Visit Information")
        form = QFormLayout(grp)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.f_visit_type = StyledComboBox()
        self.f_visit_type.addItems(VISIT_TYPES)

        self.f_diagnosed_by = StyledComboBox()
        self.f_diagnosed_by.addItems(["Doctor", "Nurse"])

        self.f_visit_date = QDateEdit()
        self.f_visit_date.setCalendarPopup(True)
        self.f_visit_date.setDate(QDate.currentDate())
        self.f_visit_date.setDisplayFormat("dd MMM yyyy")

        form.addRow(self._lbl("Visit Type *"), self.f_visit_type)
        form.addRow(self._lbl("Diagnosed By *"), self.f_diagnosed_by)
        form.addRow(self._lbl("Date *"),       self.f_visit_date)
        return grp

    def _build_clinical_group(self) -> QGroupBox:
        grp = QGroupBox("Clinical Details")
        form = QFormLayout(grp)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.f_complaint = QTextEdit()
        self.f_complaint.setPlaceholderText("What does the patient present with?")
        self.f_complaint.setMinimumHeight(60)

        self.f_diagnosis = QTextEdit()
        self.f_diagnosis.setPlaceholderText("Clinical diagnosis")
        self.f_diagnosis.setMinimumHeight(60)

        # Category row: dropdown + Add button
        cat_row = QHBoxLayout()
        self.f_category = StyledComboBox()
        self.f_category.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_add_cat = QPushButton("＋ Add Category")
        btn_add_cat.setFixedWidth(130)
        btn_add_cat.clicked.connect(self._on_add_category)
        cat_row.addWidget(self.f_category)
        cat_row.addWidget(btn_add_cat)

        self.f_investigations = QTextEdit()
        self.f_investigations.setPlaceholderText("Lab tests, X-Ray, ECG, etc.")
        self.f_investigations.setMinimumHeight(60)

        self.f_treatment = QTextEdit()
        self.f_treatment.setPlaceholderText("Treatment given")
        self.f_treatment.setMinimumHeight(60)

        self.f_prescription = QTextEdit()
        self.f_prescription.setPlaceholderText("Medicines prescribed (free text)")
        self.f_prescription.setMinimumHeight(60)

        form.addRow(self._lbl("Chief Complaint"), self.f_complaint)
        form.addRow(self._lbl("Diagnosis"),       self.f_diagnosis)
        form.addRow(self._lbl("Disease Category"), cat_row)
        form.addRow(self._lbl("Investigations"),  self.f_investigations)
        form.addRow(self._lbl("Treatment"),       self.f_treatment)
        form.addRow(self._lbl("Prescription"),    self.f_prescription)
        return grp

    def _build_outcomes_group(self) -> QGroupBox:
        grp = QGroupBox("Outcomes & Actions")
        grid = QGridLayout(grp)
        grid.setSpacing(10)

        # Referral
        grid.addWidget(self._lbl("Referral To"), 0, 0, Qt.AlignRight)
        self.f_referral = QLineEdit()
        self.f_referral.setPlaceholderText("Hospital / Specialist (leave blank if none)")
        grid.addWidget(self.f_referral, 0, 1)

        # Rest days
        grid.addWidget(self._lbl("Rest Days"), 1, 0, Qt.AlignRight)
        self.f_rest_days = QSpinBox()
        self.f_rest_days.setRange(0, 30)
        self.f_rest_days.setSuffix(" days")
        grid.addWidget(self.f_rest_days, 1, 1)

        # Follow-up
        grid.addWidget(self._lbl("Follow-up Date"), 2, 0, Qt.AlignRight)
        fu_row = QHBoxLayout()
        self.chk_followup = QCheckBox("Schedule follow-up")
        self.f_followup_date = QDateEdit()
        self.f_followup_date.setCalendarPopup(True)
        self.f_followup_date.setDate(QDate.currentDate().addDays(7))
        self.f_followup_date.setDisplayFormat("dd MMM yyyy")
        self.f_followup_date.setEnabled(False)
        self.chk_followup.toggled.connect(self.f_followup_date.setEnabled)
        fu_row.addWidget(self.chk_followup)
        fu_row.addWidget(self.f_followup_date)
        fu_row.addStretch()
        grid.addLayout(fu_row, 2, 1)

        # Checkboxes row
        chk_row = QHBoxLayout()
        self.chk_med_leave = QCheckBox("Medical Leave Issued")
        self.chk_ambulance = QCheckBox("Ambulance Used 🚑")
        chk_row.addWidget(self.chk_med_leave)
        chk_row.addSpacing(24)
        chk_row.addWidget(self.chk_ambulance)
        chk_row.addStretch()
        grid.addWidget(self._lbl("Flags"), 3, 0, Qt.AlignRight)
        grid.addLayout(chk_row, 3, 1)

        # Notes
        grid.addWidget(self._lbl("Notes"), 4, 0, Qt.AlignRight | Qt.AlignTop)
        self.f_notes = QTextEdit()
        self.f_notes.setPlaceholderText("Any additional notes…")
        self.f_notes.setMinimumHeight(60)
        grid.addWidget(self.f_notes, 4, 1)

        return grp

    def _build_buttons(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(20, 10, 20, 20)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("💾  Save Consultation")
        self.btn_save.setObjectName("BtnPrimary")
        self.btn_save.setFixedHeight(40)
        self.btn_save.clicked.connect(self._on_save)

        h.addStretch()
        h.addWidget(btn_cancel)
        h.addSpacing(8)
        h.addWidget(self.btn_save)
        return w

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl

    # ── Categories ───────────────────────────────────────────────────────────────

    def _load_categories(self):
        self._categories = get_all_categories()
        self.f_category.clear()
        self.f_category.addItem("— Select Category —", None)
        for cat in self._categories:
            suffix = "  ★" if cat.get("is_custom") else ""
            self.f_category.addItem(cat["name"] + suffix, cat["id"])

    def _on_add_category(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "Add Disease Category",
            "New category name:", QLineEdit.Normal
        )
        if ok and name.strip():
            try:
                new_id = add_custom_category(name.strip())
                self._load_categories()
                # Select the new one
                idx = self.f_category.findData(new_id)
                if idx >= 0:
                    self.f_category.setCurrentIndex(idx)
                QMessageBox.information(
                    self, "Category Added",
                    f"Category '{name.strip()}' added successfully."
                )
            except Exception:
                QMessageBox.warning(
                    self, "Duplicate",
                    f"Category '{name.strip()}' already exists."
                )

    # ── Save ────────────────────────────────────────────────────────────────────

    def _on_save(self):
        # Minimal validation
        if not self.f_diagnosis.toPlainText().strip() and \
           not self.f_complaint.toPlainText().strip():
            QMessageBox.warning(
                self, "Validation",
                "Please enter at least a Chief Complaint or Diagnosis."
            )
            return

        category_id = self.f_category.currentData()  # None if not selected

        follow_up = None
        if self.chk_followup.isChecked():
            follow_up = self.f_followup_date.date().toString("yyyy-MM-dd")

        referral = self.f_referral.text().strip() or None

        try:
            create_visit(
                patient_id       = self.patient_id,
                visit_type       = self.f_visit_type.currentText(),
                visit_date       = self.f_visit_date.date().toString("yyyy-MM-dd HH:mm:ss"),
                chief_complaint  = self.f_complaint.toPlainText().strip() or None,
                diagnosis        = self.f_diagnosis.toPlainText().strip() or None,
                category_id      = category_id,
                investigations   = self.f_investigations.toPlainText().strip() or None,
                treatment        = self.f_treatment.toPlainText().strip() or None,
                prescription     = self.f_prescription.toPlainText().strip() or None,
                referral         = referral,
                rest_days        = self.f_rest_days.value(),
                medical_leave    = self.chk_med_leave.isChecked(),
                ambulance_used   = self.chk_ambulance.isChecked(),
                follow_up_date   = follow_up,
                notes            = self.f_notes.toPlainText().strip() or None,
            )
            self.accept()

        except Exception as exc:
            QMessageBox.critical(
                self, "Save Error",
                f"Could not save consultation:\n{exc}"
            )