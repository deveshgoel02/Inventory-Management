from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import require_permission
from app.core.database import get_db
from app.models.auth import User
from app.services import settings_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: Any


@router.get("")
def get_all_settings(db: Session = Depends(get_db), _: User = Depends(require_permission("inventory:view"))):
    settings_service.ensure_defaults_seeded(db)
    db.commit()
    return settings_service.get_all_settings(db)


@router.put("/{key}")
def update_setting(key: str, payload: SettingUpdate, db: Session = Depends(get_db), user: User = Depends(require_permission("settings:manage"))):
    before = None
    try:
        before = settings_service.get_setting(db, key)
    except KeyError:
        pass
    setting = settings_service.set_setting(db, key, payload.value, updated_by=user.id)
    log_action(db, user_id=user.id, action="UPDATE_SETTING", entity_type="business_setting", entity_id=setting.id, before={"value": before}, after={"value": payload.value})
    db.commit()
    return {"key": setting.key, "value": setting.value}
