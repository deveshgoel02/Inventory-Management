"""Stock deadline status/escalation + alert generation.

Status transitions (NORMAL -> APPROACHING_DEADLINE -> DUE -> OVERDUE) are
purely a function of `deadline_date`, `warning_days`, and today's date —
recomputed on every read/refresh rather than trusted from a stale stored
value, then written back so listings can filter/sort on it cheaply.
"""
import datetime

from sqlalchemy.orm import Session

from app.models.catalog import Product, ProductVariant
from app.models.deadlines import StockDeadline
from app.services import alert_service
from app.services.settings_service import get_setting


def compute_status_and_escalation(deadline: StockDeadline, as_of: datetime.date, escalation_thresholds: list[int]) -> tuple[str, int]:
    if deadline.status == "RESOLVED":
        return "RESOLVED", deadline.escalation_level

    days_remaining = (deadline.deadline_date - as_of).days
    if days_remaining < 0:
        status = "OVERDUE"
    elif days_remaining == 0:
        status = "DUE"
    elif days_remaining <= deadline.warning_days:
        status = "APPROACHING_DEADLINE"
    else:
        status = "NORMAL"

    escalation_level = 0
    for i, threshold in enumerate(sorted(escalation_thresholds, reverse=True)):
        if days_remaining <= threshold:
            escalation_level = i + 1
    if days_remaining < 0:
        escalation_level = len(escalation_thresholds) + 1

    return status, escalation_level


def refresh_all_deadline_statuses(db: Session, as_of: datetime.date | None = None) -> list[StockDeadline]:
    as_of = as_of or datetime.date.today()
    escalation_thresholds = get_setting(db, "deadline_escalation_days")
    deadlines = db.query(StockDeadline).filter(StockDeadline.status != "RESOLVED").all()

    for deadline in deadlines:
        status, escalation = compute_status_and_escalation(deadline, as_of, escalation_thresholds)
        deadline.status = status
        deadline.escalation_level = escalation

        if status in ("DUE", "OVERDUE"):
            severity = "CRITICAL" if status == "OVERDUE" else "WARNING"
            alert_service.raise_alert(
                db,
                alert_type="STOCK_DEADLINE",
                severity=severity,
                entity_type="STOCK_DEADLINE",
                entity_id=deadline.id,
                title=f"Stock deadline {status.lower()} ({deadline.scope_type})",
                message=(
                    f"{deadline.scope_type} #{deadline.scope_id} deadline was {deadline.deadline_date}. "
                    f"{deadline.notes or ''}"
                ).strip(),
            )
        elif status == "APPROACHING_DEADLINE":
            alert_service.raise_alert(
                db,
                alert_type="STOCK_DEADLINE",
                severity="INFO",
                entity_type="STOCK_DEADLINE",
                entity_id=deadline.id,
                title=f"Stock deadline approaching ({deadline.scope_type})",
                message=f"{deadline.scope_type} #{deadline.scope_id} deadline is {deadline.deadline_date}.",
            )
        else:
            alert_service.resolve_alert_if_open(db, "STOCK_DEADLINE", "STOCK_DEADLINE", deadline.id)

    db.flush()
    return deadlines


def get_deadlines_for_variant(db: Session, variant: ProductVariant) -> list[StockDeadline]:
    """A SKU can be governed by a deadline on itself, its product, its
    brand, or its category. Returns all applicable, active (non-RESOLVED)
    deadlines, most urgent first."""
    product: Product = variant.product
    conditions = [
        (StockDeadline.scope_type == "SKU") & (StockDeadline.scope_id == variant.id),
        (StockDeadline.scope_type == "PRODUCT") & (StockDeadline.scope_id == product.id),
        (StockDeadline.scope_type == "BRAND") & (StockDeadline.scope_id == product.brand_id),
    ]
    if product.category_id:
        conditions.append((StockDeadline.scope_type == "CATEGORY") & (StockDeadline.scope_id == product.category_id))

    from sqlalchemy import or_

    deadlines = (
        db.query(StockDeadline)
        .filter(or_(*conditions), StockDeadline.status != "RESOLVED")
        .order_by(StockDeadline.deadline_date.asc())
        .all()
    )
    return deadlines
