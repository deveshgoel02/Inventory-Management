import datetime
import decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def _json_safe(value: Any) -> Any:
    """Audit before/after payloads are often built from `model_dump()` or
    live ORM attributes, which routinely contain date/datetime/Decimal
    values the JSON column can't serialize natively. Recursively coerce
    those to JSON-safe primitives rather than letting the INSERT blow up."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    return value


def log_action(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=_json_safe(before),
        after_json=_json_safe(after),
        reason=reason,
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
    return entry
