import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import require_permission
from app.core.database import get_db
from app.models.auth import User
from app.models.purchasing import PurchaseOrder, PurchaseOrderItem, Supplier
from app.schemas.purchasing import PurchaseOrderCreate, PurchaseOrderOut, SupplierCreate, SupplierOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/api", tags=["purchasing"])


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(q: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_permission("purchase:view"))):
    query = db.query(Supplier).filter(Supplier.is_active.is_(True))
    if q:
        query = query.filter(Supplier.name.ilike(f"%{q}%"))
    return query.order_by(Supplier.name).limit(200).all()


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("purchase:manage"))):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.flush()
    log_action(db, user_id=user.id, action="CREATE", entity_type="supplier", entity_id=supplier.id, after=payload.model_dump())
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    status: str | None = None,
    supplier_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("purchase:view")),
):
    query = db.query(PurchaseOrder).options(joinedload(PurchaseOrder.items))
    if status:
        query = query.filter(PurchaseOrder.status == status)
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    return query.order_by(PurchaseOrder.order_date.desc()).limit(500).all()


@router.post("/purchase-orders", response_model=PurchaseOrderOut, status_code=201)
def create_purchase_order(
    payload: PurchaseOrderCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("purchase:manage"))
):
    if not payload.items:
        raise HTTPException(400, "At least one item is required")
    if not db.get(Supplier, payload.supplier_id):
        raise HTTPException(400, "Invalid supplier_id")

    po_number = f"PO-{datetime.date.today():%Y%m%d}-{db.query(PurchaseOrder).count() + 1:04d}"
    po = PurchaseOrder(
        po_number=po_number,
        supplier_id=payload.supplier_id,
        warehouse_id=payload.warehouse_id,
        order_date=payload.order_date,
        expected_date=payload.expected_date,
        status="SENT",
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(po)
    db.flush()
    for item in payload.items:
        db.add(
            PurchaseOrderItem(
                purchase_order_id=po.id,
                variant_id=item.variant_id,
                quantity_ordered=item.quantity_ordered,
                unit_cost=item.unit_cost,
            )
        )
    log_action(db, user_id=user.id, action="CREATE", entity_type="purchase_order", entity_id=po.id, after={"items": len(payload.items)})
    db.commit()
    db.refresh(po)
    return po


@router.post("/purchase-orders/{po_id}/cancel", response_model=PurchaseOrderOut)
def cancel_purchase_order(po_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("purchase:manage"))):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(404, "Purchase order not found")
    if po.status in ("RECEIVED", "CANCELLED"):
        raise HTTPException(400, f"Cannot cancel a purchase order with status {po.status}")
    before_status = po.status
    po.status = "CANCELLED"
    db.flush()
    log_action(db, user_id=user.id, action="CANCEL", entity_type="purchase_order", entity_id=po.id, before={"status": before_status}, after={"status": "CANCELLED"})
    db.commit()
    db.refresh(po)
    return po
