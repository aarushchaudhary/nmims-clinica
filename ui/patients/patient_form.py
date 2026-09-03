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
from PySide6.QtCore import Qt, QDate, Signal

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
}

DATE_FIELDS = {
    "exam_date": "Date",
    "admission_referral_date": "Admission/Referral Date",
    "letter_date": "Prescription Date",
}

COMBO_FIELDS = {
    "blood_pressure": ["", "80/50 mmHg", "90/50 mmHg", "100/60 mmHg", "110/70 mmHg", "120/80 mmHg", "130/90 mmHg", "140/100 mmHg", "Above 150/100 mmHg"],
    "pulse": ["", "60-65", "70-75", "75-80", "80-85", "85-90", "90-95", "95-100", "Above 100"],
    "resp_rate": ["", "16-20%", "95%", "98%", "99%"],
    "advise": ["", "Yes", "No"],
    "chief_complaint_1": ["", "Cold", "Cough", "Throat pain", "Body ache", "Headache", "Breathing difficulty", "Fever", "Bleeding", "Itching", "Pain (legs, upper arms)", "Loose stools", "Loss of appetite", "Allergy", "Running nose", "Nose block", "Sore throat", "Watery eyes", "Stomach pain", "Nausea/Vomiting", "Dehydration", "Frequent urination", "Urgency (urine)", "Smelling urine", "Pain (lower abdomen)", "Blood in urine", "Fever with chills", "Back pain", "Shoulder pain", "Bloating (gas problem)", "Fainting"],
    "chief_complaint_2": ["", "Cold", "Cough", "Throat pain", "Body ache", "Headache", "Breathing difficulty", "Fever", "Bleeding", "Itching", "Pain (legs, upper arms)", "Loose stools", "Loss of appetite", "Allergy", "Running nose", "Nose block", "Sore throat", "Watery eyes", "Stomach pain", "Nausea/Vomiting", "Dehydration", "Frequent urination", "Urgency (urine)", "Smelling urine", "Pain (lower abdomen)", "Blood in urine", "Fever with chills", "Back pain", "Shoulder pain", "Bloating (gas problem)", "Fainting"],
    "chief_complaint_3": ["", "Cold", "Cough", "Throat pain", "Body ache", "Headache", "Breathing difficulty", "Fever", "Bleeding", "Itching", "Pain (legs, upper arms)", "Loose stools", "Loss of appetite", "Allergy", "Running nose", "Nose block", "Sore throat", "Watery eyes", "Stomach pain", "Nausea/Vomiting", "Dehydration", "Frequent urination", "Urgency (urine)", "Smelling urine", "Pain (lower abdomen)", "Blood in urine", "Fever with chills", "Back pain", "Shoulder pain", "Bloating (gas problem)", "Fainting"],
    "chief_complaint_4": ["", "Cold", "Cough", "Throat pain", "Body ache", "Headache", "Breathing difficulty", "Fever", "Bleeding", "Itching", "Pain (legs, upper arms)", "Loose stools", "Loss of appetite", "Allergy", "Running nose", "Nose block", "Sore throat", "Watery eyes", "Stomach pain", "Nausea/Vomiting", "Dehydration", "Frequent urination", "Urgency (urine)", "Smelling urine", "Pain (lower abdomen)", "Blood in urine", "Fever with chills", "Back pain", "Shoulder pain", "Bloating (gas problem)", "Fainting"],
}


class TypeToggleWidget(QWidget):
    """Segmented toggle control for Student vs Staff."""
    typeChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_val = "Student"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn_student = QPushButton("Student")
        self.btn_staff = QPushButton("Staff")

        for btn in (self.btn_student, self.btn_staff):
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(34)

        self.btn_student.clicked.connect(lambda: self.setValue("Student"))
        self.btn_staff.clicked.connect(lambda: self.setValue("Staff"))

        layout.addWidget(self.btn_student, stretch=1)
        layout.addWidget(self.btn_staff, stretch=1)

        self.setValue("Student", force=True)

    def currentText(self) -> str:
        return self._current_val

    def setCurrentText(self, val: str):
        self.setValue(val)

    def setValue(self, val: str, force: bool = False):
        val_str = "Staff" if (str(val).strip().capitalize() == "Staff") else "Student"
        if not force and self._current_val == val_str:
            return

        self._current_val = val_str
        is_staff = (val_str == "Staff")

        self.btn_staff.blockSignals(True)
        self.btn_student.blockSignals(True)
        self.btn_staff.setChecked(is_staff)
        self.btn_student.setChecked(not is_staff)
        self.btn_staff.blockSignals(False)
        self.btn_student.blockSignals(False)

        self._update_styles()
        self.typeChanged.emit(self._current_val)

    def _update_styles(self):
        if self.btn_student.isChecked():
            self.btn_student.setStyleSheet("""
                QPushButton {
                    background-color: #0d9488;
                    color: #ffffff;
                    font-weight: bold;
                    border: 1px solid #0d9488;
                    border-radius: 6px;
                }
            """)
            self.btn_staff.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #64748b;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #f8fafc;
                    color: #1e293b;
                }
            """)
        else:
            self.btn_staff.setStyleSheet("""
                QPushButton {
                    background-color: #7c3aed;
                    color: #ffffff;
                    font-weight: bold;
                    border: 1px solid #7c3aed;
                    border-radius: 6px;
                }
            """)
            self.btn_student.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #64748b;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #f8fafc;
                    color: #1e293b;
                }
            """)

class YesNoToggleWidget(QWidget):
    """Segmented toggle control for Yes vs No."""
    valueChanged = Signal(str)

    def __init__(self, default_yes: bool = False, parent=None):
        super().__init__(parent)
        self._val = "Yes" if default_yes else "No"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.btn_no = QPushButton("No")
        self.btn_yes = QPushButton("Yes")

        for btn in (self.btn_no, self.btn_yes):
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setFixedWidth(50)

        self.btn_no.clicked.connect(lambda: self.setValue("No"))
        self.btn_yes.clicked.connect(lambda: self.setValue("Yes"))

        layout.addWidget(self.btn_no)
        layout.addWidget(self.btn_yes)

        self.setValue(self._val, force=True)

    def currentText(self) -> str:
        return self._val

    def setCurrentText(self, val: str):
        self.setValue(val)

    def setValue(self, val: str, force: bool = False):
        val_str = "Yes" if (str(val).strip().capitalize() == "Yes") else "No"
        if not force and self._val == val_str:
            return

        self._val = val_str
        is_yes = (val_str == "Yes")

        self.btn_yes.blockSignals(True)
        self.btn_no.blockSignals(True)
        self.btn_yes.setChecked(is_yes)
        self.btn_no.setChecked(not is_yes)
        self.btn_yes.blockSignals(False)
        self.btn_no.blockSignals(False)

        self._update_styles()
        self.valueChanged.emit(self._val)

    def _update_styles(self):
        if self.btn_yes.isChecked():
            self.btn_yes.setStyleSheet("""
                QPushButton {
                    background-color: #0d9488;
                    color: #ffffff;
                    font-weight: bold;
                    border: 1px solid #0d9488;
                    border-radius: 4px;
                }
            """)
            self.btn_no.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #64748b;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                }
                QPushButton:hover { background-color: #f8fafc; color: #1e293b; }
            """)
        else:
            self.btn_no.setStyleSheet("""
                QPushButton {
                    background-color: #64748b;
                    color: #ffffff;
                    font-weight: bold;
                    border: 1px solid #64748b;
                    border-radius: 4px;
                }
            """)
            self.btn_yes.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #64748b;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                }
                QPushButton:hover { background-color: #f8fafc; color: #1e293b; }
            """)


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
        self.fields: dict[str, QLineEdit | QTextEdit | QDateEdit | StyledComboBox | TypeToggleWidget] = {}

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

        self.fields["patient_type"] = TypeToggleWidget()
        self.fields["patient_type"].typeChanged.connect(self._on_type_changed)
        wrap_type = QWidget()
        form_type = QFormLayout(wrap_type)
        form_type.setContentsMargins(0, 0, 0, 0)
        form_type.setLabelAlignment(Qt.AlignLeft)
        form_type.addRow(self._lbl("Patient Type *"), self.fields["patient_type"])
        grid.addWidget(wrap_type, 3, 0)

        self.fields["school"] = StyledComboBox()
        self.lbl_school = self._lbl("School")
        self.wrap_school = QWidget()
        form_school = QFormLayout(self.wrap_school)
        form_school.setContentsMargins(0, 0, 0, 0)
        form_school.setLabelAlignment(Qt.AlignLeft)
        form_school.addRow(self.lbl_school, self.fields["school"])
        grid.addWidget(self.wrap_school, 3, 1)

        self.fields["sex"] = StyledComboBox()
        self.fields["sex"].addItems(["", "M", "F"])
        wrap_sex = QWidget()
        form_sex = QFormLayout(wrap_sex)
        form_sex.setContentsMargins(0, 0, 0, 0)
        form_sex.setLabelAlignment(Qt.AlignLeft)
        form_sex.addRow(self._lbl("Sex (M/F)"), self.fields["sex"])
        grid.addWidget(wrap_sex, 4, 1)

        self.fields["year"] = StyledComboBox()
        self.fields["year"].addItems(["", "1st", "2nd", "3rd", "4th", "5th"])
        self.wrap_year = QWidget()
        form_year = QFormLayout(self.wrap_year)
        form_year.setContentsMargins(0, 0, 0, 0)
        form_year.setLabelAlignment(Qt.AlignLeft)
        form_year.addRow(self._lbl("Year"), self.fields["year"])
        grid.addWidget(self.wrap_year, 4, 0)

        self._add_grid_field(grid, "age", 5, 0)
        self._add_grid_field(grid, "age_months", 5, 1)
        self._add_grid_field(grid, "height", 6, 0)
        self._add_grid_field(grid, "weight", 6, 1)
        self._add_grid_field(grid, "address", 7, 0, colspan=2)
        self._add_grid_field(grid, "tel", 8, 0)
        self._add_grid_field(grid, "brought_by", 8, 1)
        self._add_grid_field(grid, "relation", 9, 0)
        self._add_grid_field(grid, "brought_by_name", 9, 1)

        self._on_type_changed(self.fields["patient_type"].currentText())
        return group

    def _on_type_changed(self, ptype: str):
        is_student = (ptype == "Student")
        current_val = self.fields["school"].currentText().strip()

        self.lbl_school.setText("School" if is_student else "Department")

        self.fields["school"].blockSignals(True)
        self.fields["school"].clear()

        if is_student:
            items = ["", "STME", "SPTM", "SOL", "SOC", "SBM"]
        else:
            items = ["", "SVKMs", "HK worker", "Security", "Canteen", "Project", "Others"]

        self.fields["school"].addItems(items)

        idx = self.fields["school"].findText(current_val)
        self.fields["school"].setCurrentIndex(max(0, idx))
        self.fields["school"].blockSignals(False)

        self.wrap_school.setVisible(True)
        self.wrap_year.setVisible(is_student)
        if not is_student:
            self.fields["year"].setCurrentIndex(0)

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

        # ── Past History Group ──────────────────────────────────────────────
        past = QGroupBox("Any Past/History Of")
        past_vbox = QVBoxLayout(past)
        past_vbox.setSpacing(8)

        self.fields["has_past_history"] = YesNoToggleWidget(default_yes=False)
        self.fields["has_past_history"].valueChanged.connect(self._on_past_history_toggled)

        past_toggle_wrap = QWidget()
        past_toggle_layout = QHBoxLayout(past_toggle_wrap)
        past_toggle_layout.setContentsMargins(0, 0, 0, 0)
        past_toggle_layout.setSpacing(10)
        past_toggle_layout.addWidget(self._lbl("Has Past History?"))
        past_toggle_layout.addWidget(self.fields["has_past_history"])
        past_toggle_layout.addStretch()
        past_vbox.addWidget(past_toggle_wrap)

        self.past_fields_widget = QWidget()
        past_grid = QGridLayout(self.past_fields_widget)
        past_grid.setContentsMargins(0, 0, 0, 0)
        past_grid.setHorizontalSpacing(12)
        past_grid.setVerticalSpacing(8)

        self._add_grid_field(past_grid, "past_high_blood_pressure", 0, 0)
        self._add_grid_field(past_grid, "past_chest_pain", 0, 1)
        self._add_grid_field(past_grid, "past_shortness_of_breath", 1, 0)
        self._add_grid_field(past_grid, "past_asthma", 1, 1)
        self._add_grid_field(past_grid, "past_ulcer_peptic", 2, 0)
        self._add_grid_field(past_grid, "past_diabetes", 2, 1)
        self._add_grid_field(past_grid, "past_major_illness_surgery", 3, 0, colspan=2)

        past_vbox.addWidget(self.past_fields_widget)
        root.addWidget(past)

        # ── Family History Group ────────────────────────────────────────────
        family = QGroupBox("Family History Of")
        family_vbox = QVBoxLayout(family)
        family_vbox.setSpacing(8)

        self.fields["has_family_history"] = YesNoToggleWidget(default_yes=False)
        self.fields["has_family_history"].valueChanged.connect(self._on_family_history_toggled)

        self.fields["family_relation"] = StyledComboBox()
        self.fields["family_relation"].addItems(["Nill", "Father", "Mother", "Grandfather", "Grandmother"])

        fam_top_wrap = QWidget()
        fam_top_layout = QHBoxLayout(fam_top_wrap)
        fam_top_layout.setContentsMargins(0, 0, 0, 0)
        fam_top_layout.setSpacing(10)
        fam_top_layout.addWidget(self._lbl("Has Family History?"))
        fam_top_layout.addWidget(self.fields["has_family_history"])
        fam_top_layout.addSpacing(20)
        fam_top_layout.addWidget(self._lbl("Relation / Member:"))
        fam_top_layout.addWidget(self.fields["family_relation"])
        fam_top_layout.addStretch()
        family_vbox.addWidget(fam_top_wrap)

        self.family_fields_widget = QWidget()
        family_grid = QGridLayout(self.family_fields_widget)
        family_grid.setContentsMargins(0, 0, 0, 0)
        family_grid.setHorizontalSpacing(12)
        family_grid.setVerticalSpacing(8)

        self._add_grid_field(family_grid, "family_high_blood_pressure", 0, 0)
        self._add_grid_field(family_grid, "family_diabetes", 0, 1)
        self._add_grid_field(family_grid, "family_cardiac_disorder", 1, 0)
        self._add_grid_field(family_grid, "family_genetic_disorder", 1, 1)
        self._add_grid_field(family_grid, "other_relevant_history", 2, 0, colspan=2)

        family_vbox.addWidget(self.family_fields_widget)
        root.addWidget(family)

        self._on_past_history_toggled(self.fields["has_past_history"].currentText())
        self._on_family_history_toggled(self.fields["has_family_history"].currentText())
        return group

    def _on_past_history_toggled(self, val: str):
        is_yes = (val == "Yes")
        self.past_fields_widget.setEnabled(is_yes)

    def _on_family_history_toggled(self, val: str):
        is_yes = (val == "Yes")
        self.family_fields_widget.setEnabled(is_yes)
        self.fields["family_relation"].setEnabled(is_yes)

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
        
        if key in COMBO_FIELDS:
            widget = StyledComboBox()
            widget.setEditable(True)
            widget.addItems(COMBO_FIELDS[key])
        elif key in MULTILINE_FIELDS:
            widget = QTextEdit()
            widget.setFixedHeight(MULTILINE_FIELDS[key])
        else:
            widget = QLineEdit()
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
        if "*" in text:
            text = text.replace("*", '<span style="color: #dc2626; font-weight: bold;">*</span>')
            lbl = QLabel(text)
            lbl.setTextFormat(Qt.RichText)
        else:
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
        if hasattr(widget, "currentText"):
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
            if widget.isEditable():
                widget.setCurrentText(text)
            else:
                idx = widget.findText(text)
                widget.setCurrentIndex(max(0, idx))
        elif hasattr(widget, "setCurrentText"):
            widget.setCurrentText(text)
        else:
            widget.setText(text)

    def _populate_fields(self):
        p = self._patient
        today_iso = QDate.currentDate().toString("yyyy-MM-dd")

        for key in self.fields:
            val = p.get(key)
            if key == "patient_type" and val is None:
                val = p.get("type") or "Student"
            elif key in DATE_FIELDS:
                # All prescription & case paper date fields automatically fetch the current date
                val = today_iso
            self._set_field_text(key, val)

        if not p.get("employee_id"):
            self._set_field_text("employee_id", p.get("sap_id"))
        if not p.get("emp_name"):
            self._set_field_text("emp_name", p.get("name"))
        if not p.get("emp_code"):
            self._set_field_text("emp_code", p.get("sap_id"))

        # Populate toggle states for Past History and Family History
        past_keys = [
            "past_high_blood_pressure", "past_chest_pain", "past_shortness_of_breath",
            "past_asthma", "past_ulcer_peptic", "past_diabetes", "past_major_illness_surgery"
        ]
        has_past = (p.get("has_past_history") == "Yes") or any(bool(p.get(k)) for k in past_keys)
        past_val = "Yes" if has_past else "No"
        self._set_field_text("has_past_history", past_val)
        self._on_past_history_toggled(past_val)

        fam_keys = [
            "family_high_blood_pressure", "family_diabetes", "family_cardiac_disorder",
            "family_genetic_disorder", "other_relevant_history"
        ]
        fam_rel = p.get("family_relation") or "Nill"
        has_fam = (p.get("has_family_history") == "Yes") or any(bool(p.get(k)) for k in fam_keys) or (fam_rel != "Nill")
        fam_val = "Yes" if has_fam else "No"
        self._set_field_text("has_family_history", fam_val)
        self._set_field_text("family_relation", fam_rel)
        self._on_family_history_toggled(fam_val)

        self._on_type_changed(self.fields["patient_type"].currentText())

        if self.is_edit:
            self.fields["employee_id"].setEnabled(False)

    def _validate(self) -> bool:
        errors = []
        employee_id = self._field_text("employee_id")
        name = self._field_text("name")
        ptype = self._field_text("patient_type")

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

        if ptype not in ("Student", "Staff"):
            errors.append("Patient Type must be either Student or Staff.")

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
        patient_type = payload.get("patient_type") or "Student"
        sex = payload.get("sex") or None
        gender = {"M": "Male", "F": "Female"}.get(sex)

        age = self._int_or_none(payload.pop("age", None))
        age_months = self._int_or_none(payload.get("age_months"))

        school = payload.get("school")
        if not school or school == "":
            school = None

        has_past = payload.get("has_past_history") == "Yes"
        has_fam = payload.get("has_family_history") == "Yes"

        if not has_past:
            for k in [
                "past_high_blood_pressure", "past_chest_pain", "past_shortness_of_breath",
                "past_asthma", "past_ulcer_peptic", "past_diabetes", "past_major_illness_surgery"
            ]:
                payload[k] = None

        if not has_fam:
            for k in [
                "family_high_blood_pressure", "family_diabetes", "family_cardiac_disorder",
                "family_genetic_disorder", "other_relevant_history"
            ]:
                payload[k] = None
            payload["family_relation"] = "Nill"

        year = payload.get("year") if patient_type == "Student" else None
        if not year or year == "":
            year = None

        payload["employee_id"] = employee_id
        payload["emp_code"] = payload.get("emp_code") or employee_id
        payload["emp_name"] = payload.get("emp_name") or name
        payload["mobile"] = payload.get("tel")
        payload["gender"] = gender
        payload["age"] = age
        payload["age_months"] = age_months
        payload["dob"] = None
        payload["blood_group"] = None
        payload["school"] = school
        payload["year"] = year
        payload["patient_type"] = patient_type
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

