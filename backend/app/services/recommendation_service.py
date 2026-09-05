"""Purchase recommendation engine.

    Suggested Order Quantity
        = max(0, ForecastDemandDuringLeadTime + SafetyStock
                 - AvailableStock - IncomingStock)

Every term is configurable (lead time, safety-stock days) and every
recommendation stores the exact numbers used to produce it in `reasoning`,
so "why 200 units?" always has a concrete answer — never a bare number. This
is decision support only: nothing here creates a purchase order
automatically (see docs/business-rules.md 'AI safety').
"""
import datetime
import math

from sqlalchemy.orm import Session

from app.models.analytics import AIRecommendation
from app.models.catalog import ProductVariant
from app.models.purchasing import PurchaseOrderItem, PurchaseOrder
from app.services import inventory_service
from app.services.forecasting_service import ForecastOutcome, run_forecast_for_variant
from app.services.settings_service import get_setting


def get_incoming_stock(db: Session, variant_id: int) -> int:
    rows = (
        db.query(PurchaseOrderItem)
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .filter(
            PurchaseOrderItem.variant_id == variant_id,
            PurchaseOrder.status.in_(["SENT", "PARTIALLY_RECEIVED"]),
        )
        .all()
    )
    return sum(max(0, r.quantity_ordered - r.quantity_received) for r in rows)


def _get_lead_time_days(db: Session, variant: ProductVariant) -> int:
    last_po_item = (
        db.query(PurchaseOrderItem)
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .filter(PurchaseOrderItem.variant_id == variant.id)
        .order_by(PurchaseOrder.order_date.desc())
        .first()
    )
    if last_po_item and last_po_item.purchase_order.supplier and last_po_item.purchase_order.supplier.lead_time_days:
        return last_po_item.purchase_order.supplier.lead_time_days
    return get_setting(db, "default_lead_time_days")


def generate_recommendation(db: Session, variant_id: int) -> AIRecommendation:
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise ValueError(f"No such product variant: {variant_id}")

    outcome: ForecastOutcome = run_forecast_for_variant(db, variant_id)

    lead_time_days = _get_lead_time_days(db, variant)
    safety_stock_days = get_setting(db, "default_safety_stock_days")

    forecast_demand_lead_time = round(outcome.daily_rate * lead_time_days, 1)
    safety_stock = round(outcome.daily_rate * safety_stock_days, 1)
    current_stock = inventory_service.get_stock_on_hand(db, variant_id)
    incoming_stock = get_incoming_stock(db, variant_id)

    raw_suggested = forecast_demand_lead_time + safety_stock - current_stock - incoming_stock
    suggested = max(0, math.ceil(raw_suggested))

    moq = variant.minimum_order_quantity
    if moq and suggested > 0 and suggested % moq != 0:
        suggested = math.ceil(suggested / moq) * moq

    days_of_cover = round(current_stock / outcome.daily_rate, 1) if outcome.daily_rate > 0 else None

    reasoning = {
        "daily_sales_rate": round(outcome.daily_rate, 3),
        "model_used": outcome.model_name,
        "lead_time_days": lead_time_days,
        "safety_stock_days": safety_stock_days,
        "forecast_demand_during_lead_time": forecast_demand_lead_time,
        "safety_stock_units": safety_stock,
        "current_stock": current_stock,
        "incoming_stock": incoming_stock,
        "days_of_cover_at_current_stock": days_of_cover,
        "minimum_order_quantity_applied": moq,
        "formula": "max(0, forecast_demand_during_lead_time + safety_stock - current_stock - incoming_stock), "
        "rounded up to the nearest MOQ multiple if one is set",
        "forecast_explanation": outcome.explanation,
    }

    recommendation = AIRecommendation(
        variant_id=variant_id,
        generated_at=datetime.datetime.now(datetime.timezone.utc),
        recommended_order_qty=suggested,
        forecast_demand_lead_time=forecast_demand_lead_time,
        safety_stock=safety_stock,
        current_stock=current_stock,
        incoming_stock=incoming_stock,
        confidence=outcome.confidence,
        risk_level=outcome.risk_level,
        reasoning=reasoning,
        status="PENDING",
    )
    db.add(recommendation)
    db.flush()
    return recommendation


def generate_recommendations_for_all(db: Session) -> list[AIRecommendation]:
    variant_ids = [v.id for v in db.query(ProductVariant.id).filter(ProductVariant.is_active.is_(True)).all()]
    return [generate_recommendation(db, vid) for vid in variant_ids]
