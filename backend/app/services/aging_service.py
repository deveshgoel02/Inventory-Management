"""Inventory aging.

Aging is computed per batch (not per SKU) because a SKU can have multiple
receiving lots of different ages sitting in the same warehouse. Age is
`as_of_date - batch.received_date`, and remaining quantity in a batch comes
from the ledger (`get_batch_stock_on_hand`), never from a static "quantity
remaining" column, so a partial sale out of an old batch is reflected
immediately everywhere.
"""
import datetime

from sqlalchemy.orm import Session, joinedload

from app.models.inventory import InventoryBatch
from app.services import inventory_service
from app.services.settings_service import get_setting


def _bucket_label(age_days: int, thresholds: list[int]) -> tuple[str, int, int | None]:
    lower = 0
    for upper in thresholds:
        if age_days <= upper:
            return f"{lower}-{upper} days", lower, upper
        lower = upper + 1
    return f"{lower}+ days", lower, None


def compute_aging_detail(db: Session, as_of: datetime.date | None = None) -> list[dict]:
    as_of = as_of or datetime.date.today()
    thresholds = get_setting(db, "aging_buckets_days")

    batches = (
        db.query(InventoryBatch)
        .options(
            joinedload(InventoryBatch.variant),
            joinedload(InventoryBatch.warehouse),
        )
        .all()
    )
    rows = []
    for batch in batches:
        remaining = inventory_service.get_batch_stock_on_hand(db, batch.id)
        if remaining <= 0:
            continue
        age_days = (as_of - batch.received_date).days
        label, lo, hi = _bucket_label(age_days, thresholds)
        unit_cost = float(batch.unit_cost) if batch.unit_cost is not None else None
        value = (unit_cost or 0) * remaining
        variant = batch.variant
        rows.append(
            {
                "variant_id": variant.id,
                "sku": variant.sku,
                "product_name": variant.product.name,
                "brand_name": variant.product.brand.name,
                "warehouse_name": batch.warehouse.name,
                "batch_id": batch.id,
                "batch_code": batch.batch_code,
                "received_date": batch.received_date,
                "age_days": age_days,
                "bucket_label": label,
                "quantity": remaining,
                "unit_cost": unit_cost,
                "inventory_value": round(value, 2),
            }
        )
    return rows


def compute_aging_summary(db: Session, as_of: datetime.date | None = None) -> list[dict]:
    detail = compute_aging_detail(db, as_of)
    thresholds = get_setting(db, "aging_buckets_days")

    labels_ordered = []
    lower = 0
    for upper in thresholds:
        labels_ordered.append((f"{lower}-{upper} days", lower, upper))
        lower = upper + 1
    labels_ordered.append((f"{lower}+ days", lower, None))

    buckets = {label: {"sku_count": set(), "quantity": 0, "inventory_value": 0.0} for label, _, _ in labels_ordered}
    for row in detail:
        b = buckets[row["bucket_label"]]
        b["sku_count"].add(row["variant_id"])
        b["quantity"] += row["quantity"]
        b["inventory_value"] += row["inventory_value"]

    result = []
    for label, lo, hi in labels_ordered:
        b = buckets[label]
        result.append(
            {
                "bucket_label": label,
                "bucket_min_days": lo,
                "bucket_max_days": hi,
                "sku_count": len(b["sku_count"]),
                "quantity": b["quantity"],
                "inventory_value": round(b["inventory_value"], 2),
            }
        )
    return result
