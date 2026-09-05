import datetime

from pydantic import BaseModel, ConfigDict, Field


class SupplierCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    gstin: str | None = None
    address: str | None = None
    lead_time_days: int | None = None
    notes: str | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str | None
    email: str | None
    lead_time_days: int | None
    is_active: bool


class PurchaseOrderItemCreate(BaseModel):
    variant_id: int
    quantity_ordered: int = Field(gt=0)
    unit_cost: float | None = None


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    order_date: datetime.date
    expected_date: datetime.date | None = None
    notes: str | None = None
    items: list[PurchaseOrderItemCreate]


class PurchaseOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    variant_id: int
    quantity_ordered: int
    quantity_received: int
    unit_cost: float | None


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    po_number: str
    supplier_id: int
    warehouse_id: int
    order_date: datetime.date
    expected_date: datetime.date | None
    status: str
    items: list[PurchaseOrderItemOut] = []
