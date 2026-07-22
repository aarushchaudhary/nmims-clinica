"""
models/inventory.py
--------------------
Dataclasses for all inventory-related records:
  - MedicineSubtype   — lookup table object
  - Medicine          — a medicine batch in stock
  - DispenseRecord    — one dispense event from the log
  - Equipment         — instrument / equipment item
"""

from __future__ import annotations
from dataclasses import dataclass, field, fields
from datetime import datetime, date, timedelta
from typing import Optional


VALID_EQUIP_CATEGORIES = {"Instrument", "Equipment", "Miscellaneous"}

# Medicines expiring within this many days are considered "expiring soon"
EXPIRY_SOON_DAYS = 60


# ─────────────────────────────────────────────────────────────────────────────
#  MEDICINE SUBTYPE  (lookup)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MedicineSubtype:
    id: int
    name: str

    @classmethod
    def from_dict(cls, data: dict) -> "MedicineSubtype":
        return cls(id=data["id"], name=data["name"])

    def __str__(self) -> str:
        return self.name


# ─────────────────────────────────────────────────────────────────────────────
#  MEDICINE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Medicine:
    # ── Required ─────────────────────────────────────────────────────────────
    name: str
    expiry_date: str            # ISO date string: 'YYYY-MM-DD'

    # ── Optional / defaults ──────────────────────────────────────────────────
    id: Optional[int]           = None
    subtype_id: Optional[int]   = None
    subtype_name: Optional[str] = None   # populated by JOINed queries
    batch_number: Optional[str] = None
    supplier: Optional[str]     = None

    stock_received: int         = 0
    current_stock: int          = 0
    minimum_stock_alert: int    = 10

    mfg_date: Optional[str]     = None   # ISO date
    dispensed_after_expiry: int = 0

    notes: Optional[str]        = None
    created_at: Optional[str]   = None
    updated_at: Optional[str]   = None

    # ── Validation ────────────────────────────────────────────────────────────

    def __post_init__(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Medicine name cannot be empty.")
        if not self.expiry_date:
            raise ValueError("expiry_date is required.")
        if self.stock_received < 0:
            raise ValueError("stock_received cannot be negative.")
        if self.current_stock < 0:
            raise ValueError("current_stock cannot be negative.")
        if self.minimum_stock_alert < 0:
            self.minimum_stock_alert = 0

    # ── Constructors ─────────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, data: dict) -> "Medicine":
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @classmethod
    def from_db_row(cls, row) -> "Medicine":
        return cls.from_dict(dict(row))

    # ── Derived status properties ──────────────────────────────────────────────

    @property
    def expiry_date_obj(self) -> Optional[date]:
        try:
            return date.fromisoformat(self.expiry_date[:10])
        except (ValueError, TypeError):
            return None

    @property
    def days_to_expiry(self) -> Optional[int]:
        exp = self.expiry_date_obj
        if exp is None:
            return None
        return (exp - date.today()).days

    @property
    def is_expired(self) -> bool:
        days = self.days_to_expiry
        return days is not None and days < 0

    @property
    def is_expiring_soon(self) -> bool:
        """True if expires within EXPIRY_SOON_DAYS but not yet expired."""
        days = self.days_to_expiry
        return days is not None and 0 <= days <= EXPIRY_SOON_DAYS

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.minimum_stock_alert

    @property
    def is_out_of_stock(self) -> bool:
        return self.current_stock == 0

    @property
    def stock_status(self) -> str:
        """Human-readable stock status for display."""
        if self.is_out_of_stock:
            return "Out of Stock"
        if self.is_low_stock:
            return "Low Stock"
        return "OK"

    @property
    def expiry_status(self) -> str:
        """Human-readable expiry status."""
        if self.is_expired:
            return "Expired"
        if self.is_expiring_soon:
            days = self.days_to_expiry
            return f"Expiring in {days}d"
        return "OK"

    # ── Serialization ─────────────────────────────────────────────────────────

    @property
    def consumed(self) -> int:
        """Quantity consumed since last added/received."""
        return max(0, (self.stock_received or 0) - (self.current_stock or 0))

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def to_export_row(self) -> dict:
        return {
            "ID":                       self.id,
            "Name":                     self.name,
            "Subtype":                  self.subtype_name or "",
            "Batch Number":             self.batch_number or "",
            "Stock Received":           self.stock_received,
            "Consumed":                 self.consumed,
            "Current Stock":            self.current_stock,
            "Stock Status":             self.stock_status,
            "Expiry Date":              self._fmt_date(self.expiry_date),
            "Expiry Status":            self.expiry_status,
            "Days To Expiry":           self.days_to_expiry if not self.is_expired else "EXPIRED",
            "Dispensed After Expiry":   self.dispensed_after_expiry,
            "Notes":                    self.notes or "",
        }

    @staticmethod
    def _fmt_date(dt_str: Optional[str]) -> str:
        if not dt_str:
            return ""
        try:
            return datetime.fromisoformat(dt_str[:10]).strftime("%d %b %Y")
        except ValueError:
            return dt_str

    def __str__(self) -> str:
        return (
            f"Medicine(id={self.id}, name={self.name}, "
            f"stock={self.current_stock}, expiry={self.expiry_date})"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  DISPENSE RECORD
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DispenseRecord:
    medicine_id: int
    quantity: int

    id: Optional[int]               = None
    visit_id: Optional[int]         = None
    dispensed_at: Optional[str]     = None
    dispensed_by: Optional[str]     = None
    notes: Optional[str]            = None

    # Joined fields
    medicine_name: Optional[str]    = None
    patient_name: Optional[str]     = None
    patient_sap_id: Optional[str]   = None

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError(f"quantity must be > 0. Got: {self.quantity}")

    @classmethod
    def from_dict(cls, data: dict) -> "DispenseRecord":
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def to_export_row(self) -> dict:
        return {
            "Dispense ID":    self.id,
            "Medicine":       self.medicine_name or str(self.medicine_id),
            "Quantity":       self.quantity,
            "Patient":        self.patient_name or "",
            "SAP ID":         self.patient_sap_id or "",
            "Dispensed By":   self.dispensed_by or "",
            "Dispensed At":   self._fmt_dt(self.dispensed_at),
            "Notes":          self.notes or "",
        }

    @staticmethod
    def _fmt_dt(dt_str: Optional[str]) -> str:
        if not dt_str:
            return ""
        try:
            return datetime.fromisoformat(dt_str).strftime("%d %b %Y %H:%M")
        except ValueError:
            return dt_str

    def __str__(self) -> str:
        return (
            f"DispenseRecord(id={self.id}, medicine_id={self.medicine_id}, "
            f"qty={self.quantity}, at={self.dispensed_at})"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  EQUIPMENT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Equipment:
    name: str
    category: str = "Instrument"       # 'Instrument' | 'Equipment' | 'Miscellaneous'

    id: Optional[int]                  = None
    quantity: int                      = 0
    disposal_required: bool            = False
    purchase_date: Optional[str]       = None
    last_serviced_date: Optional[str]  = None
    notes: Optional[str]               = None
    created_at: Optional[str]          = None
    updated_at: Optional[str]          = None

    def __post_init__(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Equipment name cannot be empty.")
        if self.category not in VALID_EQUIP_CATEGORIES:
            raise ValueError(
                f"category must be one of {VALID_EQUIP_CATEGORIES}. Got: '{self.category}'"
            )
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative.")
        # Coerce int (0/1) from DB to bool
        if isinstance(self.disposal_required, int):
            self.disposal_required = bool(self.disposal_required)

    @classmethod
    def from_dict(cls, data: dict) -> "Equipment":
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @classmethod
    def from_db_row(cls, row) -> "Equipment":
        return cls.from_dict(dict(row))

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def to_export_row(self) -> dict:
        return {
            "ID":               self.id,
            "Name":             self.name,
            "Category":         self.category,
            "Quantity":         self.quantity,
            "Disposal Required":"Yes" if self.disposal_required else "No",
            "Purchase Date":    self._fmt_date(self.purchase_date),
            "Last Serviced":    self._fmt_date(self.last_serviced_date),
            "Notes":            self.notes or "",
        }

    @staticmethod
    def _fmt_date(dt_str: Optional[str]) -> str:
        if not dt_str:
            return ""
        try:
            return datetime.fromisoformat(dt_str[:10]).strftime("%d %b %Y")
        except ValueError:
            return dt_str

    def __str__(self) -> str:
        return (
            f"Equipment(id={self.id}, name={self.name}, "
            f"qty={self.quantity}, category={self.category})"
        )