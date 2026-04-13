"""
utils/validators.py
--------------------
Pure validation functions — no DB calls, no UI imports.
Return a ValidationResult so callers can decide what to do with errors.

Usage example:
    result = validate_patient_form(sap_id="S123", name="", patient_type="Student")
    if not result.ok:
        print(result.errors)   # ["name cannot be empty"]
        print(result.first)    # "name cannot be empty"

Every public function follows the same contract:
  - Takes raw string/primitive values (exactly what a form gives you)
  - Returns ValidationResult(ok, errors, field_errors)
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
#  VALIDATION RESULT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    field_errors: dict[str, str] = field(default_factory=dict)
    # field_errors maps field name → error message (used to highlight form fields)

    def add(self, message: str, field_name: str = None):
        self.ok = False
        self.errors.append(message)
        if field_name:
            self.field_errors[field_name] = message

    @property
    def first(self) -> str:
        """The first error message, or empty string if none."""
        return self.errors[0] if self.errors else ""

    def __bool__(self) -> bool:
        return self.ok

    def summary(self) -> str:
        return "\n".join(f"• {e}" for e in self.errors)


# ─────────────────────────────────────────────────────────────────────────────
#  REGEX PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

_MOBILE_RE = re.compile(r"^[+\d][\d\s\-]{6,14}$")
_SAP_RE    = re.compile(r"^[A-Za-z0-9_\-]{2,20}$")
_NAME_RE   = re.compile(r"^[A-Za-z\s\.\-\']{2,100}$")
_DATE_FMT  = "%Y-%m-%d"


# ─────────────────────────────────────────────────────────────────────────────
#  PRIMITIVE VALIDATORS
#  Small, focused helpers — each validates ONE thing.
# ─────────────────────────────────────────────────────────────────────────────

def is_required(value: str, field_name: str = "Field") -> Optional[str]:
    """Returns an error string if the value is blank, else None."""
    if not value or not str(value).strip():
        return f"{field_name} is required."
    return None


def is_valid_sap_id(sap_id: str) -> Optional[str]:
    """
    SAP ID rules:
      - 2–20 characters
      - Letters, digits, underscores, hyphens only
    """
    sap_id = sap_id.strip()
    if not sap_id:
        return "SAP ID is required."
    if not _SAP_RE.match(sap_id):
        return "SAP ID must be 2–20 characters (letters, digits, - or _ only)."
    return None


def is_valid_name(name: str) -> Optional[str]:
    name = name.strip()
    if not name:
        return "Name is required."
    if len(name) < 2:
        return "Name must be at least 2 characters."
    if len(name) > 100:
        return "Name must be 100 characters or fewer."
    if not _NAME_RE.match(name):
        return "Name can only contain letters, spaces, dots, hyphens, or apostrophes."
    return None


def is_valid_mobile(mobile: str) -> Optional[str]:
    """
    Mobile validation:
      - Optional field — empty string passes
      - If provided: must match E.164-ish pattern
    """
    mobile = mobile.strip()
    if not mobile:
        return None   # optional
    if not _MOBILE_RE.match(mobile):
        return "Mobile number looks invalid (e.g. +91 9876543210)."
    return None


def is_valid_age(age) -> Optional[str]:
    """Accepts int, float, or string. Returns error string or None."""
    if age is None or str(age).strip() == "":
        return None   # optional
    try:
        age_int = int(age)
    except (ValueError, TypeError):
        return "Age must be a whole number."
    if not (1 <= age_int <= 120):
        return "Age must be between 1 and 120."
    return None


def is_valid_date(date_str: str, field_name: str = "Date",
                  allow_empty: bool = True) -> Optional[str]:
    """
    Validates a 'YYYY-MM-DD' date string.
    allow_empty=True → empty string passes.
    """
    if not date_str or not date_str.strip():
        if allow_empty:
            return None
        return f"{field_name} is required."
    try:
        datetime.strptime(date_str.strip()[:10], _DATE_FMT)
        return None
    except ValueError:
        return f"{field_name} must be a valid date (YYYY-MM-DD)."


def is_future_date(date_str: str, field_name: str = "Date") -> Optional[str]:
    """Returns an error if the date is in the past."""
    err = is_valid_date(date_str, field_name, allow_empty=False)
    if err:
        return err
    d = date.fromisoformat(date_str.strip()[:10])
    if d < date.today():
        return f"{field_name} must be today or a future date."
    return None


def is_not_expired(expiry_str: str) -> Optional[str]:
    """Warns (but does not block) if a medicine expiry date is already past."""
    err = is_valid_date(expiry_str, "Expiry Date", allow_empty=False)
    if err:
        return err
    exp = date.fromisoformat(expiry_str.strip()[:10])
    if exp < date.today():
        return "⚠ This medicine has already expired."
    return None


def is_valid_quantity(qty, field_name: str = "Quantity",
                      min_val: int = 0) -> Optional[str]:
    try:
        val = int(qty)
    except (ValueError, TypeError):
        return f"{field_name} must be a whole number."
    if val < min_val:
        return f"{field_name} must be {min_val} or greater."
    return None


def is_valid_patient_type(ptype: str) -> Optional[str]:
    if ptype not in ("Student", "Staff"):
        return "Type must be 'Student' or 'Staff'."
    return None


def is_valid_visit_type(vtype: str) -> Optional[str]:
    if vtype not in ("Walk-in", "Scheduled", "Emergency"):
        return "Visit type must be Walk-in, Scheduled, or Emergency."
    return None


def is_valid_equipment_category(cat: str) -> Optional[str]:
    if cat not in ("Instrument", "Equipment", "Miscellaneous"):
        return "Category must be Instrument, Equipment, or Miscellaneous."
    return None


def mfg_before_expiry(mfg_str: str, expiry_str: str) -> Optional[str]:
    """Validates that manufacturing date is before expiry date."""
    if not mfg_str or not expiry_str:
        return None
    try:
        mfg    = date.fromisoformat(mfg_str.strip()[:10])
        expiry = date.fromisoformat(expiry_str.strip()[:10])
        if mfg >= expiry:
            return "Manufacturing date must be before the expiry date."
    except ValueError:
        pass
    return None


def dispense_qty_available(quantity: int, current_stock: int) -> Optional[str]:
    """Ensures you can't dispense more than what's in stock."""
    if quantity > current_stock:
        return (
            f"Cannot dispense {quantity} units. "
            f"Only {current_stock} in stock."
        )
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  COMPOSITE FORM VALIDATORS
#  These combine primitives to validate a whole form at once.
# ─────────────────────────────────────────────────────────────────────────────

def validate_patient_form(
    sap_id: str,
    name: str,
    patient_type: str,
    mobile: str = "",
    age = None,
    gender: str = None,
    blood_group: str = None,
) -> ValidationResult:
    result = ValidationResult()

    checks = [
        (is_valid_sap_id(sap_id),          "sap_id"),
        (is_valid_name(name),               "name"),
        (is_valid_patient_type(patient_type),"type"),
        (is_valid_mobile(mobile),           "mobile"),
        (is_valid_age(age),                 "age"),
    ]

    if gender and gender not in ("Male", "Female", "Other"):
        checks.append(("Gender must be Male, Female, or Other.", "gender"))

    valid_blood = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
    if blood_group and blood_group not in valid_blood:
        checks.append((f"Blood group '{blood_group}' is not valid.", "blood_group"))

    for error, field_name in checks:
        if error:
            result.add(error, field_name)

    return result


def validate_visit_form(
    patient_id,
    visit_type: str,
    chief_complaint: str = "",
    diagnosis: str = "",
    visit_date: str = "",
) -> ValidationResult:
    result = ValidationResult()

    if not patient_id:
        result.add("Patient is required.", "patient_id")

    err = is_valid_visit_type(visit_type)
    if err:
        result.add(err, "visit_type")

    err = is_valid_date(visit_date, "Visit Date", allow_empty=True)
    if err:
        result.add(err, "visit_date")

    if not chief_complaint.strip() and not diagnosis.strip():
        result.add(
            "At least a Chief Complaint or Diagnosis must be provided.",
            "diagnosis"
        )

    return result


def validate_medicine_form(
    name: str,
    expiry_date: str,
    stock_received = 0,
    mfg_date: str = "",
    minimum_stock_alert = 10,
) -> ValidationResult:
    result = ValidationResult()

    if not name or not name.strip():
        result.add("Medicine name is required.", "name")
    elif len(name.strip()) > 100:
        result.add("Medicine name must be 100 characters or fewer.", "name")

    err = is_valid_date(expiry_date, "Expiry Date", allow_empty=False)
    if err:
        result.add(err, "expiry_date")

    if mfg_date:
        err = is_valid_date(mfg_date, "Manufacturing Date", allow_empty=True)
        if err:
            result.add(err, "mfg_date")
        else:
            err = mfg_before_expiry(mfg_date, expiry_date)
            if err:
                result.add(err, "mfg_date")

    err = is_valid_quantity(stock_received, "Stock Received", min_val=0)
    if err:
        result.add(err, "stock_received")

    err = is_valid_quantity(minimum_stock_alert, "Low Stock Alert", min_val=0)
    if err:
        result.add(err, "minimum_stock_alert")

    return result


def validate_dispense_form(
    quantity,
    current_stock: int,
    medicine_name: str = "Medicine",
) -> ValidationResult:
    result = ValidationResult()

    err = is_valid_quantity(quantity, "Quantity", min_val=1)
    if err:
        result.add(err, "quantity")
        return result

    err = dispense_qty_available(int(quantity), current_stock)
    if err:
        result.add(err, "quantity")

    return result


def validate_equipment_form(
    name: str,
    category: str,
    quantity = 0,
) -> ValidationResult:
    result = ValidationResult()

    if not name or not name.strip():
        result.add("Equipment name is required.", "name")
    elif len(name.strip()) > 100:
        result.add("Name must be 100 characters or fewer.", "name")

    err = is_valid_equipment_category(category)
    if err:
        result.add(err, "category")

    err = is_valid_quantity(quantity, "Quantity", min_val=0)
    if err:
        result.add(err, "quantity")

    return result


# ─────────────────────────────────────────────────────────────────────────────
#  UTILITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def sanitize_text(value: str, max_len: int = None) -> str:
    """Strip whitespace and optionally truncate."""
    if value is None:
        return ""
    cleaned = " ".join(str(value).split())   # collapse internal whitespace too
    if max_len:
        cleaned = cleaned[:max_len]
    return cleaned


def sanitize_sap_id(sap_id: str) -> str:
    """Uppercase and strip a SAP ID."""
    return str(sap_id).strip().upper()


def parse_date_safe(date_str: str) -> Optional[date]:
    """Parse 'YYYY-MM-DD' safely; return None on failure."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(str(date_str).strip()[:10])
    except ValueError:
        return None


def format_date_display(date_str: str) -> str:
    """Convert 'YYYY-MM-DD' to '15 Jan 2025' for display."""
    d = parse_date_safe(date_str)
    return d.strftime("%d %b %Y") if d else ""


def format_datetime_display(dt_str: str) -> str:
    """Convert ISO datetime to '15 Jan 2025 14:30' for display."""
    if not dt_str:
        return ""
    try:
        return datetime.fromisoformat(dt_str).strftime("%d %b %Y %H:%M")
    except ValueError:
        return dt_str[:16]


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"