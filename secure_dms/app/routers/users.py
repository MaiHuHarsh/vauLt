from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..deps import get_current_user, require_master
from ..audit import create_audit_log

router = APIRouter(prefix="/users", tags=["users"])

ALLOWED_ROLES = ["master", "investigating_officer", "judge", "prosecutor", "forensic", "clerk"]


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.get("", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _: models.User = Depends(require_master)):
    return db.query(models.User).all()


@router.patch("/{user_id}/role", response_model=schemas.UserOut)
def change_role(user_id: str, payload: schemas.RoleUpdate, db: Session = Depends(get_db),
                 master: models.User = Depends(require_master)):
    if payload.role not in ALLOWED_ROLES:
        raise HTTPException(400, f"Invalid role. Allowed: {ALLOWED_ROLES}")
    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    old_role = target.role
    target.role = payload.role
    db.commit()
    create_audit_log(db, master.id, master.username, "role_changed", "user", target.id,
                      details=f"{old_role} -> {payload.role}")
    db.refresh(target)
    return target


@router.patch("/{user_id}/status", response_model=schemas.UserOut)
def change_status(user_id: str, payload: schemas.StatusUpdate, db: Session = Depends(get_db),
                   master: models.User = Depends(require_master)):
    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    target.status = payload.status
    db.commit()
    create_audit_log(db, master.id, master.username, "status_changed", "user", target.id,
                      details=payload.status)
    db.refresh(target)
    return target
