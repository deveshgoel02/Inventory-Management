from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.core.database import get_db
from app.models.auth import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, ProfileUpdate, TokenResponse, UserOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    import datetime

    user.last_login_at = datetime.datetime.now(datetime.timezone.utc)
    db.flush()
    db.commit()

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    out = UserOut.model_validate(current_user)
    out.permissions = sorted(p.code for p in current_user.role.permissions)
    return out


@router.patch("/me", response_model=UserOut)
def update_my_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Self-service: any authenticated user can update their own display
    name and login email. Role and active-status changes are deliberately
    NOT here - those go through /api/users (user:manage only), which also
    guards against removing the last active admin."""
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "email" in updates and updates["email"] != current_user.email:
        existing = db.query(User).filter(User.email == updates["email"], User.id != current_user.id).one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That email is already in use by another account")

    before = {k: getattr(current_user, k) for k in updates}
    for field, value in updates.items():
        setattr(current_user, field, value)
    db.flush()
    log_action(db, user_id=current_user.id, action="UPDATE_PROFILE", entity_type="user", entity_id=current_user.id, before=before, after=updates)
    db.commit()
    db.refresh(current_user)

    out = UserOut.model_validate(current_user)
    out.permissions = sorted(p.code for p in current_user.role.permissions)
    return out


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different from the current password")

    current_user.hashed_password = hash_password(payload.new_password)
    db.flush()
    # Never log password values themselves - just the fact that it changed.
    log_action(db, user_id=current_user.id, action="CHANGE_PASSWORD", entity_type="user", entity_id=current_user.id)
    db.commit()
    return {"status": "ok"}
