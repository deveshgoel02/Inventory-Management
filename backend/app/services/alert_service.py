"""Alert de-duplication.

`dedupe_key` is a stable string built from (alert_type, entity_type,
entity_id) — e.g. "DEADLINE_OVERDUE:SKU:123". `raise_alert` upserts: if an
OPEN or ACKNOWLEDGED alert with that key already exists, its message/severity
is refreshed in place instead of creating a second row, so a condition that
stays true for weeks produces exactly one alert, not one per check run.
"""
import datetime

from sqlalchemy.orm import Session

from app.models.deadlines import Alert


def build_dedupe_key(alert_type: str, entity_type: str, entity_id: int) -> str:
    return f"{alert_type}:{entity_type}:{entity_id}"


def raise_alert(
    db: Session,
    *,
    alert_type: str,
    severity: str,
    entity_type: str,
    entity_id: int,
    title: str,
    message: str,
) -> Alert:
    dedupe_key = build_dedupe_key(alert_type, entity_type, entity_id)
    existing = db.query(Alert).filter(Alert.dedupe_key == dedupe_key).one_or_none()
    if existing and existing.status != "RESOLVED":
        existing.severity = severity
        existing.title = title
        existing.message = message
        db.flush()
        return existing
    if existing and existing.status == "RESOLVED":
        # Condition recurred after being resolved: reopen rather than spam a new row.
        existing.status = "OPEN"
        existing.severity = severity
        existing.title = title
        existing.message = message
        existing.resolved_at = None
        existing.resolved_by = None
        db.flush()
        return existing
    alert = Alert(
        alert_type=alert_type,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        message=message,
        status="OPEN",
        dedupe_key=dedupe_key,
    )
    db.add(alert)
    db.flush()
    return alert


def resolve_alert_if_open(db: Session, alert_type: str, entity_type: str, entity_id: int, resolved_by: int | None = None) -> None:
    dedupe_key = build_dedupe_key(alert_type, entity_type, entity_id)
    existing = db.query(Alert).filter(Alert.dedupe_key == dedupe_key).one_or_none()
    if existing and existing.status != "RESOLVED":
        existing.status = "RESOLVED"
        existing.resolved_at = datetime.datetime.now(datetime.timezone.utc)
        existing.resolved_by = resolved_by
        db.flush()
