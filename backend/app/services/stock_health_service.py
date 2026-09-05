"""Stock health score: a transparent, additive 0-100 score built from four
weighted, individually-explained factors. Never a black box — every score
comes back with the factor breakdown that produced it (see
docs/business-rules.md 'Stock health score').

    Movement classification   (40 pts max)
    Inventory aging           (25 pts max)
    Deadline proximity        (20 pts max)
    Sales trend               (15 pts max)
"""
import datetime

from sqlalchemy.orm import Session

from app.models.catalog import ProductVariant
from app.services import inventory_service
from app.services.classification_service import classify_variant
from app.services.deadline_service import get_deadlines_for_variant
from app.services.forecasting_service import run_forecast_for_variant

_MOVEMENT_POINTS = {
    "FAST_MOVING": 40,
    "HEALTHY": 32,
    "SLOW_MOVING": 20,
    "VERY_SLOW": 8,
    "DEAD_STOCK": 0,
    "NEW_INSUFFICIENT_DATA": 20,
}

_DEADLINE_STATUS_POINTS = {
    "NORMAL": 20,
    "APPROACHING_DEADLINE": 12,
    "DUE": 5,
    "OVERDUE": 0,
}


def _aging_points(db: Session, variant_id: int) -> tuple[int, str]:
    from app.models.inventory import InventoryBatch

    batches = db.query(InventoryBatch).filter(InventoryBatch.variant_id == variant_id).all()
    if not batches:
        return 25, "No batch data recorded; assuming fresh stock."

    today = datetime.date.today()
    weighted_age = 0
    total_qty = 0
    for batch in batches:
        remaining = inventory_service.get_batch_stock_on_hand(db, batch.id)
        if remaining <= 0:
            continue
        age = (today - batch.received_date).days
        weighted_age += age * remaining
        total_qty += remaining

    if total_qty == 0:
        return 25, "No stock currently on hand."

    avg_age = weighted_age / total_qty
    # Linear falloff: full marks at 0 days, zero marks at 2 years (730 days).
    points = max(0, round(25 * (1 - min(avg_age, 730) / 730)))
    return points, f"Stock-weighted average age is {avg_age:.0f} days."


def _deadline_points(db: Session, variant: ProductVariant) -> tuple[int, str]:
    deadlines = get_deadlines_for_variant(db, variant)
    if not deadlines:
        return 20, "No active deadline applies to this SKU."
    most_urgent = deadlines[0]
    points = _DEADLINE_STATUS_POINTS.get(most_urgent.status, 20)
    return points, f"Most urgent applicable deadline is {most_urgent.deadline_date} ({most_urgent.status})."


def _trend_points(db: Session, variant_id: int) -> tuple[int, str]:
    outcome = run_forecast_for_variant(db, variant_id)
    if outcome.historical_avg_daily_sales <= 0:
        return 8, "No sales history to establish a trend."
    ratio = outcome.recent_avg_daily_sales / outcome.historical_avg_daily_sales
    if ratio >= 1.0:
        return 15, f"Recent daily sales ({outcome.recent_avg_daily_sales:.2f}) are at or above the historical average."
    if ratio >= 0.7:
        return 10, f"Recent daily sales are {ratio*100:.0f}% of the historical average — a mild slowdown."
    if ratio >= 0.4:
        return 5, f"Recent daily sales are {ratio*100:.0f}% of the historical average — a notable slowdown."
    return 0, f"Recent daily sales are only {ratio*100:.0f}% of the historical average — a sharp slowdown."


def compute_stock_health(db: Session, variant_id: int) -> dict:
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise ValueError(f"No such product variant: {variant_id}")

    classification = classify_variant(db, variant)
    movement_points = _MOVEMENT_POINTS.get(classification["classification"], 20)
    aging_points, aging_note = _aging_points(db, variant_id)
    deadline_points, deadline_note = _deadline_points(db, variant)
    trend_points, trend_note = _trend_points(db, variant_id)

    score = movement_points + aging_points + deadline_points + trend_points

    if score >= 75:
        status = "Healthy"
    elif score >= 50:
        status = "Watch"
    elif score >= 25:
        status = "At Risk"
    else:
        status = "Critical"

    return {
        "variant_id": variant_id,
        "sku": variant.sku,
        "score": score,
        "status": status,
        "factors": [
            {
                "name": "Movement classification",
                "points": movement_points,
                "max_points": 40,
                "detail": f"Classified as {classification['classification']}. {classification['explanation']}",
            },
            {"name": "Inventory aging", "points": aging_points, "max_points": 25, "detail": aging_note},
            {"name": "Deadline proximity", "points": deadline_points, "max_points": 20, "detail": deadline_note},
            {"name": "Sales trend", "points": trend_points, "max_points": 15, "detail": trend_note},
        ],
    }
