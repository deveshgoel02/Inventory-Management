from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.catalog import ProductVariant
    from app.models.warehouse import Warehouse


class SalesAllotment(Base, TimestampMixin, SoftDeleteMixin):
    """A quantity target an admin/manager assigns to a salesman for a specific
    SKU. Execution is deliberately never stored here - it's computed on read
    as the sum of the salesman's own recorded sales for that variant from
    allotted_date onward, so progress always reflects the live sales ledger
    rather than a copy that could drift out of sync. `is_active=False` means
    the allotment was cancelled (SoftDeleteMixin), not that it was fulfilled."""

    __tablename__ = "sales_allotments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    salesman_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"), index=True)
    allotted_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    allotted_date: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    due_date: Mapped[datetime.date | None] = mapped_column()
    notes: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    salesman: Mapped["User"] = relationship("User", foreign_keys=[salesman_id])
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    warehouse: Mapped["Warehouse | None"] = relationship("Warehouse")

    __table_args__ = (CheckConstraint("allotted_quantity > 0", name="ck_allotment_qty_positive"),)
