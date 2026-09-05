from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import require_permission
from app.core.config import settings as app_settings
from app.core.database import get_db
from app.models.auth import User
from app.models.importing import DataImportJob
from app.services import import_service
from app.services.import_service import ImportError_

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("/jobs")
async def upload_import_job(
    target_entity: str | None = Form(None, description="Omit or pass 'AUTO' to auto-detect Sales/Purchases/etc. from the file's columns"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("import:run")),
):
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in app_settings.ALLOWED_IMPORT_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {app_settings.ALLOWED_IMPORT_EXTENSIONS}")

    content = await file.read()
    if len(content) > app_settings.MAX_IMPORT_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds the {app_settings.MAX_IMPORT_FILE_SIZE_MB}MB limit")

    was_auto_detected = target_entity in (None, "AUTO")
    try:
        job = import_service.create_import_job(
            db, filename=file.filename, content=content, target_entity=target_entity, user_id=user.id
        )
    except ImportError_ as e:
        raise HTTPException(400, str(e))
    db.commit()

    return {
        "job_id": job.id,
        "filename": job.filename,
        "total_rows": job.total_rows,
        "headers": job.raw_rows_cache["headers"],
        "target_entity": job.target_entity,
        "target_entity_auto_detected": was_auto_detected,
        "suggested_mapping": import_service.get_suggested_mapping(job),
        "status": job.status,
    }


@router.post("/jobs/{job_id}/mapping")
def set_import_mapping(
    job_id: int, mapping: dict[str, str | None], db: Session = Depends(get_db), user: User = Depends(require_permission("import:run"))
):
    job = db.get(DataImportJob, job_id)
    if not job:
        raise HTTPException(404, "Import job not found")
    try:
        import_service.set_mapping(db, job, mapping)
    except ImportError_ as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"job_id": job.id, "status": job.status}


@router.post("/jobs/{job_id}/validate")
def validate_import_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("import:run"))):
    job = db.get(DataImportJob, job_id)
    if not job:
        raise HTTPException(404, "Import job not found")
    try:
        import_service.validate_job(db, job)
    except ImportError_ as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {
        "job_id": job.id,
        "status": job.status,
        "total_rows": job.total_rows,
        "valid_rows": job.valid_rows,
        "invalid_rows": job.invalid_rows,
        "duplicate_rows": job.duplicate_rows,
        "issues": job.error_report,
    }


@router.post("/jobs/{job_id}/commit")
def commit_import_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("import:run"))):
    job = db.get(DataImportJob, job_id)
    if not job:
        raise HTTPException(404, "Import job not found")
    try:
        import_service.commit_job(db, job, user.id)
        db.commit()
    except ImportError_ as e:
        db.rollback()
        raise HTTPException(400, str(e))
    except Exception:
        db.rollback()
        raise
    return {
        "job_id": job.id,
        "status": job.status,
        "committed_at": job.committed_at,
        "valid_rows": job.valid_rows,
        "invalid_rows": job.invalid_rows,
    }


@router.get("/jobs")
def list_import_jobs(db: Session = Depends(get_db), user: User = Depends(require_permission("import:run"))):
    jobs = db.query(DataImportJob).order_by(DataImportJob.uploaded_at.desc()).limit(100).all()
    return [
        {
            "id": j.id,
            "filename": j.filename,
            "target_entity": j.target_entity,
            "status": j.status,
            "total_rows": j.total_rows,
            "valid_rows": j.valid_rows,
            "invalid_rows": j.invalid_rows,
            "duplicate_rows": j.duplicate_rows,
            "uploaded_at": j.uploaded_at,
            "committed_at": j.committed_at,
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}")
def get_import_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("import:run"))):
    job = db.get(DataImportJob, job_id)
    if not job:
        raise HTTPException(404, "Import job not found")
    return {
        "id": job.id,
        "filename": job.filename,
        "target_entity": job.target_entity,
        "status": job.status,
        "column_mapping": job.column_mapping,
        "total_rows": job.total_rows,
        "valid_rows": job.valid_rows,
        "invalid_rows": job.invalid_rows,
        "duplicate_rows": job.duplicate_rows,
        "error_report": job.error_report,
    }
