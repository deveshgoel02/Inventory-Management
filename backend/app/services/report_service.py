"""CSV/Excel export for the Reports & Import Center pages. Every export is
generated from the exact same service-layer functions the on-screen tables
use, so an exported file can never disagree with what a user saw before
exporting."""
import io

import pandas as pd
from sqlalchemy.orm import Session

from app.models.analytics import AIRecommendation
from app.models.catalog import Brand, ProductVariant
from app.models.sales import Sale
from app.services import aging_service, classification_service, inventory_service
from app.services.data_quality_service import run_data_quality_checks


def _rows_for_current_stock(db: Session) -> list[dict]:
    variants = db.query(ProductVariant).filter(ProductVariant.is_active.is_(True)).all()
    stock_map = inventory_service.get_stock_on_hand_bulk(db)
    out = []
    for v in variants:
        qty = stock_map.get(v.id, 0)
        if qty == 0:
            continue
        out.append(
            {
                "sku": v.sku,
                "product_name": v.product.name,
                "brand_name": v.product.brand.name,
                "quantity_on_hand": qty,
                "purchase_cost": float(v.purchase_cost or 0),
                "selling_price": float(v.selling_price or 0),
                "inventory_cost_value": round(qty * float(v.purchase_cost or 0), 2),
                "inventory_selling_value": round(qty * float(v.selling_price or 0), 2),
            }
        )
    return out


def _rows_for_aging(db: Session) -> list[dict]:
    return aging_service.compute_aging_detail(db)


def _rows_for_dead_stock(db: Session) -> list[dict]:
    classified = classification_service.classify_all_variants(db)
    return [c for c in classified if c["classification"] in ("DEAD_STOCK", "VERY_SLOW")]


def _rows_for_recommendations(db: Session) -> list[dict]:
    recs = db.query(AIRecommendation).order_by(AIRecommendation.generated_at.desc()).limit(1000).all()
    out = []
    for r in recs:
        variant = db.get(ProductVariant, r.variant_id)
        out.append(
            {
                "sku": variant.sku if variant else None,
                "product_name": variant.product.name if variant else None,
                "recommended_order_qty": r.recommended_order_qty,
                "current_stock": r.current_stock,
                "confidence": r.confidence,
                "risk_level": r.risk_level,
                "status": r.status,
                "generated_at": r.generated_at,
            }
        )
    return out


def _rows_for_sales(db: Session) -> list[dict]:
    sales = db.query(Sale).order_by(Sale.sale_date.desc()).limit(5000).all()
    return [
        {
            "invoice_number": s.invoice_number,
            "sale_date": s.sale_date,
            "warehouse_id": s.warehouse_id,
            "customer_id": s.customer_id,
            "subtotal": float(s.subtotal),
            "discount_total": float(s.discount_total),
            "tax_total": float(s.tax_total),
            "total": float(s.total),
        }
        for s in sales
    ]


def _rows_for_brand_performance(db: Session) -> list[dict]:
    from sqlalchemy import func

    from app.models.catalog import Product
    from app.models.sales import SaleItem

    rows = (
        db.query(
            Brand.name,
            func.sum(SaleItem.quantity).label("units_sold"),
            func.sum(SaleItem.quantity * SaleItem.unit_price - SaleItem.discount).label("revenue"),
        )
        .join(Product, Product.brand_id == Brand.id)
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .join(SaleItem, SaleItem.variant_id == ProductVariant.id)
        .group_by(Brand.name)
        .all()
    )
    return [{"brand": name, "units_sold": int(units or 0), "revenue": round(float(rev or 0), 2)} for name, units, rev in rows]


REPORT_BUILDERS = {
    "inventory": _rows_for_current_stock,
    "aging": _rows_for_aging,
    "dead_stock": _rows_for_dead_stock,
    "recommendations": _rows_for_recommendations,
    "sales": _rows_for_sales,
    "brand_performance": _rows_for_brand_performance,
}


def build_report_rows(db: Session, report_name: str) -> list[dict]:
    builder = REPORT_BUILDERS.get(report_name)
    if builder is None:
        raise ValueError(f"Unknown report: {report_name}. Available: {list(REPORT_BUILDERS)}")
    return builder(db)


def to_csv_bytes(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode("utf-8")


def to_xlsx_bytes(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return buffer.getvalue()
