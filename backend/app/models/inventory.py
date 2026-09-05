from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TransactionType
from app.models.mixins import DemoDataMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.catalog import ProductVariant
    from app.models.warehouse import Warehouse


class InventoryBatch(Base, TimestampMixin, DemoDataMixin):
    """A specific receiving lot of a SKU at a warehouse. Batches are what
    make stock aging, FIFO costing, and 'this specific lot must be sold by
    date X' deadlines possible — a bare (SKU, warehouse, quantity) tuple
    cannot represent any of that."""

    __tablename__ = "inventory_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    batch_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    received_date: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))

    variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")

    __table_args__ = (
        CheckConstraint("quantity_received >= 0", name="ck_batch_qty_received_nonneg"),
    )


class InventoryTransaction(Base, TimestampMixin):
    """The append-only inventory ledger. This is the single source of truth
    for stock on hand — current stock is ALWAYS derived by summing signed
    quantities from this table, never read from a manually maintained
    'current stock' column. See docs/business-rules.md."""

    __tablename__ = "inventory_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_batches.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # always stored positive
    unit_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    unit_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    transaction_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, index=True)
    reference_type: Mapped[str | None] = mapped_column(String(50))  # e.g. SALE, STOCK_RECEIPT, ADJUSTMENT
    reference_id: Mapped[int | None] = mapped_column(Integer)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(String(500))
    is_historical_import: Mapped[bool] = mapped_column(default=False)

    variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    batch: Mapped["InventoryBatch | None"] = relationship("InventoryBatch")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_txn_qty_positive"),
        CheckConstraint(
            "transaction_type IN ("
            "'OPENING_BALANCE','PURCHASE','SALE','SALE_RETURN','PURCHASE_RETURN',"
            "'STOCK_ADJUSTMENT_IN','STOCK_ADJUSTMENT_OUT','TRANSFER_IN','TRANSFER_OUT')",
            name="ck_txn_type_valid",
        ),
        Index("ix_txn_variant_warehouse_date", "variant_id", "warehouse_id", "transaction_date"),
    )

    @property
    def signed_quantity(self) -> int:
        from app.models.enums import TRANSACTION_DIRECTION

        direction = TRANSACTION_DIRECTION[TransactionType(self.transaction_type)]
        return direction * self.quantity


class StockReceipt(Base, TimestampMixin, DemoDataMixin):
    """Header document for goods received (from a purchase order or ad-hoc)."""

    __tablename__ = "stock_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    purchase_order_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_orders.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    receipt_date: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    items: Mapped[list["StockReceiptItem"]] = relationship(back_populates="receipt")


class StockReceiptItem(Base, TimestampMixin):
    __tablename__ = "stock_receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("stock_receipts.id"), nullable=False, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_batches.id"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))

    receipt: Mapped["StockReceipt"] = relationship(back_populates="items")

    __table_args__ = (CheckConstraint("quantity > 0", name="ck_receipt_item_qty_positive"),)
