"""Reusable column-mapping engine.

This is deliberately NOT written for one specific spreadsheet layout. Given
any list of column headers from an uploaded file, `suggest_mapping` proposes
a best-effort mapping onto a fixed set of canonical logical fields (per
target entity), using an alias dictionary plus fuzzy string matching so
headers like "Product Code", "Item Code", and "Style Code" all resolve to
the canonical field `sku`. The user reviews/edits the suggestion before
anything is imported.
"""
import difflib
import re

# canonical_field -> list of known aliases (already-normalized lower/no-space forms are
# derived automatically by _normalize, so aliases can be written in natural casing here).
FIELD_ALIASES: dict[str, list[str]] = {
    "date": ["date", "sale date", "transaction date", "invoice date", "bill date"],
    "sku": ["sku", "product code", "item code", "style code", "variant code", "article code"],
    "barcode": ["barcode", "ean", "upc", "ean code"],
    "quantity": ["quantity", "qty", "units", "units sold", "no of units", "pairs"],
    "unit_price": ["selling price", "price", "unit price", "rate", "sale price", "sp"],
    "unit_cost": ["cost", "purchase price", "cost price", "unit cost", "buying price", "cp"],
    "mrp": ["mrp", "list price", "maximum retail price"],
    "discount": ["discount", "disc", "discount amount"],
    "tax": ["tax", "gst", "tax amount"],
    "customer_name": ["customer", "customer name", "buyer", "party", "party name"],
    "supplier_name": ["supplier", "vendor", "supplier name", "vendor name"],
    "warehouse_code": ["warehouse", "location", "store", "warehouse code", "godown"],
    "brand": ["brand", "brand name", "make"],
    "product_name": ["product", "product name", "item name", "description", "model", "item description"],
    "category": ["category", "type", "product type"],
    "size": ["size", "shoe size", "uk size"],
    "color": ["color", "colour", "shade"],
    "gender": ["gender", "segment"],
    "invoice_number": ["invoice", "invoice no", "invoice number", "bill no", "bill number"],
    "po_number": ["po number", "po no", "purchase order", "po"],
    "received_date": ["received date", "receipt date", "grn date"],
    "notes": ["notes", "remarks", "comments"],
}

# Which canonical fields are relevant (and which are required) per import target.
ENTITY_FIELDS: dict[str, dict[str, bool]] = {
    "SALES": {
        "date": True,
        "sku": True,
        "quantity": True,
        "unit_price": True,
        "customer_name": False,
        "warehouse_code": False,
        "discount": False,
        "tax": False,
        "invoice_number": False,
        "notes": False,
    },
    "PURCHASES": {
        "date": True,
        "sku": True,
        "quantity": True,
        "unit_cost": True,
        "supplier_name": False,
        "warehouse_code": False,
        "po_number": False,
        "notes": False,
    },
    "OPENING_STOCK": {
        "sku": True,
        "quantity": True,
        "warehouse_code": False,
        "unit_cost": False,
        "received_date": False,
        "notes": False,
    },
    "PRODUCTS": {
        "brand": True,
        "product_name": True,
        "sku": True,
        "category": False,
        "size": False,
        "color": False,
        "gender": False,
        "barcode": False,
        "unit_cost": False,
        "unit_price": False,
        "mrp": False,
    },
}


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def suggest_mapping(headers: list[str], target_entity: str) -> dict[str, dict]:
    """Returns {canonical_field: {"header": matched header or None,
    "confidence": "EXACT"|"FUZZY"|"NONE", "required": bool}} for every
    canonical field relevant to target_entity."""
    if target_entity not in ENTITY_FIELDS:
        raise ValueError(f"Unknown import target entity: {target_entity}")

    normalized_headers = {h: _normalize(h) for h in headers}
    result: dict[str, dict] = {}

    for field, required in ENTITY_FIELDS[target_entity].items():
        aliases = {_normalize(a) for a in FIELD_ALIASES.get(field, [field])}
        aliases.add(_normalize(field))

        match_header = None
        confidence = "NONE"

        for header, norm in normalized_headers.items():
            if norm in aliases:
                match_header = header
                confidence = "EXACT"
                break

        if match_header is None:
            for header, norm in normalized_headers.items():
                close = difflib.get_close_matches(norm, aliases, n=1, cutoff=0.82)
                if close:
                    match_header = header
                    confidence = "FUZZY"
                    break

        result[field] = {"header": match_header, "confidence": confidence, "required": required}

    return result


#: Order matters only as a tie-break when two entities score identically —
#: SALES/PURCHASES first since they're what a distributor uploads day to day.
_AUTO_DETECT_CANDIDATES = ["SALES", "PURCHASES", "OPENING_STOCK", "PRODUCTS"]


def detect_target_entity(headers: list[str]) -> tuple[str, dict[str, dict]]:
    """Picks the best-fitting import target for a file's headers, so the
    user doesn't have to say up front whether it's a sales or purchases
    sheet. Scores each candidate entity by how completely its *required*
    fields are matched (a file missing a required field for an entity is
    almost certainly not that entity — e.g. a sales file has no unit_cost
    column, a purchases file has no unit_price column) and breaks ties with
    how many optional fields also matched.

    Returns (best_entity, its suggested mapping) so the caller never has to
    call suggest_mapping a second time.
    """
    best_entity = _AUTO_DETECT_CANDIDATES[0]
    best_mapping = suggest_mapping(headers, best_entity)
    best_score = float("-inf")

    for entity in _AUTO_DETECT_CANDIDATES:
        mapping = suggest_mapping(headers, entity)
        required_total = sum(1 for info in mapping.values() if info["required"])
        required_matched = sum(1 for info in mapping.values() if info["required"] and info["header"])
        optional_matched = sum(1 for info in mapping.values() if not info["required"] and info["header"])

        if required_matched < required_total:
            # Heavily penalize missing required fields so a merely-plausible
            # entity never outranks one that's actually fully matched.
            score = required_matched - (required_total - required_matched) * 100
        else:
            score = required_matched * 10 + optional_matched

        if score > best_score:
            best_score = score
            best_entity = entity
            best_mapping = mapping

    return best_entity, best_mapping


def validate_mapping_complete(mapping: dict[str, str | None], target_entity: str) -> list[str]:
    """mapping here is {canonical_field: header_or_None} as confirmed by the
    user. Returns a list of error strings for any missing required field."""
    errors = []
    for field, required in ENTITY_FIELDS.get(target_entity, {}).items():
        if required and not mapping.get(field):
            errors.append(f"Required field '{field}' is not mapped to any column.")
    return errors
