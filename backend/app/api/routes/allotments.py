from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import require_permission
from app.core.database import get_db
from app.models.allotments import SalesAllotment
from app.models.auth import User
from app.models.catalog import ProductVariant
from app.models.sales import Sale, SaleItem
from app.models.warehouse import Warehouse
from app.schemas.allotments import (
    AllotmentCreate,
    AllotmentDetailOut,
    AllotmentExecutionSale,
    AllotmentOut,
    AllotmentUpdate,
    SalesmanBrief,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/api", tags=["allotments"])


def _contributing_sales(db: Session, allotment: SalesAllotment) -> list[tuple[SaleItem, Sale]]:
    """A sale counts toward an allotment if it was recorded by the same
    salesman, for the same SKU, on/after the allotment's start date (and
    within its due date / warehouse, when those are set). This is computed
    live rather than tracked via a link table so it can never fall out of
    sync with edits or returns on the underlying sales."""
    query = (
        db.query(SaleItem, Sale)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(
            Sale.created_by == allotment.salesman_id,
            SaleItem.variant_id == allotment.variant_id,
            Sale.sale_date >= allotment.allotted_date,
            Sale.is_active.is_(True),
        )
    )
    if allotment.warehouse_id:
        query = query.filter(Sale.warehouse_id == allotment.warehouse_id)
    if allotment.due_date:
        query = query.filter(Sale.sale_date <= allotment.due_date)
    return query.order_by(Sale.sale_date).all()


def _serialize(db: Session, allotment: SalesAllotment, *, with_sales: bool = False):
    rows = _contributing_sales(db, allotment)
    executed_qty = sum(item.quantity for item, _ in rows)
    remaining = max(0, allotment.allotted_quantity - executed_qty)
    pct = round(executed_qty / allotment.allotted_quantity * 100, 1) if allotment.allotted_quantity else 0.0

    if not allotment.is_active:
        fulfillment_status = "CANCELLED"
    elif executed_qty >= allotment.allotted_quantity:
        fulfillment_status = "FULFILLED"
    elif executed_qty > 0:
        fulfillment_status = "IN_PROGRESS"
    else:
        fulfillment_status = "PENDING"

    data = dict(
        id=allotment.id,
        salesman_id=allotment.salesman_id,
        salesman_name=allotment.salesman.full_name,
        variant_id=allotment.variant_id,
        sku=allotment.variant.sku,
        product_name=allotment.variant.product.name,
        warehouse_id=allotment.warehouse_id,
        warehouse_name=allotment.warehouse.name if allotment.warehouse else None,
        allotted_quantity=allotment.allotted_quantity,
        allotted_date=allotment.allotted_date,
        due_date=allotment.due_date,
        notes=allotment.notes,
        is_active=allotment.is_active,
        executed_quantity=executed_qty,
        remaining_quantity=remaining,
        completion_pct=pct,
        fulfillment_status=fulfillment_status,
        created_at=allotment.created_at,
    )
    if with_sales:
        data["contributing_sales"] = [
            AllotmentExecutionSale(
                sale_id=sale.id,
                invoice_number=sale.invoice_number,
                sale_date=sale.sale_date,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
            )
            for item, sale in rows
        ]
        return AllotmentDetailOut(**data)
    return AllotmentOut(**data)


@router.get("/allotments/salesmen", response_model=list[SalesmanBrief])
def list_salesmen(db: Session = Depends(get_db), _: User = Depends(require_permission("allotment:manage"))):
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    return [SalesmanBrief(id=u.id, full_name=u.full_name, email=u.email, role_name=u.role.name) for u in users]


@router.get("/allotments", response_model=list[AllotmentOut])
def list_allotments(
    salesman_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("allotment:view")),
):
    query = db.query(SalesAllotment).options(
        joinedload(SalesAllotment.salesman),
        joinedload(SalesAllotment.variant).joinedload(ProductVariant.product),
        joinedload(SalesAllotment.warehouse),
    )
    if salesman_id:
        query = query.filter(SalesAllotment.salesman_id == salesman_id)
    allotments = query.order_by(SalesAllotment.created_at.desc()).limit(500).all()
    return [_serialize(db, a) for a in allotments]


@router.get("/allotments/{allotment_id}", response_model=AllotmentDetailOut)
def get_allotment(
    allotment_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("allotment:view"))
):
    allotment = db.get(SalesAllotment, allotment_id)
    if not allotment:
        raise HTTPException(404, "Allotment not found")
    return _serialize(db, allotment, with_sales=True)


@router.post("/allotments", response_model=AllotmentOut, status_code=201)
def create_allotment(
    payload: AllotmentCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("allotment:manage"))
):
    salesman = db.get(User, payload.salesman_id)
    if not salesman:
        raise HTTPException(400, "Invalid salesman_id")
    if not db.get(ProductVariant, payload.variant_id):
        raise HTTPException(400, "Invalid variant_id")
    if payload.warehouse_id and not db.get(Warehouse, payload.warehouse_id):
        raise HTTPException(400, "Invalid warehouse_id")
    if payload.due_date and payload.due_date < payload.allotted_date:
        raise HTTPException(400, "due_date cannot be before allotted_date")

    allotment = SalesAllotment(
        salesman_id=payload.salesman_id,
        variant_id=payload.variant_id,
        warehouse_id=payload.warehouse_id,
        allotted_quantity=payload.allotted_quantity,
        allotted_date=payload.allotted_date,
        due_date=payload.due_date,
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(allotment)
    db.flush()
    log_action(
        db,
        user_id=user.id,
        action="CREATE",
        entity_type="sales_allotment",
        entity_id=allotment.id,
        after=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(allotment)
    return _serialize(db, allotment)


@router.patch("/allotments/{allotment_id}", response_model=AllotmentOut)
def update_allotment(
    allotment_id: int,
    payload: AllotmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("allotment:manage")),
):
    allotment = db.get(SalesAllotment, allotment_id)
    if not allotment:
        raise HTTPException(404, "Allotment not found")

    updates = payload.model_dump(exclude_unset=True)
    before = {k: getattr(allotment, k) for k in updates}
    for field, value in updates.items():
        setattr(allotment, field, value)
    db.flush()
    log_action(
        db,
        user_id=user.id,
        action="UPDATE",
        entity_type="sales_allotment",
        entity_id=allotment.id,
        before=before,
        after=updates,
    )
    db.commit()
    db.refresh(allotment)
    return _serialize(db, allotment)
