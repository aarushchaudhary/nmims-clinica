"""
inventory_form.py
-----------------
Three dialogs:
  1. MedicineFormDialog  — Add / Edit medicine
  2. EquipmentFormDialog — Add / Edit equipment
  3. DispenseDialog      — Dispense medicine with optional visit linkage
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton,
    QGroupBox, QTextEdit, QDialogButtonBox, QMessageBox,
    QDateEdit, QCheckBox, QFrame, QWidget, QSizePolicy
)
from ui.widgets import StyledComboBox
from PySide6.QtCore import Qt, QDate

from database.inventory_queries import (
    add_medicine, update_medicine,
    get_medicine_by_id, get_medicine_subtypes,
    add_equipment, update_equipment,
    get_all_equipment, dispense_medicine
)
from database.patient_queries import get_patient_by_id


def _lbl(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("FieldLabel")
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
#  MEDICINE FORM
# ─────────────────────────────────────────────────────────────────────────────

class MedicineFormDialog(QDialog):
    """
    medicine_id=None  → Add New
    medicine_id=<int> → Edit
    """

    def __init__(self, medicine_id: int = None, parent=None):
        super().__init__(parent)
        self.medicine_id = medicine_id
        self.is_edit     = medicine_id is not None
        self._subtypes: list[dict] = []

        self.setWindowTitle("Edit Medicine" if self.is_edit else "Add Medicine")
        self.setMinimumWidth(500)
        self.setModal(True)

        self._build_ui()
        self._load_subtypes()

        if self.is_edit:
            self._populate()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("Edit Medicine" if self.is_edit else "Add New Medicine")
        title.setObjectName("SectionHeader")
        root.addWidget(title)

        # ── Basic info ──
        basic = QGroupBox("Medicine Information")
        form = QFormLayout(basic)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("Medicine name")
        self.f_name.setMaxLength(100)

        self.f_subtype = StyledComboBox()

        self.f_batch = QLineEdit()
        self.f_batch.setPlaceholderText("Batch / lot number")
        self.f_batch.setMaxLength(40)

        from PySide6.QtWidgets import QSpinBox

        self.f_strength = QSpinBox()
        self.f_strength.setRange(0, 1000000)
        self.f_strength.setSuffix(" mg")
        self.f_strength.setToolTip("Strength in milligrams (enter 0 if not applicable)")

        self.f_supplier = QLineEdit()
        self.f_supplier.setPlaceholderText("Supplier / manufacturer")
        self.f_supplier.setMaxLength(80)

        form.addRow(_lbl("Name *"),    self.f_name)
        form.addRow(_lbl("Subtype"),   self.f_subtype)
        form.addRow(_lbl("Strength (mg)"),    self.f_strength)
        form.addRow(_lbl("Batch No."), self.f_batch)
        form.addRow(_lbl("Supplier"),  self.f_supplier)
        root.addWidget(basic)

        # ── Stock ──
        stock = QGroupBox("Stock Details")
        sform = QFormLayout(stock)
        sform.setLabelAlignment(Qt.AlignRight)
        sform.setSpacing(10)

        self.f_stock_received = QSpinBox()
        self.f_stock_received.setRange(0, 999999)
        self.f_stock_received.setSuffix(" units")

        self.f_min_alert = QSpinBox()
        self.f_min_alert.setRange(0, 9999)
        self.f_min_alert.setValue(10)
        self.f_min_alert.setSuffix(" units")
        self.f_min_alert.setToolTip("Alert when stock falls to or below this level")

        sform.addRow(_lbl("Quantity Received *"), self.f_stock_received)
        sform.addRow(_lbl("Low Stock Alert At"),  self.f_min_alert)

        if self.is_edit:
            self.f_current_stock = QSpinBox()
            self.f_current_stock.setRange(0, 999999)
            self.f_current_stock.setSuffix(" units")
            sform.addRow(_lbl("Current Stock"), self.f_current_stock)

        root.addWidget(stock)

        # ── Dates ──
        dates = QGroupBox("Dates")
        dform = QFormLayout(dates)
        dform.setLabelAlignment(Qt.AlignRight)
        dform.setSpacing(10)

        self.f_mfg_date = QDateEdit()
        self.f_mfg_date.setCalendarPopup(True)
        self.f_mfg_date.setDisplayFormat("dd MMM yyyy")
        self.f_mfg_date.setDate(QDate.currentDate().addYears(-1))

        self.f_expiry_date = QDateEdit()
        self.f_expiry_date.setCalendarPopup(True)
        self.f_expiry_date.setDisplayFormat("dd MMM yyyy")
        self.f_expiry_date.setDate(QDate.currentDate().addYears(2))

        dform.addRow(_lbl("Mfg Date"),    self.f_mfg_date)
        dform.addRow(_lbl("Expiry Date *"), self.f_expiry_date)
        root.addWidget(dates)

        # ── Notes ──
        self.f_notes = QTextEdit()
        self.f_notes.setPlaceholderText("Additional notes…")
        self.f_notes.setFixedHeight(52)
        root.addWidget(self.f_notes)

        # ── Buttons ──
        h = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton(
            "Update Medicine" if self.is_edit else "Add Medicine"
        )
        self.btn_save.setObjectName("BtnPrimary")
        self.btn_save.setFixedHeight(38)
        self.btn_save.clicked.connect(self._on_save)
        h.addStretch()
        h.addWidget(btn_cancel)
        h.addSpacing(8)
        h.addWidget(self.btn_save)
        root.addLayout(h)

    def _load_subtypes(self):
        self._subtypes = get_medicine_subtypes()
        self.f_subtype.clear()
        self.f_subtype.addItem("— Select Subtype —", None)
        for s in self._subtypes:
            self.f_subtype.addItem(s["name"], s["id"])

    def _populate(self):
        m = get_medicine_by_id(self.medicine_id) or {}
        self.f_name.setText(m.get("name", ""))

        sid = m.get("subtype_id")
        if sid:
            idx = self.f_subtype.findData(sid)
            self.f_subtype.setCurrentIndex(max(0, idx))

        self.f_batch.setText(m.get("batch_number") or "")
        # strength_mg stored as integer in DB; show 0 as empty
        val = m.get("strength_mg")
        if val is None:
            self.f_strength.setValue(0)
        else:
            try:
                self.f_strength.setValue(int(val))
            except Exception:
                self.f_strength.setValue(0)
        self.f_supplier.setText(m.get("supplier") or "")
        self.f_stock_received.setValue(m.get("stock_received", 0))
        self.f_min_alert.setValue(m.get("minimum_stock_alert", 10))

        if hasattr(self, "f_current_stock"):
            self.f_current_stock.setValue(m.get("current_stock", 0))

        if m.get("mfg_date"):
            self.f_mfg_date.setDate(
                QDate.fromString(m["mfg_date"][:10], "yyyy-MM-dd")
            )
        if m.get("expiry_date"):
            self.f_expiry_date.setDate(
                QDate.fromString(m["expiry_date"][:10], "yyyy-MM-dd")
            )
        self.f_notes.setPlainText(m.get("notes") or "")

    def _on_save(self):
        name = self.f_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Medicine name is required.")
            self.f_name.setStyleSheet("border:1.5px solid #dc2626;")
            return

        expiry = self.f_expiry_date.date().toString("yyyy-MM-dd")
        mfg    = self.f_mfg_date.date().toString("yyyy-MM-dd")
        sid    = self.f_subtype.currentData()

        try:
            if self.is_edit:
                kwargs = dict(
                    name=name, subtype_id=sid,
                    batch_number=self.f_batch.text().strip() or None,
                    dosage=None,
                    strength_mg=(self.f_strength.value() or None),
                    stock_received=self.f_stock_received.value(),
                    current_stock=self.f_current_stock.value(),
                    minimum_stock_alert=self.f_min_alert.value(),
                    mfg_date=mfg, expiry_date=expiry,
                    supplier=self.f_supplier.text().strip() or None,
                    notes=self.f_notes.toPlainText().strip() or None,
                )
                update_medicine(self.medicine_id, **kwargs)
            else:
                add_medicine(
                    name=name, expiry_date=expiry,
                    subtype_id=sid,
                    batch_number=self.f_batch.text().strip() or None,
                    dosage=None,
                    strength_mg=(self.f_strength.value() or None),
                    stock_received=self.f_stock_received.value(),
                    mfg_date=mfg,
                    minimum_stock_alert=self.f_min_alert.value(),
                    supplier=self.f_supplier.text().strip() or None,
                    notes=self.f_notes.toPlainText().strip() or None,
                )
            self.accept()

        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))


# ─────────────────────────────────────────────────────────────────────────────
#  EQUIPMENT FORM
# ─────────────────────────────────────────────────────────────────────────────

class EquipmentFormDialog(QDialog):
    """Add / Edit equipment or instrument."""

    def __init__(self, equipment_id: int = None, parent=None, default_category: str = None):
        super().__init__(parent)
        self.equipment_id = equipment_id
        self.is_edit      = equipment_id is not None
        self.default_category = default_category

        self.setWindowTitle("Edit Equipment" if self.is_edit else "Add Equipment / Instrument")
        self.setMinimumWidth(460)
        self.setModal(True)

        self._build_ui()

        if self.is_edit:
            self._populate()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("Edit Equipment" if self.is_edit else "Add New Equipment")
        title.setObjectName("SectionHeader")
        root.addWidget(title)

        grp = QGroupBox("Equipment Details")
        form = QFormLayout(grp)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("Equipment / instrument name")
        self.f_name.setMaxLength(100)

        self.f_category = StyledComboBox()
        self.f_category.addItems(["Instrument", "Equipment", "Miscellaneous"])

        self.f_qty = QSpinBox()
        self.f_qty.setRange(0, 99999)
        self.f_qty.setSuffix(" units")

        self.chk_disposal = QCheckBox("Disposal Required")

        self.f_purchase_date = QDateEdit()
        self.f_purchase_date.setCalendarPopup(True)
        self.f_purchase_date.setDisplayFormat("dd MMM yyyy")
        self.f_purchase_date.setDate(QDate.currentDate())

        self.f_service_date = QDateEdit()
        self.f_service_date.setCalendarPopup(True)
        self.f_service_date.setDisplayFormat("dd MMM yyyy")
        self.f_service_date.setDate(QDate.currentDate())

        self.f_notes = QTextEdit()
        self.f_notes.setPlaceholderText("Notes or additional info")
        self.f_notes.setFixedHeight(52)

        form.addRow(_lbl("Name *"),           self.f_name)
        form.addRow(_lbl("Category"),         self.f_category)
        form.addRow(_lbl("Quantity"),         self.f_qty)
        form.addRow(_lbl("Disposal"),         self.chk_disposal)
        form.addRow(_lbl("Purchase Date"),    self.f_purchase_date)
        form.addRow(_lbl("Last Serviced"),    self.f_service_date)
        form.addRow(_lbl("Notes"),            self.f_notes)
        root.addWidget(grp)

        h = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton(
            "Update" if self.is_edit else "Add Equipment"
        )
        self.btn_save.setObjectName("BtnPrimary")
        self.btn_save.setFixedHeight(38)
        self.btn_save.clicked.connect(self._on_save)
        h.addStretch()
        h.addWidget(btn_cancel)
        h.addSpacing(8)
        h.addWidget(self.btn_save)
        root.addLayout(h)

        if not self.is_edit and self.default_category:
            idx = self.f_category.findText(self.default_category)
            if idx >= 0:
                self.f_category.setCurrentIndex(idx)

    def _populate(self):
        from database.inventory_queries import search_equipment
        items = search_equipment()
        item  = next((e for e in items if e["id"] == self.equipment_id), None)
        if not item:
            return
        self.f_name.setText(item.get("name", ""))
        idx = self.f_category.findText(item.get("category", "Instrument"))
        self.f_category.setCurrentIndex(max(0, idx))
        self.f_qty.setValue(item.get("quantity", 0))
        self.chk_disposal.setChecked(bool(item.get("disposal_required")))
        self.f_notes.setPlainText(item.get("notes") or "")

        if item.get("purchase_date"):
            self.f_purchase_date.setDate(
                QDate.fromString(item["purchase_date"][:10], "yyyy-MM-dd")
            )
        if item.get("last_serviced_date"):
            self.f_service_date.setDate(
                QDate.fromString(item["last_serviced_date"][:10], "yyyy-MM-dd")
            )

    def _on_save(self):
        name = self.f_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        try:
            kwargs = dict(
                name=name,
                category=self.f_category.currentText(),
                quantity=self.f_qty.value(),
                disposal_required=self.chk_disposal.isChecked(),
                purchase_date=self.f_purchase_date.date().toString("yyyy-MM-dd"),
                last_serviced_date=self.f_service_date.date().toString("yyyy-MM-dd"),
                notes=self.f_notes.toPlainText().strip() or None,
            )
            if self.is_edit:
                update_equipment(self.equipment_id, **kwargs)
            else:
                add_equipment(**kwargs)
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))


# ─────────────────────────────────────────────────────────────────────────────
#  DISPENSE DIALOG
# ─────────────────────────────────────────────────────────────────────────────

class DispenseDialog(QDialog):
    """Dispense a medicine. Optionally link to a visit.

    New: accept optional `visit_id` so dispenses can be linked to a visit record.
    """

    def __init__(self, medicine_id: int, parent=None, visit_id: int = None):
        super().__init__(parent)
        self.medicine_id = medicine_id
        self.visit_id    = visit_id
        self._medicine   = get_medicine_by_id(medicine_id) or {}

        self.setWindowTitle("Dispense Medicine")
        self.setMinimumWidth(420)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Medicine info banner
        m = self._medicine
        banner = QFrame()
        banner.setObjectName("Card")
        banner.setStyleSheet(
            "#Card { background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; }"
        )
        bh = QHBoxLayout(banner)
        bh.setContentsMargins(14, 10, 14, 10)

        name_lbl = QLabel(f"<b>{m.get('name', '—')}</b>")
        name_lbl.setStyleSheet("font-size:15px; color:#166534;")
        stock_lbl = QLabel(
            f"Current Stock: <b>{m.get('current_stock', 0)}</b> units"
        )
        stock_lbl.setStyleSheet("color:#166534;")
        expiry_lbl = QLabel(f"Expires: {(m.get('expiry_date') or '—')[:10]}")
        expiry_lbl.setStyleSheet("color:#64748b; font-size:12px;")

        bh.addWidget(name_lbl)
        bh.addStretch()
        bh.addWidget(stock_lbl)
        bh.addSpacing(16)
        bh.addWidget(expiry_lbl)
        root.addWidget(banner)

        # Expiry warning
        from datetime import date
        exp_str = m.get("expiry_date", "")
        is_expired = False
        if exp_str:
            try:
                is_expired = date.fromisoformat(exp_str[:10]) < date.today()
            except ValueError:
                pass

        if is_expired:
            warn = QLabel(
                "⚠ WARNING: This medicine has EXPIRED. "
                "Dispensing will be flagged as post-expiry."
            )
            warn.setWordWrap(True)
            warn.setStyleSheet(
                "color:#dc2626; background:#fee2e2; border-radius:6px; "
                "padding:8px; font-weight:bold;"
            )
            root.addWidget(warn)

        # Form
        grp = QGroupBox("Dispense Details")
        form = QFormLayout(grp)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.f_qty = QSpinBox()
        max_qty = max(1, m.get("current_stock", 0)) if not is_expired else 9999
        self.f_qty.setRange(1, max_qty)
        self.f_qty.setValue(1)
        self.f_qty.setSuffix(" units")

        self.f_dispensed_by = QLineEdit()
        self.f_dispensed_by.setPlaceholderText("Doctor / nurse name")

        self.f_notes = QLineEdit()
        self.f_notes.setPlaceholderText("Optional notes")

        form.addRow(_lbl("Quantity *"),     self.f_qty)
        form.addRow(_lbl("Dispensed By"),   self.f_dispensed_by)
        form.addRow(_lbl("Notes"),          self.f_notes)
        root.addWidget(grp)

        # Buttons
        h = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        self.btn_dispense = QPushButton("💊  Confirm Dispense")
        self.btn_dispense.setObjectName("BtnPrimary")
        if is_expired:
            self.btn_dispense.setObjectName("BtnDanger")
        self.btn_dispense.setFixedHeight(38)
        self.btn_dispense.clicked.connect(lambda: self._on_confirm(is_expired))
        h.addStretch()
        h.addWidget(btn_cancel)
        h.addSpacing(8)
        h.addWidget(self.btn_dispense)
        root.addLayout(h)

    def _on_confirm(self, is_expired: bool):
        qty = self.f_qty.value()
        cur = self._medicine.get("current_stock", 0)

        if not is_expired and qty > cur:
            QMessageBox.warning(
                self, "Insufficient Stock",
                f"Only {cur} units available."
            )
            return

        if is_expired:
            reply = QMessageBox.warning(
                self, "Expired Medicine",
                "You are dispensing an EXPIRED medicine.\n"
                "This will be recorded in the post-expiry log.\n\nContinue?",
                QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel
            )
            if reply != QMessageBox.Yes:
                return

        try:
            dispense_medicine(
                medicine_id    = self.medicine_id,
                quantity       = qty,
                visit_id       = self.visit_id,
                dispensed_by   = self.f_dispensed_by.text().strip() or None,
                notes          = self.f_notes.text().strip() or None,
                is_post_expiry = is_expired,
            )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))