import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_permission
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.auth import User

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("")
def list_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    date_from: datetime.date | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit:view")),
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    logs = query.order_by(AuditLog.created_at.desc()).limit(min(limit, 1000)).all()
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "before": l.before_json,
            "after": l.after_json,
            "reason": l.reason,
            "created_at": l.created_at,
        }
        for l in logs
    ]
