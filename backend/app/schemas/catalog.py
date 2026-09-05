from pydantic import BaseModel, ConfigDict


class BrandCreate(BaseModel):
    name: str
    code: str
    notes: str | None = None


class BrandUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    notes: str | None
    is_active: bool
    is_demo: bool


class CategoryCreate(BaseModel):
    name: str
    parent_id: int | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    parent_id: int | None
    is_active: bool


class ProductCreate(BaseModel):
    brand_id: int
    category_id: int | None = None
    name: str
    model_code: str | None = None
    gender: str | None = None
    season: str | None = None
    collection: str | None = None
    description: str | None = None
    attributes: dict | None = None


class ProductUpdate(BaseModel):
    brand_id: int | None = None
    category_id: int | None = None
    name: str | None = None
    model_code: str | None = None
    gender: str | None = None
    season: str | None = None
    collection: str | None = None
    description: str | None = None
    attributes: dict | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    brand_id: int
    category_id: int | None
    name: str
    model_code: str | None
    gender: str | None
    season: str | None
    collection: str | None
    description: str | None
    is_active: bool
    is_demo: bool


class ProductVariantCreate(BaseModel):
    product_id: int
    sku: str
    barcode: str | None = None
    size: str | None = None
    color: str | None = None
    purchase_cost: float | None = None
    mrp: float | None = None
    selling_price: float | None = None
    reorder_point: int | None = None
    minimum_order_quantity: int | None = None


class ProductVariantUpdate(BaseModel):
    barcode: str | None = None
    size: str | None = None
    color: str | None = None
    purchase_cost: float | None = None
    mrp: float | None = None
    selling_price: float | None = None
    reorder_point: int | None = None
    minimum_order_quantity: int | None = None
    is_active: bool | None = None


class ProductVariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    sku: str
    barcode: str | None
    size: str | None
    color: str | None
    purchase_cost: float | None
    mrp: float | None
    selling_price: float | None
    reorder_point: int | None
    minimum_order_quantity: int | None
    is_active: bool
    is_demo: bool


class ProductVariantDetailOut(ProductVariantOut):
    product_name: str
    brand_name: str
    category_name: str | None
    current_stock: int
