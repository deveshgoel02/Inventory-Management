"""Tolerant value parsing for imported spreadsheet cells. Historical
business spreadsheets are never perfectly consistent, so these parsers
accept a reasonable range of real-world formats and raise ValueError with a
human-readable message on anything else — never silently coerce garbage
into a number."""
import datetime
import re

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%Y/%m/%d",
    "%d/%m/%y",
]


def parse_date(value: str) -> datetime.date:
    if value is None:
        raise ValueError("empty date")
    text = str(value).strip()
    if not text:
        raise ValueError("empty date")

    if re.fullmatch(r"\d+(\.0+)?", text):
        # Excel serial date (days since 1899-12-30).
        serial = int(float(text))
        if 1 <= serial <= 60000:
            return datetime.date(1899, 12, 30) + datetime.timedelta(days=serial)

    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date format: '{value}'")


def parse_quantity(value: str) -> int:
    if value is None:
        raise ValueError("empty quantity")
    text = str(value).strip().replace(",", "")
    if not text:
        raise ValueError("empty quantity")
    try:
        qty = int(float(text))
    except ValueError:
        raise ValueError(f"invalid quantity: '{value}'")
    if qty <= 0:
        raise ValueError(f"quantity must be positive: '{value}'")
    return qty


def parse_price(value: str, *, allow_none: bool = True) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        if allow_none:
            return None
        raise ValueError("empty price")
    text = str(value).strip()
    text = re.sub(r"[₹$,\s]", "", text)
    try:
        price = float(text)
    except ValueError:
        raise ValueError(f"malformed price: '{value}'")
    if price < 0:
        raise ValueError(f"price cannot be negative: '{value}'")
    return price


def clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
