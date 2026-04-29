"""
patient_form.py
---------------
Add / Edit patient dialog.
  - All fields with validation
  - SAP ID uniqueness check
  - Works in two modes: create (patient_id=None) and edit (patient_id=<id>)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton,
    QGroupBox, QTextEdit, QDialogButtonBox, QMessageBox,
    QFrame, QWidget, QDateEdit
)
from ui.widgets import StyledComboBox
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from database.patient_queries import (
    create_patient, update_patient,
    get_patient_by_id, sap_id_exists
)
from models.patient import VALID_SCHOOLS


class PatientFormDialog(QDialog):
    """
    Pass patient_id=None  → Add New Patient mode
    Pass patient_id=<int> → Edit Patient mode
    """

    def __init__(self, patient_id: int = None, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.is_edit    = patient_id is not None
        self._patient   = {}

        self.setWindowTitle("Edit Patient" if self.is_edit else "Register New Patient")
        self.setMinimumWidth(520)
        self.setModal(True)

        self._build_ui()

        if self.is_edit:
            self._patient = get_patient_by_id(patient_id) or {}
            self._populate_fields()

    # ── Build UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # Title
        title_lbl = QLabel("Edit Patient Record" if self.is_edit else "Register New Patient")
        title_lbl.setObjectName("SectionHeader")
        root.addWidget(title_lbl)

        # ── Identity group ──
        id_group = QGroupBox("Identity")
        id_form  = QFormLayout(id_group)
        id_form.setLabelAlignment(Qt.AlignRight)
        id_form.setSpacing(10)

        self.f_sap_id = QLineEdit()
        self.f_sap_id.setPlaceholderText("e.g. S123456")
        self.f_sap_id.setMaxLength(20)
        self.f_sap_id.textChanged.connect(self._clear_sap_error)

        self.lbl_sap_error = QLabel("")
        self.lbl_sap_error.setStyleSheet("color:#dc2626; font-size:11px;")

        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("Full name")
        self.f_name.setMaxLength(100)

        self.f_type = StyledComboBox()
        self.f_type.addItems(["Student", "Staff"])

        self.f_school = StyledComboBox()
        self.f_school.addItems(["— Select —"] + sorted(VALID_SCHOOLS))

        id_form.addRow(self._lbl("SAP ID *"),  self.f_sap_id)
        id_form.addRow("",                     self.lbl_sap_error)
        id_form.addRow(self._lbl("Full Name *"), self.f_name)
        id_form.addRow(self._lbl("Type *"),    self.f_type)
        id_form.addRow(self._lbl("School"),    self.f_school)
        root.addWidget(id_group)

        # ── Demographics group ──
        demo_group = QGroupBox("Demographics")
        demo_form  = QFormLayout(demo_group)
        demo_form.setLabelAlignment(Qt.AlignRight)
        demo_form.setSpacing(10)

        self.f_dob = QDateEdit()
        self.f_dob.setCalendarPopup(True)
        self.f_dob.setDate(QDate(2000, 1, 1))
        self.f_dob.setDisplayFormat("dd MMM yyyy")

        self.f_gender = StyledComboBox()
        self.f_gender.addItems(["— Select —", "Male", "Female", "Other"])

        self.f_blood_group = StyledComboBox()
        self.f_blood_group.addItems([
            "— Unknown —", "A+", "A−", "B+", "B−",
            "AB+", "AB−", "O+", "O−"
        ])

        self.f_mobile = QLineEdit()
        self.f_mobile.setPlaceholderText("+91 XXXXXXXXXX")
        self.f_mobile.setMaxLength(15)

        demo_form.addRow(self._lbl("Date of Birth"), self.f_dob)
        demo_form.addRow(self._lbl("Gender"),      self.f_gender)
        demo_form.addRow(self._lbl("Blood Group"), self.f_blood_group)
        demo_form.addRow(self._lbl("Mobile"),      self.f_mobile)
        root.addWidget(demo_group)

        # ── Address ──
        addr_group = QGroupBox("Address (optional)")
        addr_form  = QFormLayout(addr_group)
        self.f_address = QTextEdit()
        self.f_address.setPlaceholderText("Hostel / residential address")
        self.f_address.setFixedHeight(60)
        addr_form.addRow(self.f_address)
        root.addWidget(addr_group)

        # ── Buttons ──
        btn_box = QDialogButtonBox()
        self.btn_save   = btn_box.addButton(
            "Save Patient" if not self.is_edit else "Update Patient",
            QDialogButtonBox.ActionRole
        )
        self.btn_cancel = btn_box.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.btn_save.setObjectName("BtnPrimary")
        self.btn_save.setFixedHeight(38)

        self.btn_save.clicked.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl

    # ── Populate (edit mode) ─────────────────────────────────────────────────

    def _populate_fields(self):
        p = self._patient
        self.f_sap_id.setText(p.get("sap_id", ""))
        self.f_name.setText(p.get("name", ""))

        idx = self.f_type.findText(p.get("type", "Student"))
        self.f_type.setCurrentIndex(max(0, idx))

        school = p.get("school") or ""
        school_idx = self.f_school.findText(school) if school else 0
        self.f_school.setCurrentIndex(max(0, school_idx))
        
        from PySide6.QtCore import QDate
        dob_str = p.get("dob")
        if dob_str:
            parts = dob_str.split('-')
            if len(parts) == 3:
                self.f_dob.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
        
        self.f_mobile.setText(p.get("mobile") or "")
        self.f_address.setPlainText(p.get("address") or "")

        gender = p.get("gender") or ""
        gi = self.f_gender.findText(gender)
        self.f_gender.setCurrentIndex(max(0, gi))

        bg = p.get("blood_group") or ""
        bi = self.f_blood_group.findText(bg)
        self.f_blood_group.setCurrentIndex(max(0, bi))

        if self.is_edit:
            self.f_sap_id.setEnabled(False)  # SAP ID not editable after creation

    # ── Validation ──────────────────────────────────────────────────────────────

    def _clear_sap_error(self):
        self.lbl_sap_error.setText("")
        self.f_sap_id.setStyleSheet("")

    def _validate(self) -> bool:
        errors = []

        sap  = self.f_sap_id.text().strip()
        name = self.f_name.text().strip()

        if not sap:
            errors.append("SAP ID is required.")
            self.f_sap_id.setStyleSheet("border: 1.5px solid #dc2626;")
        elif not self.is_edit and sap_id_exists(sap):
            errors.append(f"SAP ID '{sap}' is already registered.")
            self.lbl_sap_error.setText(f"⚠ SAP ID already exists")
            self.f_sap_id.setStyleSheet("border: 1.5px solid #dc2626;")

        if not name:
            errors.append("Patient name is required.")
            self.f_name.setStyleSheet("border: 1.5px solid #dc2626;")

        if errors:
            QMessageBox.warning(
                self, "Validation Error",
                "\n".join(f"• {e}" for e in errors)
            )
            return False
        return True

    # ── Save ────────────────────────────────────────────────────────────────────

    def _on_save(self):
        if not self._validate():
            return

        sap     = self.f_sap_id.text().strip()
        name    = self.f_name.text().strip()
        ptype   = self.f_type.currentText()
        school_txt = self.f_school.currentText()
        school  = None if school_txt.startswith("—") else school_txt.strip()
        mobile  = self.f_mobile.text().strip() or None
        dob     = self.f_dob.date().toString("yyyy-MM-dd")

        gender_txt = self.f_gender.currentText()
        gender  = None if gender_txt.startswith("—") else gender_txt

        bg_txt  = self.f_blood_group.currentText()
        bg      = None if bg_txt.startswith("—") else bg_txt

        address = self.f_address.toPlainText().strip() or None

        try:
            if self.is_edit:
                update_patient(
                    self.patient_id,
                    name=name, patient_type=ptype,
                    school=school, mobile=mobile, dob=dob,
                    gender=gender, blood_group=bg, address=address
                )
            else:
                create_patient(
                    sap_id=sap, name=name, patient_type=ptype,
                    school=school, mobile=mobile, dob=dob,
                    gender=gender, blood_group=bg, address=address
                )
        except Exception as exc:
            QMessageBox.critical(
                self, "Save Error",
                f"Could not save patient:\n{exc}"
            )
            return

        self.accept()