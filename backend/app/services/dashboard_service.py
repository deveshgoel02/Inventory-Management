import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.catalog import ProductVariant
from app.models.deadlines import Alert, StockDeadline
from app.models.inventory import InventoryTransaction
from app.models.sales import Sale
from app.services import inventory_service
from app.services.classification_service import classify_all_variants
from app.services.data_quality_service import run_data_quality_checks


def compute_dashboard_summary(db: Session, as_of: datetime.date | None = None) -> dict:
    as_of = as_of or datetime.date.today()
    thirty_days_ago = as_of - datetime.timedelta(days=30)

    variants = db.query(ProductVariant).filter(ProductVariant.is_active.is_(True)).all()
    stock_by_variant = inventory_service.get_stock_on_hand_bulk(db)

    total_units = 0
    total_cost_value = 0.0
    total_selling_value = 0.0
    for v in variants:
        qty = stock_by_variant.get(v.id, 0)
        if qty <= 0:
            continue
        total_units += qty
        total_cost_value += qty * float(v.purchase_cost or 0)
        total_selling_value += qty * float(v.selling_price or v.mrp or 0)

    classifications = classify_all_variants(db, as_of)
    fast = sum(1 for c in classifications if c["classification"] == "FAST_MOVING")
    slow = sum(1 for c in classifications if c["classification"] == "SLOW_MOVING")
    very_slow = sum(1 for c in classifications if c["classification"] == "VERY_SLOW")
    dead = sum(1 for c in classifications if c["classification"] == "DEAD_STOCK")

    overdue_count = db.query(StockDeadline).filter(StockDeadline.status == "OVERDUE").count()
    upcoming_count = db.query(StockDeadline).filter(StockDeadline.status == "APPROACHING_DEADLINE").count()
    open_alerts = db.query(Alert).filter(Alert.status == "OPEN").count()

    recent_sales_total = (
        db.query(func.coalesce(func.sum(Sale.total), 0))
        .filter(Sale.sale_date >= thirty_days_ago, Sale.sale_date <= as_of)
        .scalar()
        or 0
    )

    recent_purchase_rows = (
        db.query(InventoryTransaction)
        .filter(
            InventoryTransaction.transaction_type == "PURCHASE",
            InventoryTransaction.transaction_date >= datetime.datetime.combine(thirty_days_ago, datetime.time.min),
        )
        .all()
    )
    recent_purchases_total = sum(
        float(t.unit_cost or 0) * t.quantity for t in recent_purchase_rows
    )

    quality = run_data_quality_checks(db)

    return {
        "total_skus": len(variants),
        "total_units_in_stock": total_units,
        "total_inventory_cost_value": round(total_cost_value, 2),
        "total_inventory_selling_value": round(total_selling_value, 2),
        "fast_moving_sku_count": fast,
        "slow_moving_sku_count": slow + very_slow,
        "dead_stock_sku_count": dead,
        "overdue_stock_count": overdue_count,
        "upcoming_deadline_count": upcoming_count,
        "open_alert_count": open_alerts,
        "recent_sales_total_30d": round(float(recent_sales_total), 2),
        "recent_purchases_total_30d": round(recent_purchases_total, 2),
        "data_quality_score": quality["score"],
    }
