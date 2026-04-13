"""
models/visit.py
---------------
Dataclasses for Visit / Consultation records and Disease Categories.

Visit is the core clinical record — one per patient encounter.
DiseaseCategory is a simple lookup object for the category dropdown.
"""

from __future__ import annotations
from dataclasses import dataclass, field, fields
from datetime import datetime, date
from typing import Optional


VALID_VISIT_TYPES = {"Walk-in", "Scheduled", "Emergency"}


# ─────────────────────────────────────────────────────────────────────────────
#  DISEASE CATEGORY
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DiseaseCategory:
    id: int
    name: str
    is_custom: bool = False
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "DiseaseCategory":
        return cls(
            id=data["id"],
            name=data["name"],
            is_custom=bool(data.get("is_custom", 0)),
            created_at=data.get("created_at"),
        )

    def __str__(self) -> str:
        suffix = " ★" if self.is_custom else ""
        return f"{self.name}{suffix}"


# ─────────────────────────────────────────────────────────────────────────────
#  VISIT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Visit:
    # ── Required ────────────────────────────────────────────────────────────
    patient_id: int

    # ── Core clinical ────────────────────────────────────────────────────────
    id: Optional[int]               = None
    visit_type: str                 = "Walk-in"
    visit_date: Optional[str]       = None     # ISO datetime string

    chief_complaint: Optional[str]  = None
    diagnosis: Optional[str]        = None
    category_id: Optional[int]      = None
    investigations: Optional[str]   = None
    treatment: Optional[str]        = None
    prescription: Optional[str]     = None

    # ── Outcomes ────────────────────────────────────────────────────────────
    referral: Optional[str]         = None     # None = no referral
    rest_days: int                  = 0
    medical_leave: bool             = False
    ambulance_used: bool            = False
    follow_up_date: Optional[str]   = None

    notes: Optional[str]            = None

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at: Optional[str]       = None
    updated_at: Optional[str]       = None

    # ── Joined fields (populated by queries that JOIN other tables) ──────────
    patient_name: Optional[str]     = None
    patient_sap_id: Optional[str]   = None
    patient_type: Optional[str]     = None
    category_name: Optional[str]    = None

    # ── Validation ────────────────────────────────────────────────────────────

    def __post_init__(self):
        if not isinstance(self.patient_id, int) or self.patient_id <= 0:
            raise ValueError(f"patient_id must be a positive int. Got: {self.patient_id}")

        if self.visit_type not in VALID_VISIT_TYPES:
            raise ValueError(
                f"visit_type must be one of {VALID_VISIT_TYPES}. Got: '{self.visit_type}'"
            )

        # Coerce int DB values (0/1) to bool
        if isinstance(self.medical_leave, int):
            self.medical_leave = bool(self.medical_leave)
        if isinstance(self.ambulance_used, int):
            self.ambulance_used = bool(self.ambulance_used)

        if self.rest_days < 0:
            self.rest_days = 0

    # ── Constructors ─────────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, data: dict) -> "Visit":
        """
        Build from a raw DB dict. Ignores unknown keys.
        Handles joined columns (patient_name, category_name, etc.) transparently.
        """
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @classmethod
    def from_db_row(cls, row) -> "Visit":
        return cls.from_dict(dict(row))

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def to_export_row(self) -> dict:
        """
        Flat dict for Excel export. Joined patient/category fields used when available.
        """
        return {
            "Visit ID":          self.id,
            "Date":              self._fmt_date(self.visit_date),
            "Visit Type":        self.visit_type,
            "SAP ID":            self.patient_sap_id or "",
            "Patient Name":      self.patient_name or "",
            "Patient Type":      self.patient_type or "",
            "Disease Category":  self.category_name or "",
            "Chief Complaint":   self.chief_complaint or "",
            "Diagnosis":         self.diagnosis or "",
            "Investigations":    self.investigations or "",
            "Treatment":         self.treatment or "",
            "Prescription":      self.prescription or "",
            "Referral":          self.referral or "",
            "Rest Days":         self.rest_days,
            "Medical Leave":     "Yes" if self.medical_leave  else "No",
            "Ambulance Used":    "Yes" if self.ambulance_used else "No",
            "Follow-up Date":    self._fmt_date(self.follow_up_date),
            "Notes":             self.notes or "",
        }

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def has_referral(self) -> bool:
        return bool(self.referral and self.referral.strip())

    @property
    def visit_date_obj(self) -> Optional[date]:
        """Return a Python date object from the stored ISO string, if available."""
        if not self.visit_date:
            return None
        try:
            return datetime.fromisoformat(self.visit_date).date()
        except ValueError:
            return None

    @property
    def formatted_date(self) -> str:
        return self._fmt_date(self.visit_date)

    @staticmethod
    def _fmt_date(dt_str: Optional[str]) -> str:
        if not dt_str:
            return ""
        try:
            return datetime.fromisoformat(dt_str).strftime("%d %b %Y %H:%M")
        except ValueError:
            return dt_str[:16] if len(dt_str) >= 16 else dt_str

    def summary(self) -> str:
        """One-line summary for display in lists."""
        diag = self.diagnosis or self.chief_complaint or "No diagnosis recorded"
        return f"[{self.formatted_date}]  {self.visit_type}  —  {diag}"

    def __str__(self) -> str:
        return (
            f"Visit(id={self.id}, patient_id={self.patient_id}, "
            f"date={self.visit_date}, type={self.visit_type})"
        )