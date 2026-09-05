import datetime

import pytest

from app.importing.value_parsing import parse_date, parse_price, parse_quantity


def test_parse_date_accepts_multiple_real_world_formats():
    assert parse_date("2026-08-01") == datetime.date(2026, 8, 1)
    assert parse_date("01/08/2026") == datetime.date(2026, 8, 1)
    assert parse_date("01-08-2026") == datetime.date(2026, 8, 1)


def test_parse_date_rejects_invalid_date():
    with pytest.raises(ValueError):
        parse_date("2026-13-40")


def test_parse_quantity_rejects_negative_and_zero():
    with pytest.raises(ValueError):
        parse_quantity("-5")
    with pytest.raises(ValueError):
        parse_quantity("0")


def test_parse_quantity_accepts_comma_separated():
    assert parse_quantity("1,000") == 1000


def test_parse_price_none_value_is_missing_not_malformed():
    # Regression test: an unmapped/blank spreadsheet cell must be treated as
    # "missing" (None when allowed), never stringified into 'None' and
    # rejected as a malformed number.
    assert parse_price(None, allow_none=True) is None
    with pytest.raises(ValueError, match="empty price"):
        parse_price(None, allow_none=False)


def test_parse_price_strips_currency_symbols():
    assert parse_price("₹2,500.50") == 2500.50
    assert parse_price("$10") == 10.0


def test_parse_price_rejects_negative():
    with pytest.raises(ValueError):
        parse_price("-100", allow_none=False)
