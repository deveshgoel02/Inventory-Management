from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import DemoDataMixin, SoftDeleteMixin, TimestampMixin


class Brand(Base, TimestampMixin, DemoDataMixin, SoftDeleteMixin):
    """Brands are business configuration, not code. New brands (beyond
    Skechers/Reebok/adidas/Wildcraft) are added via the Settings > Brands
    admin page, never by editing source code."""

    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))

    products: Mapped[list["Product"]] = relationship(back_populates="brand")


class Category(Base, TimestampMixin, DemoDataMixin, SoftDeleteMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))

    parent: Mapped["Category | None"] = relationship(remote_side=[id])
    products: Mapped[list["Product"]] = relationship(back_populates="category")

    __table_args__ = (UniqueConstraint("name", "parent_id", name="uq_category_name_parent"),)


class Product(Base, TimestampMixin, DemoDataMixin, SoftDeleteMixin):
    """A product is brand + model, e.g. 'Skechers Go Walk 6'. Sellable units
    live one level down in ProductVariant (the SKU level: size + color)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_code: Mapped[str | None] = mapped_column(String(100), index=True)
    gender: Mapped[str | None] = mapped_column(String(20))  # MEN/WOMEN/UNISEX/KIDS
    season: Mapped[str | None] = mapped_column(String(50))
    collection: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(1000))
    # Free-form extensible attributes so new footwear attributes don't need a migration.
    attributes: Mapped[dict | None] = mapped_column(JSON)

    brand: Mapped["Brand"] = relationship(back_populates="products")
    category: Mapped["Category | None"] = relationship(back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product")


class ProductVariant(Base, TimestampMixin, DemoDataMixin, SoftDeleteMixin):
    """The SKU level: a specific size/color combination of a product. This is
    the unit that inventory, sales, and purchasing all operate on."""

    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    size: Mapped[str | None] = mapped_column(String(20))
    color: Mapped[str | None] = mapped_column(String(50))
    purchase_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    mrp: Mapped[float | None] = mapped_column(Numeric(12, 2))
    selling_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    reorder_point: Mapped[int | None] = mapped_column(Integer)
    minimum_order_quantity: Mapped[int | None] = mapped_column(Integer)
    attributes: Mapped[dict | None] = mapped_column(JSON)

    product: Mapped["Product"] = relationship(back_populates="variants")
