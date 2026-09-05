from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import DemoDataMixin, SoftDeleteMixin, TimestampMixin


class Warehouse(Base, TimestampMixin, DemoDataMixin, SoftDeleteMixin):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))

    locations: Mapped[list["InventoryLocation"]] = relationship(back_populates="warehouse")


class InventoryLocation(Base, TimestampMixin, SoftDeleteMixin):
    """Optional sub-location (bin/rack/shelf) within a warehouse. Most small
    operations will just use the warehouse-level default location, but this
    keeps the model ready for granular bin tracking later."""

    __tablename__ = "inventory_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False)

    warehouse: Mapped["Warehouse"] = relationship(back_populates="locations")
