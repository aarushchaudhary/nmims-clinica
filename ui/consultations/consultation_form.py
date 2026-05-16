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
    QInputDialog,
    QDateEdit, QFrame, QWidget, QSizePolicy, QScrollArea, QFileDialog,
    QTableWidget, QTableWidgetItem, QAbstractItemView
)
from ui.widgets import StyledComboBox
from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtGui import QFont, QDesktopServices

from database.patient_queries import get_patient_by_id
from database.visit_queries   import (
    create_visit, update_visit, get_visit_by_id,
    get_all_categories, add_custom_category
)
from database.inventory_queries import get_all_medicines, dispense_medicine, get_dispense_log


VISIT_TYPES = ["Walk-in", "Scheduled", "Emergency"]


class ConsultationFormDialog(QDialog):
    """
    patient_id  → required (patient must exist)
    visit_id    → optional; if provided, opens in Edit mode
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
        self._visit      = {}
        self._medicines  = []
        self._selected_medicines = {}

        self._build_ui()
        self._load_categories()
        self._load_medicines()

        if self.is_edit:
            self._visit = get_visit_by_id(visit_id) or {}
            self._populate_for_edit()

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
        self.f_visit_type.setStyleSheet(
            "QComboBox { background-color: #ffffff; color: #000000; }"
        )

        self.f_diagnosed_by = StyledComboBox()
        self.f_diagnosed_by.addItems(["Doctor", "Nurse"])
        self.f_diagnosed_by.setStyleSheet(
            "QComboBox { background-color: #ffffff; color: #000000; }"
        )

        self.f_visit_date = QDateEdit()
        self.f_visit_date.setCalendarPopup(True)
        self.f_visit_date.setDate(QDate.currentDate())
        self.f_visit_date.setDisplayFormat("dd MMM yyyy")
        self.f_visit_date.setStyleSheet(
            "QDateEdit { background-color: #ffffff; color: #000000; }"
        )

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
        self.f_category.setStyleSheet(
            "QComboBox { background-color: #ffffff; color: #000000; }"
        )
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

        med_row = QHBoxLayout()
        self.f_prescription = StyledComboBox()
        self.f_prescription.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.f_prescription.setStyleSheet(
            "QComboBox { background-color: #ffffff; color: #000000; }"
        )
        self.f_prescription.currentIndexChanged.connect(self._on_medicine_changed)

        self.f_prescription_qty = QSpinBox()
        self.f_prescription_qty.setRange(0, 0)
        self.f_prescription_qty.setSuffix(" units")
        self.f_prescription_qty.setEnabled(False)

        btn_add_med = QPushButton("Add Medicine")
        btn_add_med.setFixedWidth(120)
        btn_add_med.clicked.connect(self._on_add_medicine)

        med_row.addWidget(self.f_prescription)
        med_row.addWidget(self.f_prescription_qty)
        med_row.addWidget(btn_add_med)

        self.tbl_medicines = QTableWidget(0, 2)
        self.tbl_medicines.setHorizontalHeaderLabels(["Medicine", "Qty"])
        self.tbl_medicines.horizontalHeader().setStretchLastSection(True)
        self.tbl_medicines.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_medicines.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_medicines.setMinimumHeight(120)

        btn_remove_med = QPushButton("Remove Selected")
        btn_remove_med.setFixedWidth(130)
        btn_remove_med.clicked.connect(self._on_remove_selected_medicine)

        med_list_row = QHBoxLayout()
        med_list_row.addWidget(self.tbl_medicines)
        med_list_row.addWidget(btn_remove_med)

        form.addRow(self._lbl("Chief Complaint"), self.f_complaint)
        form.addRow(self._lbl("Diagnosis"),       self.f_diagnosis)
        form.addRow(self._lbl("Disease Category"), cat_row)
        form.addRow(self._lbl("Investigations"),  self.f_investigations)
        form.addRow(self._lbl("Treatment"),       self.f_treatment)
        form.addRow(self._lbl("Prescription"),    med_row)
        form.addRow(self._lbl("Selected Medicines"), med_list_row)
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
        self.f_followup_date.setStyleSheet(
            "QDateEdit { background-color: #ffffff; color: #000000; }"
        )
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

        btn_print = QPushButton("Print PDF")
        btn_print.setObjectName("BtnWarning")
        btn_print.clicked.connect(self._on_print_pdf)

        self.btn_save = QPushButton("✏️  Update Consultation" if self.is_edit else "💾  Save Consultation")
        self.btn_save.setObjectName("BtnPrimary")
        self.btn_save.setFixedHeight(40)
        self.btn_save.clicked.connect(self._on_save)

        h.addStretch()
        h.addWidget(btn_print)
        h.addSpacing(8)
        h.addWidget(btn_cancel)
        h.addSpacing(8)
        h.addWidget(self.btn_save)
        return w

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl

    # ── Populate for edit ────────────────────────────────────────────────────────

    def _populate_for_edit(self):
        """Pre-fill all form fields from the existing visit record."""
        v = self._visit

        # Visit type
        idx = self.f_visit_type.findText(v.get("visit_type", "Walk-in"))
        if idx >= 0:
            self.f_visit_type.setCurrentIndex(idx)

        # Visit date
        vdate = v.get("visit_date", "")
        if vdate:
            from PySide6.QtCore import QDate
            qd = QDate.fromString(vdate[:10], "yyyy-MM-dd")
            if qd.isValid():
                self.f_visit_date.setDate(qd)

        # Clinical fields
        self.f_complaint.setPlainText(v.get("chief_complaint") or "")
        self.f_diagnosis.setPlainText(v.get("diagnosis") or "")
        self.f_investigations.setPlainText(v.get("investigations") or "")
        self.f_treatment.setPlainText(v.get("treatment") or "")
        self._set_prescription_from_text(v.get("prescription") or "")

        # Category — must run after _load_categories()
        cat_id = v.get("category_id")
        if cat_id is not None:
            cidx = self.f_category.findData(cat_id)
            if cidx >= 0:
                self.f_category.setCurrentIndex(cidx)

        # Outcomes
        self.f_referral.setText(v.get("referral") or "")
        self.f_rest_days.setValue(int(v.get("rest_days") or 0))
        self.chk_med_leave.setChecked(bool(v.get("medical_leave")))
        self.chk_ambulance.setChecked(bool(v.get("ambulance_used")))

        # Follow-up
        fu = v.get("follow_up_date")
        if fu:
            from PySide6.QtCore import QDate
            qfu = QDate.fromString(fu[:10], "yyyy-MM-dd")
            if qfu.isValid():
                self.chk_followup.setChecked(True)
                self.f_followup_date.setDate(qfu)

        # Notes
        self.f_notes.setPlainText(v.get("notes") or "")

    # ── Categories ───────────────────────────────────────────────────────────────

    def _load_categories(self):
        self._categories = get_all_categories()
        self.f_category.clear()
        self.f_category.addItem("— Select Category —", None)
        for cat in self._categories:
            suffix = "  ★" if cat.get("is_custom") else ""
            self.f_category.addItem(cat["name"] + suffix, cat["id"])

    def _load_medicines(self):
        self._medicines = get_all_medicines()
        self.f_prescription.blockSignals(True)
        self.f_prescription.clear()
        self.f_prescription.addItem("— Select Medicine —", None)
        for med in self._medicines:
            self.f_prescription.addItem(self._med_label(med), med.get("id"))
        self.f_prescription.blockSignals(False)
        self._on_medicine_changed()

    def _on_medicine_changed(self):
        med_id = self.f_prescription.currentData()
        if not med_id:
            self.f_prescription_qty.setRange(0, 0)
            self.f_prescription_qty.setValue(0)
            self.f_prescription_qty.setEnabled(False)
            return

        med = next((m for m in self._medicines if m.get("id") == med_id), None)
        stock = int(med.get("current_stock", 0)) if med else 0
        selected = int(self._selected_medicines.get(med_id, 0))
        remaining = max(stock - selected, 0)
        if remaining <= 0:
            self.f_prescription_qty.setRange(0, 0)
            self.f_prescription_qty.setValue(0)
            self.f_prescription_qty.setEnabled(False)
            return

        self.f_prescription_qty.setRange(1, remaining)
        self.f_prescription_qty.setValue(1)
        self.f_prescription_qty.setEnabled(True)

    def _med_label(self, med: dict) -> str:
        name = med.get("name") or "—"
        strength = med.get("strength_mg")
        return f"{name} ({strength} mg)" if strength else name

    def _on_add_medicine(self):
        med_id = self.f_prescription.currentData()
        if not med_id:
            QMessageBox.information(self, "Medicine", "Please select a medicine.")
            return

        qty = self.f_prescription_qty.value()
        if qty <= 0:
            QMessageBox.information(self, "Quantity", "Please enter a quantity.")
            return

        med = next((m for m in self._medicines if m.get("id") == med_id), None)
        stock = int(med.get("current_stock", 0)) if med else 0
        selected = int(self._selected_medicines.get(med_id, 0))
        remaining = max(stock - selected, 0)
        if qty > remaining:
            QMessageBox.warning(
                self, "Insufficient Stock",
                f"Only {remaining} units available for {med.get('name', 'medicine')}."
            )
            return

        self._selected_medicines[med_id] = selected + qty
        self._refresh_medicine_table()
        self.f_prescription.setCurrentIndex(0)
        self._on_medicine_changed()

    def _refresh_medicine_table(self):
        self.tbl_medicines.setRowCount(0)
        for med_id, qty in self._selected_medicines.items():
            med = next((m for m in self._medicines if m.get("id") == med_id), None)
            label = self._med_label(med) if med else "—"
            row = self.tbl_medicines.rowCount()
            self.tbl_medicines.insertRow(row)

            item_med = QTableWidgetItem(label)
            item_med.setData(Qt.UserRole, med_id)
            item_qty = QTableWidgetItem(str(qty))

            self.tbl_medicines.setItem(row, 0, item_med)
            self.tbl_medicines.setItem(row, 1, item_qty)

    def _on_remove_selected_medicine(self):
        row = self.tbl_medicines.currentRow()
        if row < 0:
            return

        item = self.tbl_medicines.item(row, 0)
        med_id = item.data(Qt.UserRole) if item else None
        if med_id in self._selected_medicines:
            del self._selected_medicines[med_id]
        self._refresh_medicine_table()
        self._on_medicine_changed()

    def _set_prescription_from_text(self, text: str):
        self._selected_medicines = {}
        raw = (text or "").strip()
        if not raw:
            self.f_prescription.setCurrentIndex(0)
            self.f_prescription_qty.setValue(0)
            self._refresh_medicine_table()
            return

        parts = []
        for chunk in raw.replace("\r", "").split("\n"):
            parts.extend([p.strip() for p in chunk.split(";") if p.strip()])

        for entry in parts:
            name = entry
            qty = 1
            if " x " in entry:
                name_part, qty_part = entry.split(" x ", 1)
                name = name_part.strip()
                try:
                    qty = int(qty_part.strip())
                except ValueError:
                    qty = 1

            med = next(
                (m for m in self._medicines if (m.get("name") or "").lower() == name.lower()),
                None
            )
            if not med:
                med = next(
                    (m for m in self._medicines if name.lower() in (m.get("name") or "").lower()),
                    None
                )
            if med:
                med_id = med.get("id")
                self._selected_medicines[med_id] = self._selected_medicines.get(med_id, 0) + max(qty, 1)

        self._refresh_medicine_table()
        self.f_prescription.setCurrentIndex(0)
        self._on_medicine_changed()

    def _get_existing_dispense_totals(self) -> dict:
        if not self.visit_id:
            return {}
        rows = get_dispense_log(visit_id=self.visit_id, limit=10000, offset=0)
        totals = {}
        for row in rows:
            med_id = row.get("medicine_id")
            qty = int(row.get("quantity") or 0)
            if med_id is not None and qty > 0:
                totals[med_id] = totals.get(med_id, 0) + qty
        return totals

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

    def _export_pdf_payload(self) -> dict:
        patient = self._patient or {}
        return {
            "patient_name": patient.get("name") or "—",
            "age": patient.get("age") or "—",
            "sex": patient.get("gender") or "—",
            "sap_id": patient.get("sap_id") or "—",
            "phone": patient.get("mobile") or "—",
            "date_text": self.f_visit_date.date().toString("dd MMM yyyy"),
            "complaints": self.f_complaint.toPlainText().strip(),
            "diagnosis": self.f_diagnosis.toPlainText().strip(),
        }

    def _on_print_pdf(self):
        try:
            from utils.consultation_pdf import export_consultation_pdf
        except ModuleNotFoundError:
            QMessageBox.warning(
                self,
                "PDF Unavailable",
                "PDF export is not available because PyMuPDF is not installed."
            )
            return

        payload = self._export_pdf_payload()
        default_name = f"Consultation_{payload['sap_id']}_{self.f_visit_date.date().toString('yyyyMMdd')}.pdf"
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
            saved_path = export_consultation_pdf(file_path, **payload)
            QMessageBox.information(self, "PDF Created", f"Consultation PDF saved to:\n{saved_path}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(saved_path))
        except Exception as exc:
            QMessageBox.critical(self, "PDF Error", f"Could not create PDF:\n{exc}")

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

        selected_items = []
        for med_id, qty in self._selected_medicines.items():
            med = next((m for m in self._medicines if m.get("id") == med_id), None)
            if med and qty > 0:
                selected_items.append((med, qty))

        prescription_text = None
        if selected_items:
            prescription_text = "; ".join(
                f"{med.get('name', 'Medicine')} x {qty}" for med, qty in selected_items
            )

        common_kwargs = dict(
            visit_type       = self.f_visit_type.currentText(),
            chief_complaint  = self.f_complaint.toPlainText().strip() or None,
            diagnosis        = self.f_diagnosis.toPlainText().strip() or None,
            category_id      = category_id,
            investigations   = self.f_investigations.toPlainText().strip() or None,
            treatment        = self.f_treatment.toPlainText().strip() or None,
            prescription     = prescription_text,
            referral         = referral,
            rest_days        = self.f_rest_days.value(),
            medical_leave    = self.chk_med_leave.isChecked(),
            ambulance_used   = self.chk_ambulance.isChecked(),
            follow_up_date   = follow_up,
            notes            = self.f_notes.toPlainText().strip() or None,
        )

        try:
            if self.is_edit:
                update_visit(self.visit_id, **common_kwargs)
                prev_totals = self._get_existing_dispense_totals()
                for med, qty in selected_items:
                    med_id = med.get("id")
                    prev_qty = int(prev_totals.get(med_id, 0))
                    delta = int(qty) - prev_qty
                    if delta <= 0:
                        continue

                    stock = int(med.get("current_stock", 0))
                    if delta > stock:
                        QMessageBox.warning(
                            self, "Insufficient Stock",
                            f"Only {stock} units available for {med.get('name', 'medicine')}"
                        )
                        continue

                    dispense_medicine(
                        medicine_id=med_id,
                        quantity=delta,
                        visit_id=self.visit_id
                    )
            else:
                from datetime import datetime
                chosen_date = self.f_visit_date.date().toString("yyyy-MM-dd")
                now_time = datetime.now().strftime("%H:%M:%S")
                visit_datetime = f"{chosen_date} {now_time}"
                visit_id = create_visit(
                    patient_id = self.patient_id,
                    visit_date = visit_datetime,
                    **common_kwargs
                )
                for med, qty in selected_items:
                    stock = int(med.get("current_stock", 0))
                    if qty > stock:
                        QMessageBox.warning(
                            self, "Insufficient Stock",
                            f"Only {stock} units available for {med.get('name', 'medicine')}."
                        )
                        continue
                    dispense_medicine(
                        medicine_id=med.get("id"),
                        quantity=qty,
                        visit_id=visit_id
                    )
            self.accept()

        except Exception as exc:
            QMessageBox.critical(
                self, "Save Error",
                f"Could not save consultation:\n{exc}"
            )