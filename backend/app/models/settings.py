from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class BusinessSetting(Base, TimestampMixin):
    """Generic key/value business-rule store editable from Settings without
    a code deploy: aging buckets, forecast horizons, lead times, currency,
    fast/slow-mover thresholds, etc. See docs/business-rules.md for the
    full list of recognized keys and their defaults/meaning."""

    __tablename__ = "business_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
