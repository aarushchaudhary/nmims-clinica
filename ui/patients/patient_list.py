"""
patient_list.py
---------------
Main patient management screen.
Features:
  - Live search (name / SAP ID / tel)
  - Filters: type (Student/Staff), school, gender
  - Sortable table of patients
  - Add / Edit / View History / Delete actions
  - Row count summary
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableView,
    QHeaderView, QAbstractItemView, QMessageBox, QFrame,
    QSizePolicy, QSpacerItem
)
from ui.widgets import StyledComboBox
from PySide6.QtCore import Qt, QTimer, Signal, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QFont

from database.patient_queries import (
    search_patients, delete_patient,
    get_distinct_schools, get_patient_stats
)
from ui.patients.patient_form    import PatientFormDialog
from ui.patients.patient_history import PatientHistoryWidget


# Column indices
COL_ID     = 0
COL_EMP    = 1
COL_NAME   = 2
COL_TYPE   = 3
COL_SCHOOL = 4
COL_AGE    = 5
COL_GENDER = 6
COL_TEL    = 7

COLUMNS = ["ID", "SAP ID", "Name", "Type", "School", "Age", "Sex", "Tel."]


class PatientTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = COLUMNS

    def update_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        if 0 <= index.row() < len(self._data):
            row = self._data[index.row()]
            col = index.column()
            keys = ["id", "employee_id", "name", "type", "school", "age", "sex", "tel"]
            val = row.get(keys[col])
            if keys[col] == "employee_id" and not val:
                val = row.get("sap_id")
            if keys[col] == "tel" and not val:
                val = row.get("mobile")
            
            if role == Qt.DisplayRole:
                return str(val) if val is not None else "—"
            if role == Qt.ForegroundRole and col == COL_TYPE:
                return QColor("#0d9488") if val == "Student" else QColor("#7c3aed")
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None



class PatientListWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_patients: list[dict] = []
        self._selected_patient_id: int | None = None
        self._history_widget: PatientHistoryWidget | None = None
        self.current_page = 0
        self.page_size = 25
        self.table_model = PatientTableModel([])

        self._build_ui()
        self._load_schools()
        self._refresh()

    # ── Build UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        root.addWidget(self._build_header())
        root.addWidget(self._build_stats_bar())
        root.addWidget(self._build_filter_row())
        root.addWidget(self._build_table(), stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_header(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Patients")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Register, search, and manage patient records")
        subtitle.setObjectName("PageSubtitle")

        vb = QVBoxLayout()
        vb.setSpacing(2)
        vb.addWidget(title)
        vb.addWidget(subtitle)

        btn_add = QPushButton("＋  New Patient")
        btn_add.setObjectName("BtnPrimary")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setFixedHeight(38)
        btn_add.clicked.connect(self._on_add)

        h.addLayout(vb)
        h.addStretch()
        h.addWidget(btn_add)
        return w

    def _build_stats_bar(self) -> QWidget:
        self._stats_frame = QFrame()
        self._stats_frame.setObjectName("Card")
        h = QHBoxLayout(self._stats_frame)
        h.setContentsMargins(16, 10, 16, 10)
        h.setSpacing(32)

        self._stat_total     = self._stat_label("Total", "0")
        self._stat_students  = self._stat_label("Students", "0")
        self._stat_staff     = self._stat_label("Staff", "0")
        self._stat_followup  = self._stat_label("Follow Up Cases", "0")
        self._stat_shown     = self._stat_label("Showing", "0")

        for w in (self._stat_total, self._stat_students,
                  self._stat_staff, self._stat_followup, self._stat_shown):
            h.addWidget(w)
        h.addStretch()
        return self._stats_frame

    def _stat_label(self, title: str, value: str) -> QWidget:
        w = QWidget()
        vb = QVBoxLayout(w)
        vb.setSpacing(0)
        vb.setContentsMargins(0, 0, 0, 0)
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet("font-size:20px; font-weight:bold; color:#0d9488;")
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size:11px; color:#64748b;")
        vb.addWidget(lbl_val)
        vb.addWidget(lbl_title)
        # Store reference by sanitized title so we can update later
        attr_key = title.lower().replace(" ", "_")
        setattr(self, f"_stat_val_{attr_key}", lbl_val)
        return w

    def _build_filter_row(self) -> QWidget:
        w = QFrame()
        w.setObjectName("Card")
        h = QHBoxLayout(w)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(10)

        # Search
        self.search_box = QLineEdit()
        self.search_box.setObjectName("SearchBar")
        self.search_box.setPlaceholderText("Search by name, SAP ID or tel.")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.returnPressed.connect(self._on_search_enter)

        # Type filter
        self.filter_type = StyledComboBox()
        self.filter_type.addItems(["All Types", "Student", "Staff"])
        self.filter_type.currentIndexChanged.connect(self._on_filter_changed)

        # School filter
        self.filter_school = StyledComboBox()
        self.filter_school.addItem("All Schools")
        self.filter_school.currentIndexChanged.connect(self._on_filter_changed)

        # Gender filter
        self.filter_gender = StyledComboBox()
        self.filter_gender.addItems(["All Genders", "Male", "Female", "Other"])
        self.filter_gender.currentIndexChanged.connect(self._on_filter_changed)

        # Clear button
        btn_clear = QPushButton("Clear Filters")
        btn_clear.clicked.connect(self._clear_filters)

        h.addWidget(self.search_box, stretch=2)
        h.addWidget(QLabel("Type:"))
        h.addWidget(self.filter_type)
        h.addWidget(QLabel("School:"))
        h.addWidget(self.filter_school)
        h.addWidget(QLabel("Gender:"))
        h.addWidget(self.filter_gender)
        h.addWidget(btn_clear)

        return w

    def _build_table(self) -> QTableView:
        self.table = QTableView()
        self.table.setModel(self.table_model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.StrongFocus)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_SCHOOL, QHeaderView.Stretch)
        for col in (COL_ID, COL_EMP, COL_TYPE, COL_AGE, COL_GENDER, COL_TEL):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self.table.setColumnHidden(COL_ID, True)

        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._on_view_history)
        return self.table

    def _build_action_bar(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        self.btn_edit    = QPushButton("✏  Edit")
        self.btn_history = QPushButton("📋  View History")
        self.btn_history.setObjectName("BtnPrimary")
        self.btn_consult = QPushButton("🩺  New Consultation")
        self.btn_consult.setObjectName("BtnSuccess")
        self.btn_delete  = QPushButton("🗑  Delete")
        self.btn_delete.setObjectName("BtnDanger")

        for btn in (self.btn_edit, self.btn_history,
                    self.btn_consult, self.btn_delete):
            btn.setEnabled(False)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            h.addWidget(btn)

        h.addStretch()

        self.lbl_row_count = QLabel("")
        self.lbl_row_count.setStyleSheet("color:#64748b; font-size:12px;")
        
        self.btn_prev = QPushButton("❮ Prev")
        self.btn_next = QPushButton("Next ❯")
        self.btn_prev.clicked.connect(self._on_prev_page)
        self.btn_next.clicked.connect(self._on_next_page)
        
        h.addWidget(self.lbl_row_count)
        h.addWidget(self.btn_prev)
        h.addWidget(self.btn_next)

        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_history.clicked.connect(self._on_view_history)
        self.btn_consult.clicked.connect(self._on_new_consultation)
        self.btn_delete.clicked.connect(self._on_delete)

        return w

    # ── Data ────────────────────────────────────────────────────────────────────

    def _load_schools(self):
        self.filter_school.blockSignals(True)
        self.filter_school.clear()
        self.filter_school.addItem("All Schools")
        for school in get_distinct_schools():
            self.filter_school.addItem(school)
        self.filter_school.blockSignals(False)

    def _refresh(self):
        query       = self.search_box.text().strip()
        ptype_text  = self.filter_type.currentText()
        school_text = self.filter_school.currentText()
        gender_text = self.filter_gender.currentText()

        ptype  = None if ptype_text  == "All Types"   else ptype_text
        school = None if school_text == "All Schools"  else school_text
        gender = None if gender_text == "All Genders"  else gender_text

        self._all_patients = search_patients(
            query=query,
            patient_type=ptype,
            school=school,
            gender=gender,
            limit=self.page_size,
            offset=self.current_page * self.page_size
        )
        self.table_model.update_data(self._all_patients)
        self.lbl_row_count.setText(f"Page {self.current_page + 1}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(len(self._all_patients) == self.page_size)
        self._update_stats()

    def _update_stats(self):
        from database.patient_queries import get_patient_stats
        stats = get_patient_stats()
        shown = len(self._all_patients)

        getattr(self, "_stat_val_total",           None) and self._stat_val_total.setText(str(stats.get("total", 0)))
        getattr(self, "_stat_val_students",        None) and self._stat_val_students.setText(str(stats.get("students", 0)))
        getattr(self, "_stat_val_staff",           None) and self._stat_val_staff.setText(str(stats.get("staff", 0)))
        getattr(self, "_stat_val_follow_up_cases", None) and self._stat_val_follow_up_cases.setText(str(stats.get("follow_up_cases", 0)))
        getattr(self, "_stat_val_showing",         None) and self._stat_val_showing.setText(str(shown))


    def cleanup(self):
        """Memory Management: Release data when leaving the screen"""
        self._all_patients = []
        self.table_model.update_data([])
        self.lbl_row_count.setText("Data cleared from memory.")

    # ── Slots ───────────────────────────────────────────────────────────────────

    def _on_search_enter(self):
        self.current_page = 0
        self._refresh()
        
    def _on_filter_changed(self):
        self.current_page = 0
        self._refresh()
        
    def _on_prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh()
            
    def _on_next_page(self):
        self.current_page += 1
        self._refresh()

    def _on_selection_changed(self):
        sel = self.table.selectionModel().selectedRows()
        has_sel = bool(sel)
        for btn in (self.btn_edit, self.btn_history,
                    self.btn_consult, self.btn_delete):
            btn.setEnabled(has_sel)
        if has_sel:
            row = sel[0].row()
            self._selected_patient_id = self.table_model._data[row]["id"]

    def _get_selected_id(self) -> int | None:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        return self.table_model._data[sel[0].row()]["id"]

    def _on_add(self):
        dlg = PatientFormDialog(parent=self)
        if dlg.exec():
            self._load_schools()
            self._refresh()
            mw = self.window()
            if hasattr(mw, "show_status"):
                mw.show_status("✅  Patient registered successfully.")

    def _on_edit(self):
        pid = self._get_selected_id()
        if pid is None:
            return
        dlg = PatientFormDialog(patient_id=pid, parent=self)
        if dlg.exec():
            self._refresh()
            mw = self.window()
            if hasattr(mw, "show_status"):
                mw.show_status("✅  Patient updated.")

    def _on_view_history(self):
        pid = self._get_selected_id()
        if pid is None:
            return
        from ui.patients.patient_history import PatientHistoryDialog
        dlg = PatientHistoryDialog(patient_id=pid, parent=self)
        dlg.exec()
        self._refresh()

    def _on_new_consultation(self):
        pid = self._get_selected_id()
        if pid is None:
            return
        from ui.consultations.consultation_form import ConsultationFormDialog
        dlg = ConsultationFormDialog(patient_id=pid, parent=self)
        if dlg.exec():
            self._refresh()
            mw = self.window()
            if hasattr(mw, "show_status"):
                mw.show_status("✅  Consultation recorded.")

    def _on_delete(self):
        pid = self._get_selected_id()
        if pid is None:
            return
        sel = self.table.selectionModel().selectedRows()
        if not sel: return
        row = sel[0].row()
        name = self.table_model._data[row]["name"]

        reply = QMessageBox.warning(
            self,
            "Confirm Delete",
            f"Delete patient '{name}'?\n\nThis will also delete ALL their visit records.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel
        )
        if reply == QMessageBox.Yes:
            delete_patient(pid)
            self._refresh()
            mw = self.window()
            if hasattr(mw, "show_status"):
                mw.show_status(f"🗑  Patient '{name}' deleted.")

    def _clear_filters(self):
        self.search_box.clear()
        self.filter_type.setCurrentIndex(0)
        self.filter_school.setCurrentIndex(0)
        self.filter_gender.setCurrentIndex(0)
        self._refresh()