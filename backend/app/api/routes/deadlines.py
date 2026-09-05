import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_permission
from app.core.database import get_db
from app.models.auth import User
from app.models.catalog import Brand, Category, Product, ProductVariant
from app.models.deadlines import Alert, StockDeadline
from app.schemas.deadlines import AlertOut, StockDeadlineCreate, StockDeadlineOut, StockDeadlineUpdate
from app.services.audit_service import log_action
from app.services.deadline_service import refresh_all_deadline_statuses

router = APIRouter(prefix="/api", tags=["deadlines"])


def _scope_label(db: Session, scope_type: str, scope_id: int) -> str | None:
    model = {"SKU": ProductVariant, "PRODUCT": Product, "BRAND": Brand, "CATEGORY": Category}.get(scope_type)
    if model is None:
        return None
    obj = db.get(model, scope_id)
    if obj is None:
        return None
    return getattr(obj, "sku", None) or getattr(obj, "name", None)


@router.get("/deadlines", response_model=list[StockDeadlineOut])
def list_deadlines(status: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_permission("inventory:view"))):
    refresh_all_deadline_statuses(db)
    db.commit()
    query = db.query(StockDeadline)
    if status:
        query = query.filter(StockDeadline.status == status)
    deadlines = query.order_by(StockDeadline.deadline_date.asc()).all()
    today = datetime.date.today()
    out = []
    for d in deadlines:
        row = StockDeadlineOut.model_validate(d)
        row.scope_label = _scope_label(db, d.scope_type, d.scope_id)
        row.days_remaining = (d.deadline_date - today).days
        out.append(row)
    return out


@router.post("/deadlines", response_model=StockDeadlineOut, status_code=201)
def create_deadline(payload: StockDeadlineCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("deadline:manage"))):
    if payload.scope_type not in ("SKU", "PRODUCT", "BRAND", "CATEGORY", "WAREHOUSE", "BATCH"):
        raise HTTPException(400, "Invalid scope_type")
    deadline = StockDeadline(**payload.model_dump(), status="NORMAL")
    db.add(deadline)
    db.flush()
    log_action(db, user_id=user.id, action="CREATE", entity_type="stock_deadline", entity_id=deadline.id, after=payload.model_dump())
    db.commit()
    db.refresh(deadline)
    out = StockDeadlineOut.model_validate(deadline)
    out.scope_label = _scope_label(db, deadline.scope_type, deadline.scope_id)
    out.days_remaining = (deadline.deadline_date - datetime.date.today()).days
    return out


@router.patch("/deadlines/{deadline_id}", response_model=StockDeadlineOut)
def update_deadline(
    deadline_id: int, payload: StockDeadlineUpdate, db: Session = Depends(get_db), user: User = Depends(require_permission("deadline:manage"))
):
    deadline = db.get(StockDeadline, deadline_id)
    if not deadline:
        raise HTTPException(404, "Deadline not found")
    updates = payload.model_dump(exclude_unset=True)
    before = {k: getattr(deadline, k) for k in updates}
    for field, value in updates.items():
        setattr(deadline, field, value)
    db.flush()
    log_action(db, user_id=user.id, action="UPDATE", entity_type="stock_deadline", entity_id=deadline.id, before=before, after=updates)
    db.commit()
    db.refresh(deadline)
    out = StockDeadlineOut.model_validate(deadline)
    out.scope_label = _scope_label(db, deadline.scope_type, deadline.scope_id)
    out.days_remaining = (deadline.deadline_date - datetime.date.today()).days
    return out


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(status: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_permission("inventory:view"))):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    return query.order_by(Alert.created_at.desc()).limit(500).all()


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("alert:manage"))):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "ACKNOWLEDGED"
    db.flush()
    log_action(db, user_id=user.id, action="ACKNOWLEDGE", entity_type="alert", entity_id=alert.id)
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("alert:manage"))):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "RESOLVED"
    alert.resolved_at = datetime.datetime.now(datetime.timezone.utc)
    alert.resolved_by = user.id
    db.flush()
    log_action(db, user_id=user.id, action="RESOLVE", entity_type="alert", entity_id=alert.id)
    db.commit()
    db.refresh(alert)
    return alert
