import datetime

from pydantic import BaseModel, Field


class AllotmentCreate(BaseModel):
    salesman_id: int
    variant_id: int
    warehouse_id: int | None = None
    allotted_quantity: int = Field(gt=0)
    allotted_date: datetime.date
    due_date: datetime.date | None = None
    notes: str | None = None


class AllotmentUpdate(BaseModel):
    allotted_quantity: int | None = Field(default=None, gt=0)
    due_date: datetime.date | None = None
    notes: str | None = None
    is_active: bool | None = None  # set false to cancel


class SalesmanBrief(BaseModel):
    id: int
    full_name: str
    email: str
    role_name: str


class AllotmentExecutionSale(BaseModel):
    sale_id: int
    invoice_number: str
    sale_date: datetime.date
    quantity: int
    unit_price: float


class AllotmentOut(BaseModel):
    id: int
    salesman_id: int
    salesman_name: str
    variant_id: int
    sku: str
    product_name: str
    warehouse_id: int | None
    warehouse_name: str | None
    allotted_quantity: int
    allotted_date: datetime.date
    due_date: datetime.date | None
    notes: str | None
    is_active: bool
    executed_quantity: int
    remaining_quantity: int
    completion_pct: float
    fulfillment_status: str
    created_at: datetime.datetime


class AllotmentDetailOut(AllotmentOut):
    contributing_sales: list[AllotmentExecutionSale] = []
