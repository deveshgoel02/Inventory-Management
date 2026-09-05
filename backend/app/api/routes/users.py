from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_permission
from app.auth.security import hash_password
from app.core.database import get_db
from app.models.auth import Role, User
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.services.audit_service import log_action

router = APIRouter(prefix="/api", tags=["users"])


def _would_remove_last_admin(db: Session, target: User, updates: dict) -> bool:
    """True if this update would leave the system with zero active ADMIN
    users - e.g. demoting or deactivating the only admin, including an
    admin doing it to themselves. Checked regardless of who's making the
    change, since the permission gate (user:manage) only proves the actor
    currently has admin-level rights, not that removing the last one is
    intentional."""
    if target.role.name != "ADMIN" or not target.is_active:
        return False

    losing_admin_role = "role_id" in updates and updates["role_id"] != target.role_id
    losing_active_status = updates.get("is_active") is False
    if not losing_admin_role and not losing_active_status:
        return False

    other_active_admins = (
        db.query(User)
        .join(Role, Role.id == User.role_id)
        .filter(Role.name == "ADMIN", User.is_active.is_(True), User.id != target.id)
        .count()
    )
    return other_active_admins == 0


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_permission("user:manage"))):
    users = db.query(User).all()
    out = []
    for u in users:
        row = UserOut.model_validate(u)
        row.permissions = sorted(p.code for p in u.role.permissions)
        out.append(row)
    return out


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), _: User = Depends(require_permission("user:manage"))):
    roles = db.query(Role).all()
    return [{"id": r.id, "name": r.name, "permissions": sorted(p.code for p in r.permissions)} for r in roles]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("user:manage"))):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "A user with this email already exists")
    if not db.get(Role, payload.role_id):
        raise HTTPException(400, "Invalid role_id")

    new_user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role_id=payload.role_id,
    )
    db.add(new_user)
    db.flush()
    log_action(db, user_id=user.id, action="CREATE", entity_type="user", entity_id=new_user.id, after={"email": payload.email, "role_id": payload.role_id})
    db.commit()
    db.refresh(new_user)
    out = UserOut.model_validate(new_user)
    out.permissions = sorted(p.code for p in new_user.role.permissions)
    return out


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, payload: UserUpdate, db: Session = Depends(get_db), user: User = Depends(require_permission("user:manage"))
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")

    updates = payload.model_dump(exclude_unset=True)

    if "email" in updates and updates["email"] != target.email:
        existing = db.query(User).filter(User.email == updates["email"], User.id != target.id).one_or_none()
        if existing:
            raise HTTPException(400, "That email is already in use by another account")

    if "role_id" in updates and updates["role_id"] is not None and not db.get(Role, updates["role_id"]):
        raise HTTPException(400, "Invalid role_id")

    if _would_remove_last_admin(db, target, updates):
        raise HTTPException(400, "This is the last active admin account - assign another admin before changing this.")

    before = {k: getattr(target, k) for k in updates if hasattr(target, k)}

    if "password" in updates:
        password = updates.pop("password")
        if password:
            target.hashed_password = hash_password(password)
    for field, value in updates.items():
        setattr(target, field, value)
    db.flush()
    log_action(db, user_id=user.id, action="UPDATE", entity_type="user", entity_id=target.id, before=before, after=updates)
    db.commit()
    db.refresh(target)
    out = UserOut.model_validate(target)
    out.permissions = sorted(p.code for p in target.role.permissions)
    return out
