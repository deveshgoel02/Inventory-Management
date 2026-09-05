"""The inventory ledger engine.

Every function that mutates stock goes through `record_transaction`. Nothing
else in the codebase is allowed to write to `inventory_transactions`
directly, and no table stores a mutable "current stock" column — current
stock is always a live aggregation over this ledger (see
`get_stock_on_hand`). This is what makes stock numbers auditable: every unit
of stock can be traced back to the specific transaction(s) that put it there.
"""
import datetime
from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.enums import TRANSACTION_DIRECTION, TransactionType
from app.models.inventory import InventoryBatch, InventoryTransaction


class InsufficientStockError(Exception):
    pass


class InvalidTransactionError(Exception):
    pass


@dataclass
class TransactionRequest:
    variant_id: int
    warehouse_id: int
    transaction_type: TransactionType
    quantity: int
    transaction_date: datetime.datetime
    batch_id: int | None = None
    unit_cost: float | None = None
    unit_price: float | None = None
    reference_type: str | None = None
    reference_id: int | None = None
    user_id: int | None = None
    notes: str | None = None
    is_historical_import: bool = False
    allow_negative_stock: bool = False


_OUTFLOW_TYPES = {
    TransactionType.SALE,
    TransactionType.PURCHASE_RETURN,
    TransactionType.STOCK_ADJUSTMENT_OUT,
    TransactionType.TRANSFER_OUT,
}


def record_transaction(db: Session, req: TransactionRequest) -> InventoryTransaction:
    if req.quantity <= 0:
        raise InvalidTransactionError("Transaction quantity must be positive")

    if req.transaction_type in _OUTFLOW_TYPES and not req.allow_negative_stock:
        available = get_stock_on_hand(db, req.variant_id, req.warehouse_id)
        if available - req.quantity < 0:
            raise InsufficientStockError(
                f"Insufficient stock for variant {req.variant_id} at warehouse "
                f"{req.warehouse_id}: available {available}, requested {req.quantity}"
            )

    txn = InventoryTransaction(
        variant_id=req.variant_id,
        warehouse_id=req.warehouse_id,
        batch_id=req.batch_id,
        transaction_type=req.transaction_type.value,
        quantity=req.quantity,
        unit_cost=req.unit_cost,
        unit_price=req.unit_price,
        transaction_date=req.transaction_date,
        reference_type=req.reference_type,
        reference_id=req.reference_id,
        user_id=req.user_id,
        notes=req.notes,
        is_historical_import=req.is_historical_import,
    )
    db.add(txn)
    db.flush()
    return txn


def _signed_quantity_expr():
    """SQL CASE expression giving +quantity for inflow types, -quantity for
    outflow types, matching TRANSACTION_DIRECTION exactly."""
    inflow = [t.value for t, d in TRANSACTION_DIRECTION.items() if d > 0]
    return case(
        (InventoryTransaction.transaction_type.in_(inflow), InventoryTransaction.quantity),
        else_=-InventoryTransaction.quantity,
    )


def get_stock_on_hand(db: Session, variant_id: int, warehouse_id: int | None = None) -> int:
    stmt = select(func.coalesce(func.sum(_signed_quantity_expr()), 0)).where(
        InventoryTransaction.variant_id == variant_id
    )
    if warehouse_id is not None:
        stmt = stmt.where(InventoryTransaction.warehouse_id == warehouse_id)
    return int(db.execute(stmt).scalar_one())


def get_stock_on_hand_bulk(db: Session, warehouse_id: int | None = None) -> dict[int, int]:
    """Returns {variant_id: quantity_on_hand} for all variants with any
    ledger activity. Used by dashboard/aging/listing endpoints to avoid one
    query per SKU."""
    stmt = select(
        InventoryTransaction.variant_id,
        func.coalesce(func.sum(_signed_quantity_expr()), 0),
    ).group_by(InventoryTransaction.variant_id)
    if warehouse_id is not None:
        stmt = stmt.where(InventoryTransaction.warehouse_id == warehouse_id)
    return {row[0]: int(row[1]) for row in db.execute(stmt).all()}


def get_batch_stock_on_hand(db: Session, batch_id: int) -> int:
    stmt = select(func.coalesce(func.sum(_signed_quantity_expr()), 0)).where(
        InventoryTransaction.batch_id == batch_id
    )
    return int(db.execute(stmt).scalar_one())


def get_batches_with_remaining_stock(db: Session, variant_id: int, warehouse_id: int) -> list[tuple[InventoryBatch, int]]:
    """FIFO-ordered batches (oldest received first) with their remaining
    quantity, for aging calculations and FIFO-cost sale allocation."""
    batches = (
        db.query(InventoryBatch)
        .filter(InventoryBatch.variant_id == variant_id, InventoryBatch.warehouse_id == warehouse_id)
        .order_by(InventoryBatch.received_date.asc(), InventoryBatch.id.asc())
        .all()
    )
    result = []
    for batch in batches:
        remaining = get_batch_stock_on_hand(db, batch.id)
        if remaining > 0:
            result.append((batch, remaining))
    return result
