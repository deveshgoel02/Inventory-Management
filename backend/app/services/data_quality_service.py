"""Data Quality Center checks.

Each check returns a concrete, linkable list of offending records — never
just a count with no way to find them. The overall score is a simple,
documented penalty formula (see docs/business-rules.md 'Data quality
score'), not a mysterious composite.
"""
from sqlalchemy.orm import Session

from app.models.catalog import Product, ProductVariant
from app.models.inventory import InventoryTransaction
from app.models.sales import SaleItem

_PENALTY_WEIGHTS = {
    "products_missing_category": 0.5,
    "variants_missing_purchase_cost": 0.5,
    "variants_missing_selling_price": 0.5,
    "sale_items_missing_cost": 0.3,
    "duplicate_barcodes": 2.0,
    "unexplained_stock_adjustments": 1.0,
}


def run_data_quality_checks(db: Session) -> dict:
    issues: dict[str, list[dict]] = {}

    products_missing_category = (
        db.query(Product).filter(Product.category_id.is_(None), Product.is_active.is_(True)).all()
    )
    issues["products_missing_category"] = [
        {"entity": "product", "id": p.id, "label": p.name} for p in products_missing_category
    ]

    variants_missing_cost = (
        db.query(ProductVariant)
        .filter(ProductVariant.purchase_cost.is_(None), ProductVariant.is_active.is_(True))
        .all()
    )
    issues["variants_missing_purchase_cost"] = [
        {"entity": "product_variant", "id": v.id, "label": v.sku} for v in variants_missing_cost
    ]

    variants_missing_price = (
        db.query(ProductVariant)
        .filter(ProductVariant.selling_price.is_(None), ProductVariant.is_active.is_(True))
        .all()
    )
    issues["variants_missing_selling_price"] = [
        {"entity": "product_variant", "id": v.id, "label": v.sku} for v in variants_missing_price
    ]

    sale_items_missing_cost = db.query(SaleItem).filter(SaleItem.unit_cost.is_(None)).limit(500).all()
    issues["sale_items_missing_cost"] = [
        {"entity": "sale_item", "id": si.id, "label": f"sale_item #{si.id}"} for si in sale_items_missing_cost
    ]

    barcode_rows = (
        db.query(ProductVariant.barcode)
        .filter(ProductVariant.barcode.isnot(None))
        .all()
    )
    seen: dict[str, int] = {}
    for (barcode,) in barcode_rows:
        seen[barcode] = seen.get(barcode, 0) + 1
    dup_barcodes = [b for b, count in seen.items() if count > 1]
    dup_variants = (
        db.query(ProductVariant).filter(ProductVariant.barcode.in_(dup_barcodes)).all() if dup_barcodes else []
    )
    issues["duplicate_barcodes"] = [
        {"entity": "product_variant", "id": v.id, "label": f"{v.sku} (barcode {v.barcode})"} for v in dup_variants
    ]

    unexplained_adjustments = (
        db.query(InventoryTransaction)
        .filter(
            InventoryTransaction.transaction_type.in_(["STOCK_ADJUSTMENT_IN", "STOCK_ADJUSTMENT_OUT"]),
            (InventoryTransaction.notes.is_(None)) | (InventoryTransaction.notes == ""),
        )
        .limit(500)
        .all()
    )
    issues["unexplained_stock_adjustments"] = [
        {"entity": "inventory_transaction", "id": t.id, "label": f"txn #{t.id}"} for t in unexplained_adjustments
    ]

    penalty = sum(len(rows) * _PENALTY_WEIGHTS.get(key, 1.0) for key, rows in issues.items())
    score = max(0.0, min(100.0, 100.0 - penalty))

    return {
        "score": round(score, 1),
        "issue_counts": {k: len(v) for k, v in issues.items()},
        "issues": issues,
    }
