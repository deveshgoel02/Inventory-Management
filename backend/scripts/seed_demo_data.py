"""Generates clearly-marked demo data (is_demo=True on every master record,
is_historical_import=True on generated transactions) so a developer can see
every dashboard/aging/forecasting/recommendation feature working against a
realistic, multi-month sales history without ever being confused for real
Shoe Xpress business data.

Usage (from backend/ with the venv active):
    python scripts/seed_demo_data.py

Safe to re-run: it checks for existing demo brands and exits early if found,
rather than creating duplicates.
"""
import datetime
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.bootstrap import run_bootstrap
from app.core.database import Base, SessionLocal, engine
from app.models.catalog import Brand, Category, Product, ProductVariant
from app.models.deadlines import StockDeadline
from app.models.enums import TransactionType
from app.models.purchasing import Supplier
from app.models.sales import Customer, Sale, SaleItem
from app.models.warehouse import Warehouse
from app.services import inventory_service
from app.services.deadline_service import refresh_all_deadline_statuses
from app.services.forecasting_service import refresh_sales_history
from app.services.inventory_service import TransactionRequest

RNG_SEED = 42
TODAY = datetime.date.today()


def daily_quantity(day_index: int, span_days: int, profile: str, rng: np.random.Generator) -> int:
    if profile == "fast_growing":
        rate = 1.6 + (day_index / span_days) * 2.2
    elif profile == "steady_healthy":
        rate = 0.9
    elif profile == "declining":
        rate = 2.2 - (day_index / span_days) * 1.9
    elif profile == "slow":
        rate = 0.18
    elif profile == "dead_after_50":
        rate = 1.1 if day_index < 50 else 0.0
    elif profile == "insufficient":
        rate = 0.6
    else:
        rate = 0.5
    rate = max(rate, 0.0)
    return int(rng.poisson(rate)) if rate > 0 else 0


def build_variant_history(rng, span_days: int, profile: str):
    """Precomputes the full daily sales series so the opening stock can be
    sized to never go negative (see docs/business-rules.md 'Demo data
    generation')."""
    series = [daily_quantity(i, span_days, profile, rng) for i in range(span_days)]
    return series


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run_bootstrap(db)

        if db.query(Brand).filter(Brand.is_demo.is_(True)).first():
            print("Demo data already present — skipping. Delete demo rows first if you want to regenerate.")
            return

        rng = np.random.default_rng(RNG_SEED)
        random.seed(RNG_SEED)

        # ---- Warehouses ----
        wh_mumbai = Warehouse(name="Mumbai Central Warehouse", code="MUM-01", address="Andheri East, Mumbai", is_demo=True)
        wh_delhi = Warehouse(name="Delhi Warehouse", code="DEL-01", address="Okhla, New Delhi", is_demo=True)
        db.add_all([wh_mumbai, wh_delhi])
        db.flush()

        # ---- Suppliers ----
        sup_skechers = Supplier(name="Skechers India Distributor", lead_time_days=20, is_demo=True)
        sup_reebok = Supplier(name="Reebok India Distributor", lead_time_days=25, is_demo=True)
        sup_adidas = Supplier(name="adidas India Distributor", lead_time_days=18, is_demo=True)
        sup_wildcraft = Supplier(name="Wildcraft Distributor", lead_time_days=15, is_demo=True)
        db.add_all([sup_skechers, sup_reebok, sup_adidas, sup_wildcraft])
        db.flush()

        # ---- Customers ----
        cust_retail = Customer(name="Walk-in Retail Counter", is_demo=True)
        cust_city = Customer(name="City Sports Store", is_demo=True)
        cust_metro = Customer(name="Metro Footwear Traders", is_demo=True)
        db.add_all([cust_retail, cust_city, cust_metro])
        db.flush()

        # ---- Brands & Categories ----
        brand_skechers = Brand(name="Skechers", code="SKE", is_demo=True)
        brand_reebok = Brand(name="Reebok", code="REE", is_demo=True)
        brand_adidas = Brand(name="adidas", code="ADI", is_demo=True)
        brand_wildcraft = Brand(name="Wildcraft", code="WLD", is_demo=True)
        db.add_all([brand_skechers, brand_reebok, brand_adidas, brand_wildcraft])
        db.flush()

        cat_sports = Category(name="Sports Shoes", is_demo=True)
        cat_casual = Category(name="Casual Shoes", is_demo=True)
        cat_bags = Category(name="Bags & Backpacks", is_demo=True)
        db.add_all([cat_sports, cat_casual, cat_bags])
        db.flush()

        # ---- Products & Variants ----
        # (product, brand, category, supplier, [(size_suffix, velocity_multiplier), ...], profile, span_days, target_ending_stock)
        product_specs = [
            ("Go Walk 6", brand_skechers, cat_casual, sup_skechers, [("8", 0.9), ("9", 1.2), ("10", 0.8)], "fast_growing", 450, 45),
            ("Flex Advantage", brand_skechers, cat_sports, sup_skechers, [("8", 1.0), ("9", 1.0)], "slow", 200, 60),
            ("Classic Runner", brand_reebok, cat_sports, sup_reebok, [("8", 1.0), ("9", 1.1), ("10", 0.7)], "declining", 400, 70),
            ("Energen", brand_reebok, cat_sports, sup_reebok, [("9", 1.0)], "steady_healthy", 150, 25),
            ("Duramo SL", brand_adidas, cat_sports, sup_adidas, [("8", 1.0), ("9", 1.3), ("10", 0.9)], "fast_growing", 380, 40),
            ("Cloudfoam Pure", brand_adidas, cat_casual, sup_adidas, [("9", 1.0)], "steady_healthy", 60, 20),
            ("Trailblazer Backpack", brand_wildcraft, cat_bags, sup_wildcraft, [("OS", 1.0)], "dead_after_50", 260, 35),
            ("Rebel Backpack", brand_wildcraft, cat_bags, sup_wildcraft, [("OS", 1.0)], "insufficient", 3, 16),
        ]

        variant_batch_log = []  # for deadline demo

        for name, brand, category, supplier, sizes, profile, span_days, target_ending in product_specs:
            product = Product(brand_id=brand.id, category_id=category.id, name=name, gender="UNISEX", is_demo=True)
            db.add(product)
            db.flush()

            start_date = TODAY - datetime.timedelta(days=span_days)

            for size_suffix, velocity_mult in sizes:
                sku = f"{brand.code}-{name.replace(' ', '').upper()[:8]}-{size_suffix}"
                purchase_cost = round(rng.uniform(1200, 2600), 2)
                selling_price = round(purchase_cost * rng.uniform(1.35, 1.6), 2)
                mrp = round(selling_price * 1.1, 2)

                variant = ProductVariant(
                    product_id=product.id,
                    sku=sku,
                    barcode=f"890{rng.integers(1000000000, 9999999999)}",
                    size=None if size_suffix == "OS" else size_suffix,
                    color=rng.choice(["Black", "Grey", "Navy", "White"]),
                    purchase_cost=purchase_cost,
                    selling_price=selling_price,
                    mrp=mrp,
                    reorder_point=10,
                    minimum_order_quantity=12,
                    is_demo=True,
                )
                db.add(variant)
                db.flush()

                raw_series = build_variant_history(rng, span_days, profile)
                series = [max(0, int(round(q * velocity_mult))) for q in raw_series]
                total_sold = sum(series)
                opening_qty = total_sold + target_ending

                warehouse = wh_mumbai if rng.random() > 0.3 else wh_delhi

                # Opening batch sized so stock never goes negative through the
                # whole simulated history (see module docstring).
                opening_date = start_date - datetime.timedelta(days=1)
                from app.models.inventory import InventoryBatch

                batch = InventoryBatch(
                    variant_id=variant.id,
                    warehouse_id=warehouse.id,
                    batch_code=f"OPEN-{sku}",
                    supplier_id=supplier.id,
                    received_date=opening_date,
                    unit_cost=purchase_cost,
                    quantity_received=opening_qty,
                    is_demo=True,
                )
                db.add(batch)
                db.flush()
                inventory_service.record_transaction(
                    db,
                    TransactionRequest(
                        variant_id=variant.id,
                        warehouse_id=warehouse.id,
                        batch_id=batch.id,
                        transaction_type=TransactionType.OPENING_BALANCE,
                        quantity=opening_qty,
                        transaction_date=datetime.datetime.combine(opening_date, datetime.time.min),
                        unit_cost=purchase_cost,
                        reference_type="DEMO_SEED",
                        notes="Demo opening balance",
                        is_historical_import=True,
                    ),
                )
                variant_batch_log.append((variant, batch, opening_date))

                invoice_seq = db.query(Sale).count()
                for day_offset, qty in enumerate(series):
                    if qty <= 0:
                        continue
                    sale_date = start_date + datetime.timedelta(days=day_offset)
                    customer = rng.choice([cust_retail, cust_city, cust_metro, None], p=[0.5, 0.25, 0.15, 0.10])
                    invoice_seq += 1
                    sale = Sale(
                        invoice_number=f"DEMO-{sale_date:%Y%m%d}-{invoice_seq:05d}",
                        customer_id=customer.id if customer else None,
                        warehouse_id=warehouse.id,
                        sale_date=sale_date,
                        subtotal=qty * selling_price,
                        discount_total=0,
                        tax_total=0,
                        total=qty * selling_price,
                        is_demo=True,
                        is_historical_import=True,
                    )
                    db.add(sale)
                    db.flush()
                    db.add(
                        SaleItem(
                            sale_id=sale.id,
                            variant_id=variant.id,
                            quantity=qty,
                            unit_price=selling_price,
                            unit_cost=purchase_cost,
                            discount=0,
                            tax=0,
                        )
                    )
                    inventory_service.record_transaction(
                        db,
                        TransactionRequest(
                            variant_id=variant.id,
                            warehouse_id=warehouse.id,
                            batch_id=batch.id,
                            transaction_type=TransactionType.SALE,
                            quantity=qty,
                            transaction_date=datetime.datetime.combine(sale_date, datetime.time.min),
                            unit_price=selling_price,
                            reference_type="SALE",
                            reference_id=sale.id,
                            notes="Demo sale",
                            is_historical_import=True,
                        ),
                    )

                print(f"  seeded {sku}: span={span_days}d profile={profile} total_sold={total_sold} ending_stock~{target_ending}")

        db.flush()

        # ---- Deadline demo: one approaching, one overdue ----
        rebel = db.query(ProductVariant).filter(ProductVariant.sku.like("WLD-REBELBAC%")).first()
        trailblazer = db.query(ProductVariant).filter(ProductVariant.sku.like("WLD-TRAILBLA%")).first()

        if rebel:
            db.add(
                StockDeadline(
                    scope_type="SKU",
                    scope_id=rebel.id,
                    deadline_date=TODAY + datetime.timedelta(days=7),
                    warning_days=14,
                    notes="New Wildcraft launch — must sell through before the next collection lands.",
                    status="NORMAL",
                )
            )
        if trailblazer:
            db.add(
                StockDeadline(
                    scope_type="SKU",
                    scope_id=trailblazer.id,
                    deadline_date=TODAY - datetime.timedelta(days=20),
                    warning_days=14,
                    notes="Trailblazer Backpack — discontinued line, clear remaining stock.",
                    status="NORMAL",
                )
            )
        db.flush()
        refresh_all_deadline_statuses(db)

        refresh_sales_history(db)

        db.commit()
        print("Demo data seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
