from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    pass


class ProductSalesHistory(Base, TimestampMixin):
    """Materialized daily sales aggregate per (variant, warehouse). This is
    the feature table forecasting reads from, so a forecast run never has to
    re-scan raw sale_items. Rebuilt/upserted by the analytics refresh job."""

    __tablename__ = "product_sales_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"), index=True)
    period_date: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    quantity_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("variant_id", "warehouse_id", "period_date", name="uq_sales_history_period"),
    )


class ForecastingResult(Base, TimestampMixin):
    __tablename__ = "forecasting_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    forecast_quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    historical_avg_daily_sales: Mapped[float | None] = mapped_column(Numeric(12, 4))
    recent_avg_daily_sales: Mapped[float | None] = mapped_column(Numeric(12, 4))
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    mae: Mapped[float | None] = mapped_column(Numeric(12, 4))
    rmse: Mapped[float | None] = mapped_column(Numeric(12, 4))
    mape: Mapped[float | None] = mapped_column(Numeric(12, 4))
    parameters_json: Mapped[dict | None] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(String(2000), nullable=False)

    recommendations: Mapped[list["AIRecommendation"]] = relationship(back_populates="forecasting_result")


class AIRecommendation(Base, TimestampMixin):
    __tablename__ = "ai_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    forecasting_result_id: Mapped[int | None] = mapped_column(ForeignKey("forecasting_results.id"))
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, index=True)
    recommended_order_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    forecast_demand_lead_time: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    safety_stock: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    incoming_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    reasoning: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)

    forecasting_result: Mapped["ForecastingResult | None"] = relationship(back_populates="recommendations")
