import datetime

from pydantic import BaseModel, ConfigDict, Field


class SaleItemCreate(BaseModel):
    variant_id: int
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount: float = 0
    tax: float = 0


class SaleCreate(BaseModel):
    warehouse_id: int
    customer_id: int | None = None
    party_name: str | None = None  # alternative to customer_id: look up or create a Customer by this name
    sale_date: datetime.date
    notes: str | None = None
    items: list[SaleItemCreate]


class SaleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    variant_id: int
    quantity: int
    unit_price: float
    unit_cost: float | None
    discount: float
    tax: float


class SaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_number: str
    customer_id: int | None
    customer_name: str | None = None
    warehouse_id: int
    sale_date: datetime.date
    subtotal: float
    discount_total: float
    tax_total: float
    total: float
    items: list[SaleItemOut] = []


class SaleReturnCreate(BaseModel):
    sale_item_id: int
    quantity: int = Field(gt=0)
    notes: str | None = None


class CustomerCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    gstin: str | None = None
    address: str | None = None
    notes: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str | None
    email: str | None
    gstin: str | None
    is_active: bool
