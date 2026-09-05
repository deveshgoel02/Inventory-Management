"""Idempotent bootstrap: roles, permissions, an initial admin user, and
default business settings. Safe to run on every startup — never creates a
duplicate row on a second run.
"""
import os

from sqlalchemy.orm import Session

from app.auth.permissions import PERMISSIONS, ROLE_PERMISSIONS
from app.auth.security import hash_password
from app.models.auth import Permission, Role, User
from app.services.settings_service import ensure_defaults_seeded


def ensure_roles_and_permissions(db: Session) -> None:
    existing_permissions = {p.code: p for p in db.query(Permission).all()}
    for code, description in PERMISSIONS.items():
        if code not in existing_permissions:
            perm = Permission(code=code, description=description)
            db.add(perm)
            existing_permissions[code] = perm
    db.flush()

    existing_roles = {r.name: r for r in db.query(Role).all()}
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        role = existing_roles.get(role_name)
        if role is None:
            role = Role(name=role_name)
            db.add(role)
            db.flush()
            existing_roles[role_name] = role
        current_codes = {p.code for p in role.permissions}
        for code in perm_codes:
            if code not in current_codes:
                role.permissions.append(existing_permissions[code])
    db.flush()


def ensure_admin_user(db: Session) -> None:
    if db.query(User).count() > 0:
        return
    admin_role = db.query(Role).filter(Role.name == "ADMIN").one()
    admin_email = os.environ.get("INITIAL_ADMIN_EMAIL", "admin@shoexpress.co.in")
    admin_password = os.environ.get("INITIAL_ADMIN_PASSWORD", "ChangeMe123!")
    admin = User(
        email=admin_email,
        full_name="System Administrator",
        hashed_password=hash_password(admin_password),
        role_id=admin_role.id,
    )
    db.add(admin)
    db.flush()


def run_bootstrap(db: Session) -> None:
    ensure_roles_and_permissions(db)
    ensure_admin_user(db)
    ensure_defaults_seeded(db)
    db.commit()
