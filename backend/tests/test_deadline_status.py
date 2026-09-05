import datetime

from app.models.deadlines import StockDeadline
from app.services.deadline_service import compute_status_and_escalation


def _deadline(deadline_date, warning_days=14, status="NORMAL", escalation_level=0):
    return StockDeadline(
        scope_type="SKU",
        scope_id=1,
        deadline_date=deadline_date,
        warning_days=warning_days,
        status=status,
        escalation_level=escalation_level,
    )


def test_normal_when_far_from_deadline():
    today = datetime.date(2026, 1, 1)
    d = _deadline(today + datetime.timedelta(days=60))
    status, _ = compute_status_and_escalation(d, today, [7, 3, 0])
    assert status == "NORMAL"


def test_approaching_within_warning_window():
    today = datetime.date(2026, 1, 1)
    d = _deadline(today + datetime.timedelta(days=10), warning_days=14)
    status, _ = compute_status_and_escalation(d, today, [7, 3, 0])
    assert status == "APPROACHING_DEADLINE"


def test_due_on_the_day():
    today = datetime.date(2026, 1, 1)
    d = _deadline(today)
    status, _ = compute_status_and_escalation(d, today, [7, 3, 0])
    assert status == "DUE"


def test_overdue_after_deadline_passes():
    today = datetime.date(2026, 1, 10)
    d = _deadline(datetime.date(2026, 1, 1))
    status, escalation = compute_status_and_escalation(d, today, [7, 3, 0])
    assert status == "OVERDUE"
    assert escalation == 4  # beyond all configured thresholds


def test_resolved_deadlines_stay_resolved():
    today = datetime.date(2026, 1, 10)
    d = _deadline(datetime.date(2026, 1, 1), status="RESOLVED", escalation_level=2)
    status, escalation = compute_status_and_escalation(d, today, [7, 3, 0])
    assert status == "RESOLVED"
    assert escalation == 2
