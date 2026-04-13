"""
models/patient.py
-----------------
Dataclass representation of a Patient record.

Used to:
  - Pass structured data between layers (DB → UI → Export)
  - Validate field values in one central place
  - Convert raw sqlite3.Row dicts into typed objects

Never import DB queries here — models are pure data containers.
"""

from __future__ import annotations
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Optional


VALID_TYPES   = {"Student", "Staff"}
VALID_GENDERS = {"Male", "Female", "Other"}
VALID_BLOOD   = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
VALID_SCHOOLS = {"STME", "SPTM", "SOL", "SOC", "SBM", "OTHER"}


@dataclass
class Patient:
    # ── Required fields ──────────────────────────────────────────────────────
    sap_id: str
    name: str
    type: str                           # 'Student' | 'Staff'

    # ── Optional fields ───────────────────────────────────────────────────────
    id: Optional[int]         = None
    school: Optional[str]     = None
    mobile: Optional[str]     = None
    age: Optional[int]        = None
    gender: Optional[str]     = None    # 'Male' | 'Female' | 'Other'
    blood_group: Optional[str]= None
    address: Optional[str]    = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # ── Post-init validation ──────────────────────────────────────────────────

    def __post_init__(self):
        self.sap_id = self.sap_id.strip().upper()
        self.name   = self.name.strip()

        if not self.sap_id:
            raise ValueError("sap_id cannot be empty.")
        if not self.name:
            raise ValueError("name cannot be empty.")
        if self.type not in VALID_TYPES:
            raise ValueError(f"type must be one of {VALID_TYPES}. Got: '{self.type}'")
        if self.gender and self.gender not in VALID_GENDERS:
            raise ValueError(f"gender must be one of {VALID_GENDERS}.")
        if self.blood_group and self.blood_group not in VALID_BLOOD:
            raise ValueError(f"blood_group must be one of {VALID_BLOOD}.")
        if self.age is not None and not (1 <= self.age <= 120):
            raise ValueError(f"age must be between 1 and 120. Got: {self.age}")

    # ── Constructors ──────────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, data: dict) -> "Patient":
        """
        Build a Patient from a raw dict (e.g., sqlite3.Row converted to dict).
        Unknown keys are ignored so DB joins with extra columns don't break this.
        """
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @classmethod
    def from_db_row(cls, row) -> "Patient":
        """Accept sqlite3.Row directly."""
        return cls.from_dict(dict(row))

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Convert back to a plain dict (useful for passing to DB queries)."""
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def to_export_row(self) -> dict:
        """
        Flat dict for Excel export — human-friendly column names.
        """
        return {
            "ID":           self.id,
            "SAP ID":       self.sap_id,
            "Name":         self.name,
            "Type":         self.type,
            "School":       self.school or "",
            "Age":          self.age or "",
            "Gender":       self.gender or "",
            "Blood Group":  self.blood_group or "",
            "Mobile":       self.mobile or "",
            "Address":      self.address or "",
            "Registered On":self._fmt_date(self.created_at),
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_date(dt_str: Optional[str]) -> str:
        if not dt_str:
            return ""
        try:
            return datetime.fromisoformat(dt_str).strftime("%d %b %Y")
        except ValueError:
            return dt_str

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.sap_id})"

    @property
    def is_student(self) -> bool:
        return self.type == "Student"

    @property
    def is_staff(self) -> bool:
        return self.type == "Staff"

    def __str__(self) -> str:
        return f"Patient(id={self.id}, sap_id={self.sap_id}, name={self.name})"

    def __repr__(self) -> str:
        return self.__str__()