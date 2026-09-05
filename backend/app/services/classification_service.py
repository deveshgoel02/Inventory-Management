"""Fast/slow/dead stock classification.

Thresholds are configurable business settings, not hard-coded magic
numbers (see docs/business-rules.md 'Movement classification'). Every
classification is accompanied by the numbers that produced it — the
classification itself is never presented as a bare label.
"""
import datetime

from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.models.analytics import ProductSalesHistory
from app.models.catalog import ProductVariant
from app.services import inventory_service
from app.services.forecasting_service import get_daily_series
from app.services.settings_service import get_setting


def classify_variant(db: Session, variant: ProductVariant, as_of: datetime.date | None = None) -> dict:
    as_of = as_of or datetime.date.today()
    current_stock = inventory_service.get_stock_on_hand(db, variant.id)
    series = get_daily_series(db, variant.id, as_of)
    span_days = len(series)

    last_sale = (
        db.query(ProductSalesHistory)
        .filter(ProductSalesHistory.variant_id == variant.id, ProductSalesHistory.quantity_sold > 0)
        .order_by(ProductSalesHistory.period_date.desc())
        .first()
    )
    days_since_last_sale = (as_of - last_sale.period_date).days if last_sale else None

    dead_stock_days = get_setting(db, "dead_stock_no_sale_days")
    fast_max = get_setting(db, "fast_mover_days_of_cover_max")
    slow_min = get_setting(db, "slow_mover_days_of_cover_min")
    very_slow_min = get_setting(db, "very_slow_mover_days_of_cover_min")

    if span_days < app_settings.MIN_HISTORY_POINTS_FOR_ANY_MODEL:
        return {
            "classification": "NEW_INSUFFICIENT_DATA",
            "sales_velocity_per_day": 0.0,
            "days_of_cover": None,
            "current_stock": current_stock,
            "explanation": (
                f"Only {span_days} day(s) of sales history — not enough to classify movement yet."
            ),
        }

    recent_window = min(30, span_days)
    recent_avg = sum(series[-recent_window:]) / recent_window if recent_window else 0.0

    if current_stock > 0 and days_since_last_sale is not None and days_since_last_sale >= dead_stock_days:
        return {
            "classification": "DEAD_STOCK",
            "sales_velocity_per_day": 0.0,
            "days_of_cover": None,
            "current_stock": current_stock,
            "explanation": (
                f"{current_stock} units in stock but no sale in {days_since_last_sale} days "
                f"(threshold: {dead_stock_days} days)."
            ),
        }
    if current_stock > 0 and last_sale is None:
        return {
            "classification": "DEAD_STOCK",
            "sales_velocity_per_day": 0.0,
            "days_of_cover": None,
            "current_stock": current_stock,
            "explanation": f"{current_stock} units in stock with zero recorded sales in {span_days} days of history.",
        }

    if recent_avg <= 0:
        return {
            "classification": "VERY_SLOW",
            "sales_velocity_per_day": 0.0,
            "days_of_cover": None,
            "current_stock": current_stock,
            "explanation": "No sales in the recent window, but a sale was recorded recently enough to avoid a dead-stock flag.",
        }

    days_of_cover = round(current_stock / recent_avg, 1)

    if days_of_cover <= fast_max:
        classification = "FAST_MOVING"
        explanation = f"Current stock covers only {days_of_cover} days at recent velocity ({recent_avg:.2f} units/day) — below the {fast_max}-day fast-mover threshold."
    elif days_of_cover >= very_slow_min:
        classification = "VERY_SLOW"
        explanation = f"Current stock covers {days_of_cover} days at recent velocity ({recent_avg:.2f} units/day) — above the {very_slow_min}-day very-slow threshold."
    elif days_of_cover >= slow_min:
        classification = "SLOW_MOVING"
        explanation = f"Current stock covers {days_of_cover} days at recent velocity ({recent_avg:.2f} units/day) — above the {slow_min}-day slow-mover threshold."
    else:
        classification = "HEALTHY"
        explanation = f"Current stock covers {days_of_cover} days at recent velocity ({recent_avg:.2f} units/day) — within the healthy range."

    return {
        "classification": classification,
        "sales_velocity_per_day": round(recent_avg, 3),
        "days_of_cover": days_of_cover,
        "current_stock": current_stock,
        "explanation": explanation,
    }


def classify_all_variants(db: Session, as_of: datetime.date | None = None) -> list[dict]:
    variants = db.query(ProductVariant).filter(ProductVariant.is_active.is_(True)).all()
    results = []
    for variant in variants:
        info = classify_variant(db, variant, as_of)
        results.append(
            {
                "variant_id": variant.id,
                "sku": variant.sku,
                "product_name": variant.product.name,
                "brand_name": variant.product.brand.name,
                **info,
            }
        )
    return results
