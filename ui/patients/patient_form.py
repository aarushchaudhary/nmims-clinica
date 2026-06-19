"""
patient_form.py
---------------
Add / Edit patient dialog based on the NMIMS case paper, physical examination,
and prescription letterhead fields.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QTextEdit,
    QDialogButtonBox, QMessageBox, QWidget, QDateEdit, QScrollArea
)
from PySide6.QtCore import Qt, QDate

from ui.widgets import StyledComboBox
from database.patient_queries import (
    create_patient, update_patient, get_patient_by_id, sap_id_exists
)


TEXT_FIELDS = {
    "clinic_reg_no": "Clinic Reg. No.",
    "day_care_reg_no": "Day Care Reg. No.",
    "opd_timing": "OPD Timing",
    "opd_reg_no": "O.P.D. Reg. No.",
    "name": "Name",
    "employee_id": "SAP ID",
    "age": "Age (Yrs.)",
    "age_months": "Age (Mths)",
    "height": "Height",
    "weight": "Weight (Kg/lb)",
    "address": "Address",
    "tel": "Tel.",
    "brought_by": "Brought By",
    "relation": "Relation",
    "brought_by_name": "Name (of person brought by)",
    "chief_complaint_1": "Chief Complaint & History 1",
    "chief_complaint_2": "Chief Complaint & History 2",
    "chief_complaint_3": "Chief Complaint & History 3",
    "chief_complaint_4": "Chief Complaint & History 4",
    "past_high_blood_pressure": "High Blood Pressure",
    "past_chest_pain": "Chest Pain",
    "past_shortness_of_breath": "Shortness of Breath",
    "past_asthma": "Asthma",
    "past_ulcer_peptic": "Ulcer (Peptic)",
    "past_diabetes": "Diabetes",
    "past_major_illness_surgery": "Any Major Illness/Surgery",
    "family_high_blood_pressure": "High Blood Pressure",
    "family_diabetes": "Diabetes",
    "family_cardiac_disorder": "Cardiac Disorder",
    "family_genetic_disorder": "Genetic Disorder (if known)",
    "other_relevant_history": "Other Relevant History",
    "blood_pressure": "Blood Pressure (mm of Hg)",
    "pulse": "Pulse (PM)",
    "resp_rate": "Resp Rate (PM)",
    "general_appearance": "General Appearance",
    "eyes_right": "Eyes - Right",
    "eyes_left": "Eyes - Left",
    "colour_vision_right": "Colour Vision - Right",
    "colour_vision_left": "Colour Vision - Left",
    "ears_inspection": "Ears - Inspection",
    "ears_hearing": "Ears - Hearing",
    "cvs": "CVS",
    "per_abdomen": "Per Abdomen",
    "chest": "Chest",
    "doctor_name": "Name of Doctor",
    "diagnosis": "Diagnosis",
    "advise": "Advise",
    "emp_name": "Emp. Name",
    "emp_code": "Emp. Code",
}

MULTILINE_FIELDS = {
    "address": 72,
    "past_major_illness_surgery": 58,
    "other_relevant_history": 58,
    "general_appearance": 58,
    "diagnosis": 58,
    "advise": 120,
}

DATE_FIELDS = {
    "exam_date": "Date",
    "admission_referral_date": "Admission/Referral Date",
    "letter_date": "Prescription Date",
}


class PatientFormDialog(QDialog):
    """
    Pass patient_id=None  -> Add New Patient mode
    Pass patient_id=<int> -> Edit Patient mode
    """

    def __init__(self, patient_id: int = None, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.is_edit = patient_id is not None
        self._patient = {}
        self.fields: dict[str, QLineEdit | QTextEdit | QDateEdit | StyledComboBox] = {}

        self.setObjectName("PatientFormDialog")
        self.setWindowTitle("Edit Patient" if self.is_edit else "Register New Patient")
        self.setMinimumSize(780, 680)
        self.resize(880, 760)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog#PatientFormDialog QGroupBox {
                margin-top: 0;
                padding-top: 28px;
            }
            QDialog#PatientFormDialog QGroupBox::title {
                subcontrol-origin: padding;
                subcontrol-position: top left;
                left: 12px;
                top: 8px;
                padding: 0;
                background: transparent;
            }
        """)

        self._build_ui()

        if self.is_edit:
            self._patient = get_patient_by_id(patient_id) or {}
            self._populate_fields()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Edit Patient Record" if self.is_edit else "Register New Patient")
        title.setObjectName("SectionHeader")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        content = QVBoxLayout(body)
        content.setContentsMargins(0, 0, 6, 0)
        content.setSpacing(12)

        content.addWidget(self._build_case_paper_group())
        content.addWidget(self._build_history_group())
        content.addWidget(self._build_physical_exam_group())
        content.addWidget(self._build_letterhead_group())
        content.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

        btn_box = QDialogButtonBox()
        self.btn_save = btn_box.addButton(
            "Save Patient" if not self.is_edit else "Update Patient",
            QDialogButtonBox.ActionRole
        )
        self.btn_cancel = btn_box.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.btn_save.setObjectName("BtnPrimary")
        self.btn_save.setFixedHeight(38)
        self.btn_save.clicked.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    def _build_case_paper_group(self) -> QGroupBox:
        group = QGroupBox("Case Paper / OPD Form")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self._add_grid_field(grid, "clinic_reg_no", 0, 0)
        self._add_grid_field(grid, "day_care_reg_no", 0, 1)
        self._add_grid_field(grid, "opd_timing", 1, 0)
        self._add_grid_field(grid, "opd_reg_no", 1, 1)
        self._add_grid_field(grid, "name", 2, 0, required=True)
        self._add_grid_field(grid, "employee_id", 2, 1, required=True)

        self.fields["sex"] = StyledComboBox()
        self.fields["sex"].addItems(["", "M", "F"])
        grid.addWidget(self._lbl("Sex (M/F)"), 3, 0)
        grid.addWidget(self.fields["sex"], 3, 1)

        self._add_grid_field(grid, "age", 4, 0)
        self._add_grid_field(grid, "age_months", 4, 1)
        self._add_grid_field(grid, "height", 5, 0)
        self._add_grid_field(grid, "weight", 5, 1)
        self._add_grid_field(grid, "address", 6, 0, colspan=2)
        self._add_grid_field(grid, "tel", 7, 0)
        self._add_grid_field(grid, "brought_by", 7, 1)
        self._add_grid_field(grid, "relation", 8, 0)
        self._add_grid_field(grid, "brought_by_name", 8, 1)
        return group

    def _build_history_group(self) -> QGroupBox:
        group = QGroupBox("Chief Complaints, Past History, and Family History")
        root = QVBoxLayout(group)
        root.setSpacing(10)

        complaints = QGridLayout()
        complaints.setHorizontalSpacing(12)
        complaints.setVerticalSpacing(8)
        self._add_grid_field(complaints, "chief_complaint_1", 0, 0)
        self._add_grid_field(complaints, "chief_complaint_2", 0, 1)
        self._add_grid_field(complaints, "chief_complaint_3", 1, 0)
        self._add_grid_field(complaints, "chief_complaint_4", 1, 1)
        root.addLayout(complaints)

        past = QGroupBox("Any Past/History Of")
        past_grid = QGridLayout(past)
        self._add_grid_field(past_grid, "past_high_blood_pressure", 0, 0)
        self._add_grid_field(past_grid, "past_chest_pain", 0, 1)
        self._add_grid_field(past_grid, "past_shortness_of_breath", 1, 0)
        self._add_grid_field(past_grid, "past_asthma", 1, 1)
        self._add_grid_field(past_grid, "past_ulcer_peptic", 2, 0)
        self._add_grid_field(past_grid, "past_diabetes", 2, 1)
        self._add_grid_field(past_grid, "past_major_illness_surgery", 3, 0, colspan=2)
        root.addWidget(past)

        family = QGroupBox("Family History Of")
        family_grid = QGridLayout(family)
        self._add_grid_field(family_grid, "family_high_blood_pressure", 0, 0)
        self._add_grid_field(family_grid, "family_diabetes", 0, 1)
        self._add_grid_field(family_grid, "family_cardiac_disorder", 1, 0)
        self._add_grid_field(family_grid, "family_genetic_disorder", 1, 1)
        self._add_grid_field(family_grid, "other_relevant_history", 2, 0, colspan=2)
        root.addWidget(family)
        return group

    def _build_physical_exam_group(self) -> QGroupBox:
        group = QGroupBox("Physical Examination")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self._add_grid_field(grid, "blood_pressure", 0, 0)
        self._add_grid_field(grid, "pulse", 0, 1)
        self._add_grid_field(grid, "resp_rate", 1, 0)
        self._add_grid_field(grid, "general_appearance", 1, 1)
        self._add_grid_field(grid, "eyes_right", 2, 0)
        self._add_grid_field(grid, "eyes_left", 2, 1)
        self._add_grid_field(grid, "colour_vision_right", 3, 0)
        self._add_grid_field(grid, "colour_vision_left", 3, 1)
        self._add_grid_field(grid, "ears_inspection", 4, 0)
        self._add_grid_field(grid, "ears_hearing", 4, 1)
        self._add_grid_field(grid, "cvs", 5, 0)
        self._add_grid_field(grid, "per_abdomen", 5, 1)
        self._add_grid_field(grid, "chest", 6, 0)
        self._add_date_field(grid, "exam_date", 6, 1)
        self._add_grid_field(grid, "doctor_name", 7, 0)
        self._add_grid_field(grid, "diagnosis", 7, 1)
        self._add_date_field(grid, "admission_referral_date", 8, 0)
        self._add_grid_field(grid, "advise", 9, 0, colspan=2)
        return group

    def _build_letterhead_group(self) -> QGroupBox:
        group = QGroupBox("Prescription / Letterhead")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self._add_date_field(grid, "letter_date", 0, 0)
        self._add_grid_field(grid, "emp_name", 0, 1)
        self._add_grid_field(grid, "emp_code", 1, 0)
        return group

    def _add_grid_field(
        self, grid: QGridLayout, key: str, row: int, col: int,
        colspan: int = 1, required: bool = False
    ):
        label = TEXT_FIELDS[key] + (" *" if required else "")
        widget = QTextEdit() if key in MULTILINE_FIELDS else QLineEdit()
        if isinstance(widget, QTextEdit):
            widget.setFixedHeight(MULTILINE_FIELDS[key])
        else:
            widget.setMaxLength(160)
        self.fields[key] = widget

        wrap = QWidget()
        form = QFormLayout(wrap)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignLeft)
        form.addRow(self._lbl(label), widget)
        grid.addWidget(wrap, row, col, 1, colspan)

    def _add_date_field(self, grid: QGridLayout, key: str, row: int, col: int):
        widget = QDateEdit()
        widget.setCalendarPopup(True)
        widget.setDisplayFormat("dd MMM yyyy")
        widget.setDate(QDate.currentDate())
        widget.setSpecialValueText("")
        self.fields[key] = widget

        wrap = QWidget()
        form = QFormLayout(wrap)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow(self._lbl(DATE_FIELDS[key]), widget)
        grid.addWidget(wrap, row, col)

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl

    def _field_text(self, key: str) -> str:
        widget = self.fields[key]
        if isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        if isinstance(widget, QDateEdit):
            return widget.date().toString("yyyy-MM-dd")
        if isinstance(widget, StyledComboBox):
            return widget.currentText().strip()
        return widget.text().strip()

    def _set_field_text(self, key: str, value):
        if key not in self.fields or value is None:
            return
        widget = self.fields[key]
        text = str(value)
        if isinstance(widget, QTextEdit):
            widget.setPlainText(text)
        elif isinstance(widget, QDateEdit):
            date = QDate.fromString(text, "yyyy-MM-dd")
            if date.isValid():
                widget.setDate(date)
        elif isinstance(widget, StyledComboBox):
            idx = widget.findText(text)
            widget.setCurrentIndex(max(0, idx))
        else:
            widget.setText(text)

    def _populate_fields(self):
        p = self._patient
        for key in self.fields:
            self._set_field_text(key, p.get(key))

        if not p.get("employee_id"):
            self._set_field_text("employee_id", p.get("sap_id"))
        if not p.get("emp_name"):
            self._set_field_text("emp_name", p.get("name"))
        if not p.get("emp_code"):
            self._set_field_text("emp_code", p.get("sap_id"))

        if self.is_edit:
            self.fields["employee_id"].setEnabled(False)

    def _validate(self) -> bool:
        errors = []
        employee_id = self._field_text("employee_id")
        name = self._field_text("name")

        self.fields["employee_id"].setStyleSheet("")
        self.fields["name"].setStyleSheet("")

        if not employee_id:
            errors.append("SAP ID is required.")
            self.fields["employee_id"].setStyleSheet("border: 1.5px solid #dc2626;")
        elif not self.is_edit and sap_id_exists(employee_id):
            errors.append(f"SAP ID '{employee_id}' is already registered.")
            self.fields["employee_id"].setStyleSheet("border: 1.5px solid #dc2626;")

        if not name:
            errors.append("Patient name is required.")
            self.fields["name"].setStyleSheet("border: 1.5px solid #dc2626;")

        if errors:
            QMessageBox.warning(
                self, "Validation Error", "\n".join(f"- {e}" for e in errors)
            )
            return False
        return True

    def _payload(self) -> dict:
        payload = {}
        for key, widget in self.fields.items():
            value = self._field_text(key)
            payload[key] = value if isinstance(widget, QDateEdit) else value

        employee_id = payload.get("employee_id") or ""
        name = payload.get("name") or ""
        sex = payload.get("sex") or None
        gender = {"M": "Male", "F": "Female"}.get(sex)

        age = self._int_or_none(payload.pop("age", None))
        age_months = self._int_or_none(payload.get("age_months"))

        payload["employee_id"] = employee_id
        payload["emp_code"] = payload.get("emp_code") or employee_id
        payload["emp_name"] = payload.get("emp_name") or name
        payload["mobile"] = payload.get("tel")
        payload["gender"] = gender
        payload["age"] = age
        payload["age_months"] = age_months
        payload["dob"] = None
        payload["blood_group"] = None
        payload["school"] = None
        payload["patient_type"] = "Staff"
        return payload

    @staticmethod
    def _int_or_none(value):
        try:
            return int(str(value).strip()) if value not in (None, "") else None
        except ValueError:
            return None

    def _on_save(self):
        if not self._validate():
            return

        data = self._payload()
        employee_id = data.pop("employee_id")
        name = data.pop("name")
        patient_type = data.pop("patient_type")

        try:
            if self.is_edit:
                update_patient(
                    self.patient_id,
                    name=name,
                    patient_type=patient_type,
                    **data,
                )
            else:
                create_patient(
                    sap_id=employee_id,
                    name=name,
                    patient_type=patient_type,
                    **data,
                )
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Could not save patient:\n{exc}")
            return

        self.accept()
