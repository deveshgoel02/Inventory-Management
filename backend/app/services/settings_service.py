from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.models.settings import BusinessSetting

# Registry of recognized keys -> (default value, description). Anything not
# in this dict can still be stored, but Settings UI only surfaces these by
# default. This is the canonical list referenced by docs/business-rules.md.
DEFAULTS: dict[str, tuple[Any, str]] = {
    "currency_code": (app_settings.DEFAULT_CURRENCY, "ISO currency code used across the app"),
    "currency_symbol": (app_settings.DEFAULT_CURRENCY_SYMBOL, "Currency symbol displayed in the UI"),
    "aging_buckets_days": (
        app_settings.DEFAULT_AGING_BUCKETS_DAYS,
        "Upper bound (days) of each inventory aging bucket, ascending",
    ),
    "forecast_horizons_days": (
        app_settings.DEFAULT_FORECAST_HORIZONS_DAYS,
        "Forecast horizons shown on the AI Forecasting page",
    ),
    "default_lead_time_days": (
        app_settings.DEFAULT_LEAD_TIME_DAYS,
        "Fallback supplier lead time when not set on the supplier record",
    ),
    "default_safety_stock_days": (
        app_settings.DEFAULT_SAFETY_STOCK_DAYS,
        "Days of average demand held as safety stock when computing purchase recommendations",
    ),
    "fast_mover_days_of_cover_max": (
        21,
        "A SKU with fewer days of cover than this (given current velocity) is FAST_MOVING",
    ),
    "slow_mover_days_of_cover_min": (
        120,
        "A SKU with more days of cover than this is SLOW_MOVING",
    ),
    "very_slow_mover_days_of_cover_min": (
        240,
        "A SKU with more days of cover than this is VERY_SLOW",
    ),
    "dead_stock_no_sale_days": (
        180,
        "A SKU with in-stock quantity and zero sales in this many days is DEAD_STOCK",
    ),
    "deadline_escalation_days": (
        [7, 3, 0],
        "Days-before-deadline thresholds (descending) that bump escalation_level",
    ),
}


def get_setting(db: Session, key: str) -> Any:
    row = db.query(BusinessSetting).filter(BusinessSetting.key == key).one_or_none()
    if row is not None:
        return row.value
    if key in DEFAULTS:
        return DEFAULTS[key][0]
    raise KeyError(f"Unknown business setting key: {key}")


def get_all_settings(db: Session) -> dict[str, Any]:
    stored = {row.key: row.value for row in db.query(BusinessSetting).all()}
    merged = {k: v[0] for k, v in DEFAULTS.items()}
    merged.update(stored)
    return merged


def set_setting(db: Session, key: str, value: Any, updated_by: int | None = None) -> BusinessSetting:
    row = db.query(BusinessSetting).filter(BusinessSetting.key == key).one_or_none()
    description = DEFAULTS.get(key, (None, None))[1]
    if row is None:
        row = BusinessSetting(key=key, value=value, description=description, updated_by=updated_by)
        db.add(row)
    else:
        row.value = value
        row.updated_by = updated_by
    db.flush()
    return row


def ensure_defaults_seeded(db: Session) -> None:
    existing_keys = {row.key for row in db.query(BusinessSetting.key).all()}
    for key, (value, description) in DEFAULTS.items():
        if key not in existing_keys:
            db.add(BusinessSetting(key=key, value=value, description=description))
    db.flush()
