import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.deps import require_permission
from app.core.database import get_db
from app.models.auth import User
from app.services import report_service

router = APIRouter(prefix="/api/reports", tags=["reports"])

_MEDIA_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.get("/{report_name}/export")
def export_report(
    report_name: str,
    format: str = "csv",
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("export:run")),
):
    if format not in _MEDIA_TYPES:
        raise HTTPException(400, "format must be 'csv' or 'xlsx'")
    try:
        rows = report_service.build_report_rows(db, report_name)
    except ValueError as e:
        raise HTTPException(404, str(e))

    if not rows:
        rows = [{"note": "No data available for this report"}]

    content = report_service.to_csv_bytes(rows) if format == "csv" else report_service.to_xlsx_bytes(rows)
    filename = f"{report_name}_{datetime.date.today():%Y%m%d}.{format}"
    return Response(
        content=content,
        media_type=_MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
