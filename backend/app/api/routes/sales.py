import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import require_permission
from app.core.database import get_db
from app.models.auth import User
from app.models.catalog import ProductVariant
from app.models.enums import TransactionType
from app.models.sales import Customer, Sale, SaleItem
from app.schemas.sales import CustomerCreate, CustomerOut, SaleCreate, SaleOut, SaleReturnCreate
from app.services import inventory_service
from app.services.audit_service import log_action
from app.services.inventory_service import InsufficientStockError, TransactionRequest

router = APIRouter(prefix="/api", tags=["sales"])


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(q: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_permission("sales:view"))):
    query = db.query(Customer).filter(Customer.is_active.is_(True))
    if q:
        query = query.filter(Customer.name.ilike(f"%{q}%"))
    return query.order_by(Customer.name).limit(200).all()


@router.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("sales:create"))):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.flush()
    log_action(db, user_id=user.id, action="CREATE", entity_type="customer", entity_id=customer.id, after=payload.model_dump())
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/sales", response_model=list[SaleOut])
def list_sales(
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    warehouse_id: int | None = None,
    customer_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("sales:view")),
):
    query = db.query(Sale).options(joinedload(Sale.items)).filter(Sale.is_active.is_(True))
    if date_from:
        query = query.filter(Sale.sale_date >= date_from)
    if date_to:
        query = query.filter(Sale.sale_date <= date_to)
    if warehouse_id:
        query = query.filter(Sale.warehouse_id == warehouse_id)
    if customer_id:
        query = query.filter(Sale.customer_id == customer_id)
    return query.order_by(Sale.sale_date.desc()).limit(500).all()


def _next_invoice_number(db: Session) -> str:
    count = db.query(Sale).count()
    return f"INV-{datetime.date.today():%Y%m%d}-{count + 1:05d}"


@router.post("/sales", response_model=SaleOut, status_code=201)
def create_sale(payload: SaleCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("sales:create"))):
    if not payload.items:
        raise HTTPException(400, "At least one item is required")

    subtotal = 0.0
    discount_total = 0.0
    tax_total = 0.0
    for item in payload.items:
        if not db.get(ProductVariant, item.variant_id):
            raise HTTPException(400, f"Invalid variant_id {item.variant_id}")
        subtotal += item.quantity * item.unit_price
        discount_total += item.discount
        tax_total += item.tax
    total = subtotal - discount_total + tax_total

    sale = Sale(
        invoice_number=_next_invoice_number(db),
        customer_id=payload.customer_id,
        warehouse_id=payload.warehouse_id,
        sale_date=payload.sale_date,
        subtotal=subtotal,
        discount_total=discount_total,
        tax_total=tax_total,
        total=total,
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(sale)
    db.flush()

    try:
        for item in payload.items:
            variant = db.get(ProductVariant, item.variant_id)
            db.add(
                SaleItem(
                    sale_id=sale.id,
                    variant_id=item.variant_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    unit_cost=float(variant.purchase_cost) if variant.purchase_cost else None,
                    discount=item.discount,
                    tax=item.tax,
                )
            )
            inventory_service.record_transaction(
                db,
                TransactionRequest(
                    variant_id=item.variant_id,
                    warehouse_id=payload.warehouse_id,
                    transaction_type=TransactionType.SALE,
                    quantity=item.quantity,
                    transaction_date=datetime.datetime.combine(payload.sale_date, datetime.time.min),
                    unit_price=item.unit_price,
                    reference_type="SALE",
                    reference_id=sale.id,
                    user_id=user.id,
                ),
            )
    except InsufficientStockError as e:
        db.rollback()
        raise HTTPException(400, str(e))

    log_action(db, user_id=user.id, action="CREATE", entity_type="sale", entity_id=sale.id, after={"total": total, "items": len(payload.items)})
    db.commit()
    db.refresh(sale)
    return sale


@router.post("/sales/returns", status_code=201)
def create_sale_return(
    payload: SaleReturnCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("sales:create"))
):
    sale_item = db.get(SaleItem, payload.sale_item_id)
    if not sale_item:
        raise HTTPException(404, "Sale item not found")
    if payload.quantity > sale_item.quantity:
        raise HTTPException(400, "Return quantity cannot exceed originally sold quantity")

    sale = sale_item.sale
    txn = inventory_service.record_transaction(
        db,
        TransactionRequest(
            variant_id=sale_item.variant_id,
            warehouse_id=sale.warehouse_id,
            transaction_type=TransactionType.SALE_RETURN,
            quantity=payload.quantity,
            transaction_date=datetime.datetime.now(datetime.timezone.utc),
            unit_price=float(sale_item.unit_price),
            reference_type="SALE_RETURN",
            reference_id=sale_item.id,
            user_id=user.id,
            notes=payload.notes,
        ),
    )
    log_action(
        db,
        user_id=user.id,
        action="SALE_RETURN",
        entity_type="sale_item",
        entity_id=sale_item.id,
        after={"quantity": payload.quantity},
        reason=payload.notes,
    )
    db.commit()
    return {"transaction_id": txn.id, "status": "ok"}
