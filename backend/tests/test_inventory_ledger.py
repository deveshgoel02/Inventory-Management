import datetime

import pytest

from app.models.catalog import Brand, Product, ProductVariant
from app.models.warehouse import Warehouse
from app.models.enums import TransactionType
from app.services import inventory_service
from app.services.inventory_service import InsufficientStockError, InvalidTransactionError, TransactionRequest


def _make_variant(db):
    brand = Brand(name="TestBrand", code="TB")
    db.add(brand)
    db.flush()
    product = Product(brand_id=brand.id, name="Test Shoe")
    db.add(product)
    db.flush()
    variant = ProductVariant(product_id=product.id, sku="TB-TEST-1", purchase_cost=100, selling_price=150)
    db.add(variant)
    warehouse = Warehouse(name="Test Warehouse", code="TW-01")
    db.add(warehouse)
    db.flush()
    return variant, warehouse


def test_opening_balance_and_sale_reduce_stock(db_session):
    variant, warehouse = _make_variant(db_session)
    now = datetime.datetime.now(datetime.timezone.utc)

    inventory_service.record_transaction(
        db_session,
        TransactionRequest(
            variant_id=variant.id,
            warehouse_id=warehouse.id,
            transaction_type=TransactionType.OPENING_BALANCE,
            quantity=100,
            transaction_date=now,
        ),
    )
    assert inventory_service.get_stock_on_hand(db_session, variant.id, warehouse.id) == 100

    inventory_service.record_transaction(
        db_session,
        TransactionRequest(
            variant_id=variant.id,
            warehouse_id=warehouse.id,
            transaction_type=TransactionType.SALE,
            quantity=30,
            transaction_date=now,
        ),
    )
    assert inventory_service.get_stock_on_hand(db_session, variant.id, warehouse.id) == 70


def test_sale_return_increases_stock_back(db_session):
    variant, warehouse = _make_variant(db_session)
    now = datetime.datetime.now(datetime.timezone.utc)
    for txn_type, qty in [
        (TransactionType.OPENING_BALANCE, 50),
        (TransactionType.SALE, 10),
        (TransactionType.SALE_RETURN, 4),
    ]:
        inventory_service.record_transaction(
            db_session,
            TransactionRequest(
                variant_id=variant.id, warehouse_id=warehouse.id, transaction_type=txn_type, quantity=qty, transaction_date=now
            ),
        )
    assert inventory_service.get_stock_on_hand(db_session, variant.id, warehouse.id) == 44


def test_insufficient_stock_blocks_sale(db_session):
    variant, warehouse = _make_variant(db_session)
    now = datetime.datetime.now(datetime.timezone.utc)
    inventory_service.record_transaction(
        db_session,
        TransactionRequest(
            variant_id=variant.id, warehouse_id=warehouse.id, transaction_type=TransactionType.OPENING_BALANCE, quantity=5, transaction_date=now
        ),
    )
    with pytest.raises(InsufficientStockError):
        inventory_service.record_transaction(
            db_session,
            TransactionRequest(
                variant_id=variant.id, warehouse_id=warehouse.id, transaction_type=TransactionType.SALE, quantity=6, transaction_date=now
            ),
        )
    # The rejected sale must not have partially applied.
    assert inventory_service.get_stock_on_hand(db_session, variant.id, warehouse.id) == 5


def test_negative_or_zero_quantity_rejected(db_session):
    variant, warehouse = _make_variant(db_session)
    now = datetime.datetime.now(datetime.timezone.utc)
    with pytest.raises(InvalidTransactionError):
        inventory_service.record_transaction(
            db_session,
            TransactionRequest(
                variant_id=variant.id, warehouse_id=warehouse.id, transaction_type=TransactionType.PURCHASE, quantity=0, transaction_date=now
            ),
        )


def test_stock_is_per_warehouse(db_session):
    variant, warehouse = _make_variant(db_session)
    warehouse2 = Warehouse(name="Second Warehouse", code="TW-02")
    db_session.add(warehouse2)
    db_session.flush()
    now = datetime.datetime.now(datetime.timezone.utc)

    inventory_service.record_transaction(
        db_session,
        TransactionRequest(variant_id=variant.id, warehouse_id=warehouse.id, transaction_type=TransactionType.OPENING_BALANCE, quantity=20, transaction_date=now),
    )
    inventory_service.record_transaction(
        db_session,
        TransactionRequest(variant_id=variant.id, warehouse_id=warehouse2.id, transaction_type=TransactionType.OPENING_BALANCE, quantity=5, transaction_date=now),
    )

    assert inventory_service.get_stock_on_hand(db_session, variant.id, warehouse.id) == 20
    assert inventory_service.get_stock_on_hand(db_session, variant.id, warehouse2.id) == 5
    # Company-wide total (no warehouse filter) sums across warehouses.
    assert inventory_service.get_stock_on_hand(db_session, variant.id) == 25
