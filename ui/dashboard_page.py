"""
dashboard_page.py
-----------------
The main active dashboard greeting the user.
Displays critical alerts:
  - Low stock medicines
  - Medicines expiring within 30 days
  - Expected follow-ups for today
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor, QPixmap

from database.inventory_queries import get_expiring_soon, get_low_stock_medicines
from database.visit_queries import get_followups_for_date

class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # Top half logo + label
        logo = QLabel()
        logo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        pix = QPixmap("assets/icons/logo.png")
        if not pix.isNull():
            logo.setPixmap(pix.scaledToHeight(180, Qt.SmoothTransformation))

        top_label = QLabel("NMIMS CLINICA")
        top_label.setStyleSheet("font-size:48px; font-weight:bold; color:#0f172a;")
        top_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(30)
        top_layout.addStretch(1)
        top_layout.addWidget(logo, alignment=Qt.AlignCenter | Qt.AlignVCenter)
        top_layout.addWidget(top_label, alignment=Qt.AlignCenter | Qt.AlignVCenter)
        top_layout.addStretch(1)

        root.addWidget(top_container, stretch=1)

        # Three column layout for cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        # 1. Low Stock Card
        self.card_low_stock, self.tbl_low_stock = self._create_alert_card(
            "⚠️ Low Stock",
            ["Medicine", "Stock", "Min"]
        )
        cards_layout.addWidget(self.card_low_stock)

        # 2. Expiring Soon Card
        self.card_expiring, self.tbl_expiring = self._create_alert_card(
            "🔴 Expiring < 30 Days",
            ["Medicine", "Batch", "Expiry"]
        )
        cards_layout.addWidget(self.card_expiring)

        # 3. Today's Follow-ups Card
        self.card_followups, self.tbl_followups = self._create_alert_card(
            "📅 Today's Follow-ups",
            ["Patient Name", "SAP ID", "Reason"]
        )
        cards_layout.addWidget(self.card_followups)

        root.addLayout(cards_layout, stretch=1)

    def _create_alert_card(self, title_text: str, headers: list[str]) -> tuple[QFrame, QTableWidget]:
        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(12)

        lbl = QLabel(title_text)
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        cl.addWidget(lbl)

        tbl = QTableWidget()
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(headers)):
            tbl.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)

        cl.addWidget(tbl)
        return card, tbl

    def _set_empty_state(self, tbl: QTableWidget, msg: str = "None"):
        tbl.insertRow(0)
        item = QTableWidgetItem(msg)
        item.setForeground(QColor("#94a3b8"))
        item.setFont(QFont("Segoe UI", 10, italic=True))
        item.setTextAlignment(Qt.AlignCenter)
        tbl.setItem(0, 0, item)
        if tbl.columnCount() > 1:
            tbl.setSpan(0, 0, 1, tbl.columnCount())

    def refresh_data(self):
        """Fetches data from DB and populates tables."""
        
        # 1. Low Stock
        low_stock = get_low_stock_medicines()
        self.tbl_low_stock.setRowCount(0)
        if not low_stock:
            self._set_empty_state(self.tbl_low_stock)
        else:
            for r, m in enumerate(low_stock):
                self.tbl_low_stock.insertRow(r)
                self.tbl_low_stock.setItem(r, 0, QTableWidgetItem(m.get("name", "")))
                item_stock = QTableWidgetItem(str(m.get("current_stock", 0)))
                item_stock.setForeground(QColor("#dc2626"))
                item_stock.setFont(QFont("Segoe UI", 10, QFont.Bold))
                self.tbl_low_stock.setItem(r, 1, item_stock)
                self.tbl_low_stock.setItem(r, 2, QTableWidgetItem(str(m.get("minimum_stock_alert", 0))))

        # 2. Expiring Soon (1 month threshold)
        expiring = get_expiring_soon(months=1)
        self.tbl_expiring.setRowCount(0)
        if not expiring:
            self._set_empty_state(self.tbl_expiring)
        else:
            for r, m in enumerate(expiring):
                self.tbl_expiring.insertRow(r)
                self.tbl_expiring.setItem(r, 0, QTableWidgetItem(m.get("name", "")))
                self.tbl_expiring.setItem(r, 1, QTableWidgetItem(m.get("batch_number", "")))
                item_exp = QTableWidgetItem(m.get("expiry_date", ""))
                item_exp.setForeground(QColor("#dc2626"))
                item_exp.setFont(QFont("Segoe UI", 10, QFont.Bold))
                self.tbl_expiring.setItem(r, 2, item_exp)

        # 3. Follow-Ups for Today
        today_str = QDate.currentDate().toString("yyyy-MM-dd")
        followups = get_followups_for_date(today_str)
        self.tbl_followups.setRowCount(0)
        if not followups:
            self._set_empty_state(self.tbl_followups)
        else:
            for r, f in enumerate(followups):
                self.tbl_followups.insertRow(r)
                self.tbl_followups.setItem(r, 0, QTableWidgetItem(f.get("patient_name", "")))
                self.tbl_followups.setItem(r, 1, QTableWidgetItem(f.get("patient_sap_id", "")))
                self.tbl_followups.setItem(r, 2, QTableWidgetItem(f.get("category_name", "Review")))
