from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import DemoDataMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.catalog import ProductVariant


class Supplier(Base, TimestampMixin, DemoDataMixin, SoftDeleteMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    gstin: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(500))
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(500))


class PurchaseOrder(Base, TimestampMixin, DemoDataMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    po_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    order_date: Mapped[datetime.date] = mapped_column(nullable=False)
    expected_date: Mapped[datetime.date | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    notes: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    items: Mapped[list["PurchaseOrderItem"]] = relationship(back_populates="purchase_order")

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','SENT','PARTIALLY_RECEIVED','RECEIVED','CANCELLED')",
            name="ck_po_status_valid",
        ),
    )


class PurchaseOrderItem(Base, TimestampMixin):
    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")

    __table_args__ = (
        CheckConstraint("quantity_ordered > 0", name="ck_po_item_qty_positive"),
        CheckConstraint("quantity_received >= 0", name="ck_po_item_received_nonneg"),
    )
