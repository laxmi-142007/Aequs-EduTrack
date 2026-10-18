import datetime
from decimal import Decimal, InvalidOperation
import re


def parse_date_flexible(val):
    """
    Parse date from various inputs: datetime, date, or date string
    (YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY) with or without time.
    """
    if not val:
        return None
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val

    s = str(val).strip()
    if not s or s.lower() in ("none", "null", "-", "na", "n/a"):
        return None

    # Strip time part if present (e.g. "2026-10-15 00:00:00" or ISO "2026-10-15T00:00:00")
    s_clean = s.split()[0].split("T")[0]

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s_clean, fmt).date()
        except ValueError:
            pass
    return None


def parse_decimal_clean(val, default=Decimal("0")):
    """
    Parse a decimal or number from string or numeric input, safely stripping
    currency symbols, commas, percent signs, and whitespace.
    """
    if val is None or val == "":
        return default
    if isinstance(val, (int, Decimal)):
        return Decimal(str(val))
    if isinstance(val, float):
        return Decimal(str(val))

    s = (
        str(val)
        .strip()
        .replace(",", "")
        .replace("₹", "")
        .replace("$", "")
        .replace("%", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .strip()
    )
    if not s or s in ("-", "none", "null", "na", "n/a"):
        return default
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return default


def clean_str_value(val):
    """
    Clean string value, stripping whitespace and eliminating floating `.0`
    artifacts on integer values imported from Excel.
    """
    if val is None:
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    s = str(val).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        return s[:-2]
    return s


def normalize_header(name, alias_map=None):
    """
    Normalize CSV/Excel header names to snake_case and resolve common aliases.
    """
    if not name:
        return ""
    cleaned = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if alias_map:
        return alias_map.get(cleaned, cleaned)
    return cleaned
