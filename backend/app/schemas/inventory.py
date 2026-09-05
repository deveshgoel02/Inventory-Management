import datetime

from pydantic import BaseModel, ConfigDict, Field


class StockAdjustmentCreate(BaseModel):
    variant_id: int
    warehouse_id: int
    quantity: int = Field(gt=0)
    direction: str = Field(description="IN or OUT")
    notes: str


class InventoryTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    variant_id: int
    warehouse_id: int
    batch_id: int | None
    transaction_type: str
    quantity: int
    unit_cost: float | None
    unit_price: float | None
    transaction_date: datetime.datetime
    reference_type: str | None
    reference_id: int | None
    notes: str | None


class StockReceiptItemCreate(BaseModel):
    variant_id: int
    quantity: int = Field(gt=0)
    unit_cost: float | None = None
    batch_code: str | None = None


class StockReceiptCreate(BaseModel):
    warehouse_id: int
    supplier_id: int | None = None
    purchase_order_id: int | None = None
    receipt_date: datetime.date
    notes: str | None = None
    items: list[StockReceiptItemCreate]


class StockReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    receipt_number: str
    supplier_id: int | None
    warehouse_id: int
    receipt_date: datetime.date
    notes: str | None


class CurrentStockRow(BaseModel):
    variant_id: int
    sku: str
    product_name: str
    brand_name: str
    warehouse_id: int
    warehouse_name: str
    quantity_on_hand: int
    purchase_cost: float | None
    selling_price: float | None
    inventory_cost_value: float
    inventory_selling_value: float


class AgingBucketRow(BaseModel):
    bucket_label: str
    bucket_min_days: int
    bucket_max_days: int | None
    sku_count: int
    quantity: int
    inventory_value: float


class AgingDetailRow(BaseModel):
    variant_id: int
    sku: str
    product_name: str
    brand_name: str
    warehouse_name: str
    batch_id: int
    batch_code: str
    received_date: datetime.date
    age_days: int
    bucket_label: str
    quantity: int
    unit_cost: float | None
    inventory_value: float
