from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_permission
from app.core.database import get_db
from app.models.auth import User
from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseOut, WarehouseUpdate
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/warehouses", tags=["warehouses"])


@router.get("", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db), _: User = Depends(require_permission("inventory:view"))):
    return db.query(Warehouse).order_by(Warehouse.name).all()


@router.post("", response_model=WarehouseOut, status_code=201)
def create_warehouse(
    payload: WarehouseCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("settings:manage"))
):
    if db.query(Warehouse).filter(Warehouse.code == payload.code).first():
        raise HTTPException(400, f"Warehouse code '{payload.code}' already exists")
    warehouse = Warehouse(**payload.model_dump())
    db.add(warehouse)
    db.flush()
    log_action(db, user_id=user.id, action="CREATE", entity_type="warehouse", entity_id=warehouse.id, after=payload.model_dump())
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.patch("/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(
    warehouse_id: int,
    payload: WarehouseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings:manage")),
):
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse:
        raise HTTPException(404, "Warehouse not found")
    updates = payload.model_dump(exclude_unset=True)
    before = {k: getattr(warehouse, k) for k in updates}
    for field, value in updates.items():
        setattr(warehouse, field, value)
    db.flush()
    log_action(db, user_id=user.id, action="UPDATE", entity_type="warehouse", entity_id=warehouse.id, before=before, after=updates)
    db.commit()
    db.refresh(warehouse)
    return warehouse
