"""Centralized application configuration.

All business rules that were previously "magic numbers" scattered through the
codebase live here (or, better, in the `business_settings` DB table which this
module seeds defaults for). Nothing about aging thresholds, forecast horizons,
lead times, currency, etc. should be hard-coded anywhere else.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Shoe Xpress Inventory Intelligence"
    ENVIRONMENT: str = "development"  # development | production | test

    # Database. Defaults to a local SQLite file for zero-friction local dev.
    # In production, set DATABASE_URL to a PostgreSQL DSN, e.g.
    # postgresql+psycopg2://user:pass@host:5432/shoexpress
    DATABASE_URL: str = "sqlite:///./shoexpress.db"

    # Auth / JWT
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_ENV_FILE"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Business defaults (also mirrored into business_settings table at seed time;
    # the DB table is authoritative once seeded, these are the fallback bootstrap
    # values used only if the settings table is empty).
    DEFAULT_CURRENCY: str = "INR"
    DEFAULT_CURRENCY_SYMBOL: str = "₹"

    # Default aging buckets in days (upper bound inclusive), configurable at runtime.
    DEFAULT_AGING_BUCKETS_DAYS: List[int] = [30, 60, 90, 180, 365, 730]

    # Forecasting defaults
    DEFAULT_FORECAST_HORIZONS_DAYS: List[int] = [30, 60, 90]
    DEFAULT_LEAD_TIME_DAYS: int = 21
    DEFAULT_SAFETY_STOCK_DAYS: int = 14
    MIN_HISTORY_MONTHS_FOR_ADVANCED_MODEL: int = 12
    MIN_HISTORY_POINTS_FOR_ANY_MODEL: int = 6

    # File upload limits
    MAX_IMPORT_FILE_SIZE_MB: int = 25
    ALLOWED_IMPORT_EXTENSIONS: List[str] = [".xlsx", ".xls", ".csv"]

    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
