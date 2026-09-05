from pydantic import BaseModel, ConfigDict


class WarehouseCreate(BaseModel):
    name: str
    code: str
    address: str | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    is_active: bool | None = None


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    address: str | None
    is_active: bool
    is_demo: bool
