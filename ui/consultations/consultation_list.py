"""
consultation_list.py
--------------------
System-wide consultations page (sidebar index 2).

Features:
  - Searchable table of all visits (newest first)
  - Filter by visit type and date range
  - Click a row to see visit details in the right pane
  - "New Consultation" button → patient picker → ConsultationFormDialog
"""

from datetime import datetime, date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QSplitter, QTextEdit, QLineEdit, QComboBox, QDateEdit,
    QSizePolicy, QCheckBox
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont

from database.visit_queries import search_visits


# ── Table columns ─────────────────────────────────────────────────────────────
COL_ID       = 0
COL_DATE     = 1
COL_PATIENT  = 2
COL_TYPE     = 3
COL_SAP      = 4
COL_CATEGORY = 5
COL_DIAGNOSIS= 6

HEADERS = ["ID", "Date", "Patient", "Type", "SAP ID", "Category", "Diagnosis"]

VISIT_TYPE_COLORS = {
    "Walk-in":   "#0d9488",
    "Scheduled": "#7c3aed",
    "Emergency": "#dc2626",
}


def _fmt_date(raw: str) -> str:
    if not raw:
        return "—"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw[:19], fmt)
            return dt.strftime("%d %b %Y  %H:%M")
        except ValueError:
            continue
    return raw[:10]


# ─────────────────────────────────────────────────────────────────────────────
#  DETAIL PANE
# ─────────────────────────────────────────────────────────────────────────────

class ConsultDetailPane(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumWidth(300)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        title = QLabel("Consultation Details")
        title.setObjectName("SectionHeader")
        root.addWidget(title)

        self.area = QTextEdit()
        self.area.setReadOnly(True)
        self.area.setStyleSheet("border:none; background:transparent; font-size:13px;")
        root.addWidget(self.area, stretch=1)

    def show_visit(self, v: dict):
        def yn(val): return "✅ Yes" if val else "No"
        lines = [
            f"<b>Date:</b> {_fmt_date(v.get('visit_date', ''))}",
            f"<b>Patient:</b> {v.get('patient_name', '—')}  "
            f"<span style='color:#64748b;font-size:11px;'>SAP {v.get('patient_sap_id', '—')}</span>",
            f"<b>Type:</b> {v.get('visit_type', '—')}",
            f"<b>Category:</b> {v.get('category_name') or '—'}",
            "",
            f"<b>Chief Complaint:</b><br>{v.get('chief_complaint') or '—'}",
            f"<b>Diagnosis:</b><br>{v.get('diagnosis') or '—'}",
            f"<b>Investigations:</b><br>{v.get('investigations') or '—'}",
            f"<b>Treatment:</b><br>{v.get('treatment') or '—'}",
            f"<b>Prescription:</b><br>{v.get('prescription') or '—'}",
            "",
            f"<b>Referral:</b> {v.get('referral') or 'None'}",
            f"<b>Rest Days:</b> {v.get('rest_days') or 0}",
            f"<b>Medical Leave:</b> {yn(v.get('medical_leave'))}",
            f"<b>Ambulance Used:</b> {yn(v.get('ambulance_used'))}",
        ]
        if v.get("follow_up_date"):
            lines.append(f"<b>Follow-up:</b> {v['follow_up_date']}")
        if v.get("notes"):
            lines.append(f"<br><b>Notes:</b><br>{v['notes']}")
        self.area.setHtml("<br>".join(lines))

    def clear(self):
        self.area.setHtml(
            "<span style='color:#94a3b8;'>Select a consultation to view details.</span>"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class ConsultationListWidget(QWidget):
    """
    Full-page consultations view. Drop-in replacement for the placeholder
    at index 2 in main_window.py's QStackedWidget.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._visits: list[dict] = []
        self._build_ui()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # Header row
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Consultations")
        title.setObjectName("PageTitle")
        sub = QLabel("All patient consultations and visits")
        sub.setObjectName("PageSubtitle")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        hdr.addLayout(title_col)
        hdr.addStretch()

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color:#64748b; font-size:12px;")
        hdr.addWidget(self.lbl_count)
        root.addLayout(hdr)

        # Filter bar
        root.addWidget(self._build_filter_bar())

        # Splitter: table + detail pane
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        lv.addWidget(self._build_table())
        splitter.addWidget(left)

        self.detail_pane = ConsultDetailPane()
        self.detail_pane.clear()
        splitter.addWidget(self.detail_pane)
        splitter.setSizes([700, 340])

        root.addWidget(splitter, stretch=1)

    def _build_filter_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("Card")
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(10)

        # Search
        self.search = QLineEdit()
        self.search.setObjectName("SearchBar")
        self.search.setPlaceholderText("🔍  Search patient name or SAP ID…")
        self.search.setMinimumWidth(220)
        self.search.textChanged.connect(self._apply_filters)

        # Visit type filter
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["All Types", "Walk-in", "Scheduled", "Emergency"])
        self.cmb_type.setFixedWidth(130)
        self.cmb_type.currentTextChanged.connect(self._apply_filters)

        # Date from / to
        today = QDate.currentDate()
        lbl_from = QLabel("From:")
        lbl_from.setStyleSheet("color:#64748b; font-size:12px;")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd MMM yyyy")
        self.date_from.setDate(today.addDays(-30))
        self.date_from.setFixedWidth(120)
        self.date_from.dateChanged.connect(self._apply_filters)

        lbl_to = QLabel("To:")
        lbl_to.setStyleSheet("color:#64748b; font-size:12px;")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd MMM yyyy")
        self.date_to.setDate(today)
        self.date_to.setFixedWidth(120)
        self.date_to.dateChanged.connect(self._apply_filters)

        # "All time" toggle
        self.chk_all_time = QCheckBox("All time")
        self.chk_all_time.setStyleSheet("color:#475569;")
        self.chk_all_time.toggled.connect(self._on_all_time_toggled)

        btn_refresh = QPushButton("↻  Refresh")
        btn_refresh.setFixedWidth(90)
        btn_refresh.clicked.connect(self._refresh)

        h.addWidget(self.search)
        h.addWidget(self.cmb_type)
        h.addSpacing(6)
        h.addWidget(lbl_from)
        h.addWidget(self.date_from)
        h.addWidget(lbl_to)
        h.addWidget(self.date_to)
        h.addWidget(self.chk_all_time)
        h.addStretch()
        h.addWidget(btn_refresh)
        return bar

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget()
        self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setColumnHidden(COL_ID, True)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(COL_DIAGNOSIS, QHeaderView.Stretch)
        for col in (COL_DATE, COL_PATIENT, COL_TYPE, COL_SAP, COL_CATEGORY):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self.table.itemSelectionChanged.connect(self._on_row_selected)
        return self.table

    # ── Data ──────────────────────────────────────────────────────────────────

    def _refresh(self):
        """Re-fetch from DB and repopulate the table."""
        date_from = None
        date_to   = None
        if not self.chk_all_time.isChecked():
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to   = self.date_to.date().toString("yyyy-MM-dd")

        vtype = self.cmb_type.currentText()
        vtype = None if vtype == "All Types" else vtype

        name_or_sap = self.search.text().strip()
        patient_name = name_or_sap if name_or_sap else None
        sap_id       = name_or_sap if name_or_sap else None

        # Search by name OR sap — fetch both and merge (simple approach)
        rows_by_name = search_visits(
            patient_name=patient_name,
            visit_type=vtype,
            date_from=date_from,
            date_to=date_to,
            limit=500,
        )
        if name_or_sap:
            rows_by_sap = search_visits(
                sap_id=sap_id,
                visit_type=vtype,
                date_from=date_from,
                date_to=date_to,
                limit=500,
            )
            # Merge deduped
            seen = {r["id"] for r in rows_by_name}
            self._visits = rows_by_name + [r for r in rows_by_sap if r["id"] not in seen]
        else:
            self._visits = rows_by_name

        self._populate_table(self._visits)

    def _apply_filters(self):
        """Called on any filter widget change."""
        self._refresh()

    def _on_all_time_toggled(self, checked: bool):
        self.date_from.setEnabled(not checked)
        self.date_to.setEnabled(not checked)
        self._refresh()

    def _populate_table(self, visits: list[dict]):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for r, v in enumerate(visits):
            self.table.insertRow(r)
            vtype = v.get("visit_type", "Walk-in")
            cells = [
                str(v.get("id", "")),
                _fmt_date(v.get("visit_date") or ""),
                v.get("patient_name") or "—",
                vtype,
                v.get("patient_sap_id") or "—",
                v.get("category_name") or "—",
                v.get("diagnosis") or "—",
            ]
            for col, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if col == COL_TYPE:
                    color = VISIT_TYPE_COLORS.get(vtype, "#475569")
                    item.setForeground(QColor(color))
                self.table.setItem(r, col, item)

        self.table.setSortingEnabled(True)
        count = len(visits)
        self.lbl_count.setText(f"{count} consultation{'s' if count != 1 else ''}")
        self.detail_pane.clear()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_row_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visits):
            self.detail_pane.clear()
            return
        visit_id_item = self.table.item(row, COL_ID)
        if not visit_id_item:
            self.detail_pane.clear()
            return
        vid = int(visit_id_item.text())
        visit = next((v for v in self._visits if v["id"] == vid), None)
        if visit:
            self.detail_pane.show_visit(visit)

    # Called by main_window._navigate() when switching to this page
    def _refresh_all(self):
        self._refresh()
