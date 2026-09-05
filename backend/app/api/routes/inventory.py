import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import require_permission
from app.core.database import get_db
from app.models.auth import User
from app.models.catalog import Product, ProductVariant
from app.models.enums import TransactionType
from app.models.inventory import InventoryBatch, InventoryTransaction, StockReceipt, StockReceiptItem
from app.models.warehouse import Warehouse
from app.schemas.inventory import (
    AgingBucketRow,
    AgingDetailRow,
    CurrentStockRow,
    InventoryTransactionOut,
    StockAdjustmentCreate,
    StockReceiptCreate,
    StockReceiptOut,
)
from app.services import aging_service, inventory_service
from app.services.audit_service import log_action
from app.services.inventory_service import InsufficientStockError, InvalidTransactionError, TransactionRequest

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/current-stock", response_model=list[CurrentStockRow])
def current_stock(
    brand_id: int | None = None,
    category_id: int | None = None,
    warehouse_id: int | None = None,
    sku: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory:view")),
):
    query = (
        db.query(ProductVariant)
        .join(Product)
        .options(joinedload(ProductVariant.product).joinedload(Product.brand))
        .filter(ProductVariant.is_active.is_(True))
    )
    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if sku:
        query = query.filter(ProductVariant.sku.ilike(f"%{sku}%"))
    variants = query.limit(2000).all()

    warehouses = db.query(Warehouse).all() if not warehouse_id else [db.get(Warehouse, warehouse_id)]
    warehouses = [w for w in warehouses if w]

    rows: list[CurrentStockRow] = []
    for w in warehouses:
        stock_map = inventory_service.get_stock_on_hand_bulk(db, warehouse_id=w.id)
        for v in variants:
            qty = stock_map.get(v.id, 0)
            if qty == 0:
                continue
            cost = float(v.purchase_cost) if v.purchase_cost else None
            price = float(v.selling_price) if v.selling_price else None
            rows.append(
                CurrentStockRow(
                    variant_id=v.id,
                    sku=v.sku,
                    product_name=v.product.name,
                    brand_name=v.product.brand.name,
                    warehouse_id=w.id,
                    warehouse_name=w.name,
                    quantity_on_hand=qty,
                    purchase_cost=cost,
                    selling_price=price,
                    inventory_cost_value=round(qty * (cost or 0), 2),
                    inventory_selling_value=round(qty * (price or 0), 2),
                )
            )
    return rows


@router.get("/ledger/{variant_id}", response_model=list[InventoryTransactionOut])
def get_ledger(
    variant_id: int,
    warehouse_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory:view")),
):
    query = db.query(InventoryTransaction).filter(InventoryTransaction.variant_id == variant_id)
    if warehouse_id:
        query = query.filter(InventoryTransaction.warehouse_id == warehouse_id)
    return query.order_by(InventoryTransaction.transaction_date.desc(), InventoryTransaction.id.desc()).limit(1000).all()


@router.post("/adjustments", response_model=InventoryTransactionOut, status_code=201)
def create_adjustment(
    payload: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory:adjust")),
):
    direction = payload.direction.upper()
    if direction not in ("IN", "OUT"):
        raise HTTPException(400, "direction must be 'IN' or 'OUT'")
    txn_type = TransactionType.STOCK_ADJUSTMENT_IN if direction == "IN" else TransactionType.STOCK_ADJUSTMENT_OUT

    try:
        txn = inventory_service.record_transaction(
            db,
            TransactionRequest(
                variant_id=payload.variant_id,
                warehouse_id=payload.warehouse_id,
                transaction_type=txn_type,
                quantity=payload.quantity,
                transaction_date=datetime.datetime.now(datetime.timezone.utc),
                reference_type="MANUAL_ADJUSTMENT",
                user_id=user.id,
                notes=payload.notes,
            ),
        )
    except (InsufficientStockError, InvalidTransactionError) as e:
        raise HTTPException(400, str(e))

    log_action(
        db,
        user_id=user.id,
        action="STOCK_ADJUSTMENT",
        entity_type="product_variant",
        entity_id=payload.variant_id,
        after={"direction": direction, "quantity": payload.quantity, "warehouse_id": payload.warehouse_id},
        reason=payload.notes,
    )
    db.commit()
    db.refresh(txn)
    return txn


@router.post("/receipts", response_model=StockReceiptOut, status_code=201)
def create_receipt(
    payload: StockReceiptCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase:manage")),
):
    if not payload.items:
        raise HTTPException(400, "At least one item is required")

    receipt_number = f"GRN-{datetime.date.today():%Y%m%d}-{db.query(StockReceipt).count() + 1:04d}"
    receipt = StockReceipt(
        receipt_number=receipt_number,
        supplier_id=payload.supplier_id,
        purchase_order_id=payload.purchase_order_id,
        warehouse_id=payload.warehouse_id,
        receipt_date=payload.receipt_date,
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(receipt)
    db.flush()

    for item in payload.items:
        variant = db.get(ProductVariant, item.variant_id)
        if not variant:
            raise HTTPException(400, f"Invalid variant_id {item.variant_id}")
        batch = InventoryBatch(
            variant_id=item.variant_id,
            warehouse_id=payload.warehouse_id,
            batch_code=item.batch_code or f"{receipt_number}-{item.variant_id}",
            supplier_id=payload.supplier_id,
            received_date=payload.receipt_date,
            unit_cost=item.unit_cost,
            quantity_received=item.quantity,
        )
        db.add(batch)
        db.flush()
        db.add(StockReceiptItem(receipt_id=receipt.id, variant_id=item.variant_id, batch_id=batch.id, quantity=item.quantity, unit_cost=item.unit_cost))
        inventory_service.record_transaction(
            db,
            TransactionRequest(
                variant_id=item.variant_id,
                warehouse_id=payload.warehouse_id,
                batch_id=batch.id,
                transaction_type=TransactionType.PURCHASE,
                quantity=item.quantity,
                transaction_date=datetime.datetime.combine(payload.receipt_date, datetime.time.min),
                unit_cost=item.unit_cost,
                reference_type="STOCK_RECEIPT",
                reference_id=receipt.id,
                user_id=user.id,
            ),
        )

    log_action(db, user_id=user.id, action="CREATE", entity_type="stock_receipt", entity_id=receipt.id, after={"items": [i.model_dump() for i in payload.items]})
    db.commit()
    db.refresh(receipt)
    return receipt


@router.get("/aging/summary", response_model=list[AgingBucketRow])
def aging_summary(db: Session = Depends(get_db), _: User = Depends(require_permission("inventory:view"))):
    return aging_service.compute_aging_summary(db)


@router.get("/aging/detail", response_model=list[AgingDetailRow])
def aging_detail(db: Session = Depends(get_db), _: User = Depends(require_permission("inventory:view"))):
    return aging_service.compute_aging_detail(db)
