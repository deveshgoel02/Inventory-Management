from app.importing import column_mapping


def test_sku_aliases_all_resolve_to_canonical_field():
    for header in ["SKU", "Product Code", "Item Code", "Style Code"]:
        mapping = column_mapping.suggest_mapping([header, "Date", "Qty", "Rate"], "SALES")
        assert mapping["sku"]["header"] == header
        assert mapping["sku"]["confidence"] == "EXACT"


def test_unmapped_required_field_is_flagged():
    mapping = column_mapping.suggest_mapping(["Some Random Column"], "SALES")
    assert mapping["sku"]["header"] is None
    assert mapping["sku"]["required"] is True


def test_validate_mapping_complete_reports_missing_required_fields():
    errors = column_mapping.validate_mapping_complete({"sku": "Item Code"}, "SALES")
    assert any("date" in e for e in errors)
    assert any("quantity" in e for e in errors)
    assert any("unit_price" in e for e in errors)


def test_validate_mapping_complete_passes_when_all_required_present():
    mapping = {"date": "Date", "sku": "SKU", "quantity": "Qty", "unit_price": "Rate"}
    errors = column_mapping.validate_mapping_complete(mapping, "SALES")
    assert errors == []


def test_fuzzy_match_handles_minor_variation():
    mapping = column_mapping.suggest_mapping(["Product  Code"], "SALES")
    assert mapping["sku"]["header"] == "Product  Code"
