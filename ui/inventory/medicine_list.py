"""
medicine_list.py
----------------
Inventory management screen updated to Model/View architecture with Pagination.
Memory mapped for low resource usage.
"""

from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableView, QHeaderView, QAbstractItemView,
    QMessageBox, QFrame, QTabWidget, QSizePolicy
)
from ui.widgets import StyledComboBox
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QFont, QBrush

from database.inventory_queries import (
    get_all_medicines, search_medicines,
    get_expiring_soon, get_expired_medicines, get_low_stock_medicines,
    delete_medicine, get_all_equipment, search_equipment,
    delete_equipment, get_inventory_stats, get_medicine_subtypes
)
from ui.inventory.inventory_form import MedicineFormDialog, EquipmentFormDialog

# ── Column definitions ────────────────────────────────────────────────────────

MED_COLS    = ["ID", "Name", "Subtype", "Dosage", "Batch", "Received",
               "Current Stock", "Min Alert", "Mfg Date", "Expiry Date", "Post-Expiry Dispensed"]
EQUIP_COLS  = ["ID", "Name", "Category", "Qty", "Disposal Required",
               "Purchase Date", "Last Serviced"]

MCOL_ID            = 0
MCOL_NAME          = 1
MCOL_SUBTYPE       = 2
MCOL_BATCH         = 4
MCOL_RECEIVED      = 5
MCOL_CURRENT       = 6
MCOL_MIN_ALERT     = 7
MCOL_MFG_DATE      = 8
MCOL_EXPIRY        = 9
MCOL_POST_EXPIRY   = 10
MCOL_DOSAGE        = 3

ECOL_ID       = 0
ECOL_NAME     = 1
ECOL_CATEGORY = 2
ECOL_QTY      = 3
ECOL_DISPOSAL = 4
ECOL_PURCHASE = 5
ECOL_SERVICED = 6

def _expiry_color(expiry_str: str) -> QColor | None:
    if not expiry_str: return None
    try:
        exp = date.fromisoformat(expiry_str[:10])
        days = (exp - date.today()).days
        if days < 0: return QColor("#fee2e2")
        elif days <= 60: return QColor("#fef3c7")
    except ValueError: pass
    return None

class MedicineTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = MED_COLS

    def update_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None
        row = self._data[index.row()]
        col = index.column()
        
        val = ""
        if col == MCOL_ID: val = row.get("id", "")
        elif col == MCOL_NAME: val = row.get("name", "")
        elif col == MCOL_SUBTYPE: val = row.get("subtype_name") or "—"
        elif col == MCOL_DOSAGE:
            sm = row.get("strength_mg")
            val = (f"{sm} mg" if sm is not None and sm != 0 else "—")
        elif col == MCOL_BATCH: val = row.get("batch_number") or "—"
        elif col == MCOL_RECEIVED: val = row.get("stock_received", 0)
        elif col == MCOL_CURRENT: val = row.get("current_stock", 0)
        elif col == MCOL_MIN_ALERT: val = row.get("minimum_stock_alert", 10)
        elif col == MCOL_MFG_DATE: val = (row.get("mfg_date") or "—")[:10]
        elif col == MCOL_EXPIRY: val = (row.get("expiry_date") or "—")[:10]
        elif col == MCOL_POST_EXPIRY: val = row.get("dispensed_after_expiry", 0)

        if role == Qt.DisplayRole:
            return str(val)
        elif role == Qt.BackgroundRole:
            return QBrush(_expiry_color(row.get("expiry_date", ""))) if _expiry_color(row.get("expiry_date", "")) else None
        elif role == Qt.ForegroundRole and col == MCOL_CURRENT:
            if row.get("current_stock", 0) <= row.get("minimum_stock_alert", 10):
                return QBrush(QColor("#dc2626"))
        elif role == Qt.FontRole and col == MCOL_CURRENT:
            if row.get("current_stock", 0) <= row.get("minimum_stock_alert", 10):
                return QFont("Segoe UI", 10, QFont.Bold)
        elif role == Qt.UserRole:
            return row
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

class EquipmentTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = EQUIP_COLS

    def update_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None
        row = self._data[index.row()]
        col = index.column()
        disposal = row.get("disposal_required", 0)

        val = ""
        if col == ECOL_ID: val = row.get("id", "")
        elif col == ECOL_NAME: val = row.get("name", "")
        elif col == ECOL_CATEGORY: val = row.get("category") or "—"
        elif col == ECOL_QTY: val = row.get("quantity", 0)
        elif col == ECOL_DISPOSAL: val = "⚠ Yes" if disposal else "No"
        elif col == ECOL_PURCHASE: val = (row.get("purchase_date") or "—")[:10]
        elif col == ECOL_SERVICED: val = (row.get("last_serviced_date") or "—")[:10]

        if role == Qt.DisplayRole:
            return str(val)
        elif role == Qt.ForegroundRole and col == ECOL_DISPOSAL and disposal:
            return QBrush(QColor("#d97706"))
        elif role == Qt.UserRole:
            return row
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

class MedicineListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_size = 25
        self._modes = ["all", "expiring", "expired", "low", "equipment"]
        self._pages = {m: 0 for m in self._modes}
        self._models = {}
        self._tables = {}
        
        self._build_ui()
        self._load_subtypes()
        self._refresh_all()

    def cleanup(self):
        """Memory Management: Release data when leaving the screen"""
        for model in self._models.values():
            model.update_data([])
        self._pages = {m: 0 for m in self._modes}
        self.tabs.setTabText(1, "⏳  Expiring ( - )")
        self.tabs.setTabText(2, "🔴  Expired ( - )")
        self.tabs.setTabText(3, "📉  Low Stock ( - )")

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)
        root.addWidget(self._build_header())
        root.addWidget(self._build_stats_bar())
        root.addWidget(self._build_tabs(), stretch=1)

    def _build_header(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Inventory")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Manage medicines, stock levels, and equipment")
        subtitle.setObjectName("PageSubtitle")
        vb = QVBoxLayout()
        vb.addWidget(title)
        vb.addWidget(subtitle)
        
        btn_misc = QPushButton("＋ Add Misc")
        btn_misc.setObjectName("BtnSecondary")
        btn_misc.clicked.connect(self._on_add_misc)

        btn_equip = QPushButton("＋ Equipment")
        btn_equip.setObjectName("BtnSecondary")
        btn_equip.clicked.connect(self._on_add_equipment)
        
        btn_add = QPushButton("＋ Add Medicine")
        btn_add.setObjectName("BtnPrimary")
        btn_add.clicked.connect(self._on_add_medicine)
        
        h.addLayout(vb)
        h.addStretch()
        h.addWidget(btn_misc)
        h.addWidget(btn_equip)
        h.addWidget(btn_add)
        return w

    def _build_stats_bar(self) -> QFrame:
        self._stats_frame = QFrame()
        self._stats_frame.setObjectName("Card")
        h = QHBoxLayout(self._stats_frame)
        self._stat_meds = self._stat_label("Total Medicines", "0", "#0d9488")
        self._stat_expired = self._stat_label("Expired", "0", "#dc2626")
        self._stat_expiring = self._stat_label("Expiring Soon", "0", "#d97706")
        self._stat_low = self._stat_label("Low Stock", "0", "#7c3aed")
        self._stat_equip = self._stat_label("Total Equipment", "0", "#0284c7")
        self._stat_disp = self._stat_label("Disposal Needed", "0", "#b45309")
        
        for w in (self._stat_meds, self._stat_expired, self._stat_expiring,
                  self._stat_low, self._stat_equip, self._stat_disp):
            h.addWidget(w)
        h.addStretch()
        return self._stats_frame

    def _stat_label(self, title: str, value: str, color: str) -> QWidget:
        w = QWidget()
        vb = QVBoxLayout(w)
        vb.setContentsMargins(0,0,0,0)
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"font-size:20px; font-weight:bold; color:{color};")
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size:11px; color:#64748b;")
        vb.addWidget(lbl_val)
        vb.addWidget(lbl_title)
        setattr(self, f"_stat_val_{title.split()[0].lower()}", lbl_val)
        return w

    def _build_tabs(self) -> QTabWidget:
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_medicine_tab("all"), "💊  All Medicines")
        self.tabs.addTab(self._build_medicine_tab("expiring"), "⏳  Expiring Soon")
        self.tabs.addTab(self._build_medicine_tab("expired"), "🔴  Expired")
        self.tabs.addTab(self._build_medicine_tab("low"), "📉  Low Stock")
        self.tabs.addTab(self._build_equipment_tab(), "🔧  Equipment")
        self.tabs.currentChanged.connect(lambda: self._refresh_current_tab())
        return self.tabs

    def _build_medicine_tab(self, mode: str) -> QWidget:
        w = QWidget()
        vb = QVBoxLayout(w)
        
        if mode == "all":
            filter_row = QFrame()
            filter_row.setObjectName("Card")
            h = QHBoxLayout(filter_row)
            
            self._search_all = QLineEdit()
            self._search_all.setPlaceholderText("🔍 Search medicines...")
            self._search_all.returnPressed.connect(lambda: self._on_filter_changed(mode))
            
            self._subtype_filter = StyledComboBox()
            self._subtype_filter.addItem("All Subtypes")
            self._subtype_filter.currentIndexChanged.connect(lambda: self._on_filter_changed(mode))
            
            h.addWidget(self._search_all, stretch=2)
            h.addWidget(QLabel("Subtype:"))
            h.addWidget(self._subtype_filter)
            vb.addWidget(filter_row)

        table = QTableView()
        model = MedicineTableModel()
        table.setModel(model)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.setColumnHidden(MCOL_ID, True)
        
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(MCOL_NAME, QHeaderView.Stretch)
        for col in (MCOL_SUBTYPE, MCOL_DOSAGE, MCOL_BATCH, MCOL_RECEIVED, MCOL_CURRENT,
                MCOL_MIN_ALERT, MCOL_MFG_DATE, MCOL_EXPIRY, MCOL_POST_EXPIRY):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self._models[mode] = model
        self._tables[mode] = table
        vb.addWidget(table, stretch=1)
        vb.addWidget(self._build_medicine_action_bar(mode))
        return w

    def _build_equipment_tab(self) -> QWidget:
        w = QWidget()
        vb = QVBoxLayout(w)
        
        filter_row = QFrame()
        filter_row.setObjectName("Card")
        h = QHBoxLayout(filter_row)
        
        self.eq_search = QLineEdit()
        self.eq_search.setPlaceholderText("🔍 Search equipment...")
        self.eq_search.returnPressed.connect(lambda: self._on_filter_changed("equipment"))
        
        self.cat_filter = StyledComboBox()
        self.cat_filter.addItems(["All Categories", "Instrument", "Equipment", "Miscellaneous"])
        self.cat_filter.currentIndexChanged.connect(lambda: self._on_filter_changed("equipment"))
        
        self.disposal_filter = StyledComboBox()
        self.disposal_filter.addItems(["All", "Needs Disposal", "No Disposal"])
        self.disposal_filter.currentIndexChanged.connect(lambda: self._on_filter_changed("equipment"))

        h.addWidget(self.eq_search, stretch=2)
        h.addWidget(QLabel("Category:"))
        h.addWidget(self.cat_filter)
        h.addWidget(QLabel("Disposal:"))
        h.addWidget(self.disposal_filter)
        vb.addWidget(filter_row)

        table = QTableView()
        model = EquipmentTableModel()
        table.setModel(model)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.setColumnHidden(ECOL_ID, True)

        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(ECOL_NAME, QHeaderView.Stretch)
        for col in (ECOL_CATEGORY, ECOL_QTY, ECOL_DISPOSAL, ECOL_PURCHASE, ECOL_SERVICED):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self._models["equipment"] = model
        self._tables["equipment"] = table
        
        vb.addWidget(table, stretch=1)
        
        # Action Bar with Pagination
        action_w = QWidget()
        hb = QHBoxLayout(action_w)
        btn_edit = QPushButton("✏ Edit")
        btn_del = QPushButton("🗑 Delete")
        btn_del.setObjectName("BtnDanger")
        hb.addWidget(btn_edit)
        hb.addWidget(btn_del)
        hb.addStretch()
        
        btn_edit.clicked.connect(self._on_edit_equipment)
        btn_del.clicked.connect(self._on_delete_equipment)

        self.lbl_eq_page = QLabel("Page 1")
        btn_prev = QPushButton("❮ Prev")
        btn_next = QPushButton("Next ❯")
        btn_prev.clicked.connect(lambda: self._on_prev_page("equipment"))
        btn_next.clicked.connect(lambda: self._on_next_page("equipment"))
        
        setattr(self, f"_btn_prev_equipment", btn_prev)
        setattr(self, f"_btn_next_equipment", btn_next)
        
        hb.addWidget(self.lbl_eq_page)
        hb.addWidget(btn_prev)
        hb.addWidget(btn_next)
        vb.addWidget(action_w)
        return w

    def _build_medicine_action_bar(self, mode: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0,0,0,0)
        
        btn_edit = QPushButton("✏ Edit")
        btn_dispense = QPushButton("💊 Dispense")
        btn_restock = QPushButton("📦 Restock")
        btn_del = QPushButton("🗑 Delete")
        btn_del.setObjectName("BtnDanger")
        
        table = self._tables[mode]
        btn_edit.clicked.connect(lambda: self._on_edit_medicine(table))
        btn_dispense.clicked.connect(lambda: self._on_dispense(table))
        btn_restock.clicked.connect(lambda: self._on_restock(table))
        btn_del.clicked.connect(lambda: self._on_delete_medicine(table))
        
        h.addWidget(btn_edit)
        h.addWidget(btn_dispense)
        h.addWidget(btn_restock)
        h.addWidget(btn_del)
        h.addStretch()
        
        lbl_page = QLabel("Page 1")
        btn_prev = QPushButton("❮ Prev")
        btn_next = QPushButton("Next ❯")
        btn_prev.clicked.connect(lambda: self._on_prev_page(mode))
        btn_next.clicked.connect(lambda: self._on_next_page(mode))
        
        setattr(self, f"_lbl_page_{mode}", lbl_page)
        setattr(self, f"_btn_prev_{mode}", btn_prev)
        setattr(self, f"_btn_next_{mode}", btn_next)
        
        h.addWidget(lbl_page)
        h.addWidget(btn_prev)
        h.addWidget(btn_next)
        return w

    def _load_subtypes(self):
        self._subtype_filter.blockSignals(True)
        self._subtype_filter.clear()
        self._subtype_filter.addItem("All Subtypes", None)
        for st in get_medicine_subtypes():
            self._subtype_filter.addItem(st["name"], st["id"])
        self._subtype_filter.blockSignals(False)

    def _on_filter_changed(self, mode: str):
        self._pages[mode] = 0
        self._refresh_tab(mode)

    def _on_prev_page(self, mode: str):
        if self._pages[mode] > 0:
            self._pages[mode] -= 1
            self._refresh_tab(mode)

    def _on_next_page(self, mode: str):
        self._pages[mode] += 1
        self._refresh_tab(mode)

    def _refresh_current_tab(self):
        idx = self.tabs.currentIndex()
        if 0 <= idx < len(self._modes):
            self._refresh_tab(self._modes[idx])

    def _refresh_all(self):
        self._pages = {m: 0 for m in self._modes}
        for mode in self._modes:
            self._refresh_tab(mode)
        self._update_stats()

    def _refresh_tab(self, mode: str):
        offset = self._pages[mode] * self.page_size
        results = []
        
        if mode == "all":
            q = self._search_all.text().strip() or None
            sid = self._subtype_filter.currentData()
            results = search_medicines(query=q, subtype_id=sid, limit=self.page_size, offset=offset)
        elif mode == "expiring":
            results = search_medicines(expiring_in_months=2, limit=self.page_size, offset=offset)
        elif mode == "expired":
            results = search_medicines(expired_only=True, limit=self.page_size, offset=offset)
        elif mode == "low":
            results = search_medicines(low_stock_only=True, limit=self.page_size, offset=offset)
        elif mode == "equipment":
            q = self.eq_search.text().strip() or None
            cat = self.cat_filter.currentText()
            dis = self.disposal_filter.currentText()
            cat_val = None if cat == "All Categories" else cat
            dis_val = True if dis == "Needs Disposal" else False if dis == "No Disposal" else None
            results = search_equipment(query=q, category=cat_val, disposal_required=dis_val, limit=self.page_size, offset=offset)
            
        self._models[mode].update_data(results)
        
        # Update pagination UI
        lbl = getattr(self, f"_lbl_page_{mode}", getattr(self, "lbl_eq_page", None))
        btn_prev = getattr(self, f"_btn_prev_{mode}", None)
        btn_next = getattr(self, f"_btn_next_{mode}", None)
        
        if lbl: lbl.setText(f"Page {self._pages[mode] + 1}")
        if btn_prev: btn_prev.setEnabled(self._pages[mode] > 0)
        if btn_next: btn_next.setEnabled(len(results) == self.page_size)

    def _update_stats(self):
        stats = get_inventory_stats()
        self._stat_val_total.setText(str(stats.get("total_medicines", 0)))
        self._stat_val_expired.setText(str(stats.get("expired_count", 0)))
        self._stat_val_expiring.setText(str(stats.get("expiring_soon_count", 0)))
        self._stat_val_low.setText(str(stats.get("low_stock_count", 0)))
        self._stat_val_total.setText(str(stats.get("total_equipment", 0)))
        self._stat_val_disposal.setText(str(stats.get("disposal_needed_count", 0)))

    def _get_selected_id(self, table: QTableView) -> int:
        sel = table.selectionModel().selectedRows()
        if not sel: return None
        model = table.model()
        return model._data[sel[0].row()]["id"]

    def _on_add_medicine(self):
        if MedicineFormDialog(parent=self).exec(): 
            self._refresh_all()

    def _on_edit_medicine(self, table):
        mid = self._get_selected_id(table)
        if mid and MedicineFormDialog(medicine_id=mid, parent=self).exec():
            self._refresh_all()

    def _on_restock(self, table):
        mid = self._get_selected_id(table)
        if not mid: return
        from PySide6.QtWidgets import QInputDialog
        qty, ok = QInputDialog.getInt(self, "Restock Medicine", "Enter quantity:", 1, 1, 10000)
        if ok:
            from database.inventory_queries import restock_medicine
            restock_medicine(mid, qty)
            self._refresh_all()

    def _on_dispense(self, table):
        mid = self._get_selected_id(table)
        if mid:
            from ui.inventory.inventory_form import DispenseDialog
            if DispenseDialog(medicine_id=mid, parent=self).exec():
                self._refresh_all()

    def _on_delete_medicine(self, table):
        mid = self._get_selected_id(table)
        if mid:
            rm = QMessageBox.warning(self, "Delete", "Delete?", QMessageBox.Yes | QMessageBox.Cancel)
            if rm == QMessageBox.Yes:
                delete_medicine(mid)
                self._refresh_all()

    def _on_add_equipment(self):
        if EquipmentFormDialog(parent=self).exec():
            self._refresh_all()
            self.tabs.setCurrentIndex(4)

    def _on_add_misc(self):
        if EquipmentFormDialog(parent=self, default_category="Miscellaneous").exec():
            self._refresh_all()
            self.tabs.setCurrentIndex(4)

    def _on_edit_equipment(self):
        eid = self._get_selected_id(self._tables["equipment"])
        if eid and EquipmentFormDialog(equipment_id=eid, parent=self).exec():
            self._refresh_all()

    def _on_delete_equipment(self):
        eid = self._get_selected_id(self._tables["equipment"])
        if eid:
            rm = QMessageBox.warning(self, "Delete", "Delete?", QMessageBox.Yes | QMessageBox.Cancel)
            if rm == QMessageBox.Yes:
                delete_equipment(eid)
                self._refresh_all()
