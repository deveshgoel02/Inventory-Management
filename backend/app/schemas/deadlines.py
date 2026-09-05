import datetime

from pydantic import BaseModel, ConfigDict


class StockDeadlineCreate(BaseModel):
    scope_type: str
    scope_id: int
    deadline_date: datetime.date
    warning_days: int = 14
    responsible_user_id: int | None = None
    notes: str | None = None


class StockDeadlineUpdate(BaseModel):
    deadline_date: datetime.date | None = None
    warning_days: int | None = None
    responsible_user_id: int | None = None
    notes: str | None = None
    status: str | None = None


class StockDeadlineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scope_type: str
    scope_id: int
    scope_label: str | None = None
    deadline_date: datetime.date
    warning_days: int
    responsible_user_id: int | None
    notes: str | None
    status: str
    escalation_level: int
    days_remaining: int | None = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alert_type: str
    severity: str
    entity_type: str
    entity_id: int
    title: str
    message: str
    status: str
    created_at: datetime.datetime
    resolved_at: datetime.datetime | None
