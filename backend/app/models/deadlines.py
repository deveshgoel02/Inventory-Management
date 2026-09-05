from __future__ import annotations

import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class StockDeadline(Base, TimestampMixin):
    """A deadline can target any scope (SKU/product/brand/category/warehouse/
    batch) via (scope_type, scope_id) rather than one FK per possible scope,
    since exactly one scope applies per deadline and new scopes shouldn't
    require new columns."""

    __tablename__ = "stock_deadlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    deadline_date: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    warning_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    responsible_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NORMAL", index=True)
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('SKU','PRODUCT','BRAND','CATEGORY','WAREHOUSE','BATCH')",
            name="ck_deadline_scope_type_valid",
        ),
        CheckConstraint(
            "status IN ('NORMAL','APPROACHING_DEADLINE','DUE','OVERDUE','RESOLVED')",
            name="ck_deadline_status_valid",
        ),
    )


class Alert(Base, TimestampMixin):
    """De-duplicated via `dedupe_key` (a stable hash of alert_type+entity)
    so the same condition never spams multiple open alerts — see
    docs/business-rules.md 'Alert de-duplication'."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN", index=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    __table_args__ = (
        CheckConstraint("severity IN ('INFO','WARNING','CRITICAL')", name="ck_alert_severity_valid"),
        CheckConstraint("status IN ('OPEN','ACKNOWLEDGED','RESOLVED')", name="ck_alert_status_valid"),
    )
