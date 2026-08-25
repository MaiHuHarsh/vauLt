from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..deps import get_current_user
from ..audit import create_audit_log
from ..permissions import has_access

router = APIRouter(prefix="/access", tags=["access"])


@router.post("/grant")
def grant_access(payload: schemas.AccessGrant, db: Session = Depends(get_db),
                  user: models.User = Depends(get_current_user)):
    if not payload.case_id and not payload.document_id:
        raise HTTPException(400, "case_id or document_id is required")

    allowed = user.role == "master" or has_access(
        db, user, case_id=payload.case_id, document_id=payload.document_id, need="write"
    )
    if not allowed:
        raise HTTPException(403, "You cannot grant access to this resource")

    target_user = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(404, "Target user not found")

    ac = models.AccessControl(
        user_id=payload.user_id, case_id=payload.case_id, document_id=payload.document_id,
        permission=payload.permission, granted_by=user.id, expires_at=payload.expires_at,
    )
    db.add(ac)
    db.commit()
    db.refresh(ac)

    create_audit_log(db, user.id, user.username, "access_granted", "access_control", ac.id,
                      details=f"to={target_user.username} perm={payload.permission}")
    return {"status": "granted", "id": ac.id}


@router.post("/revoke/{access_id}")
def revoke_access(access_id: str, db: Session = Depends(get_db),
                   user: models.User = Depends(get_current_user)):
    ac = db.query(models.AccessControl).filter(models.AccessControl.id == access_id).first()
    if not ac:
        raise HTTPException(404, "Access record not found")
    allowed = user.role == "master" or ac.granted_by == user.id
    if not allowed:
        raise HTTPException(403, "You cannot revoke this access grant")

    ac.revoked_at = datetime.utcnow()
    db.commit()
    create_audit_log(db, user.id, user.username, "access_revoked", "access_control", ac.id)
    return {"status": "revoked"}


@router.get("/case/{case_id}")
def list_case_access(case_id: str, db: Session = Depends(get_db),
                      user: models.User = Depends(get_current_user)):
    if not (user.role == "master" or has_access(db, user, case_id=case_id)):
        raise HTTPException(403, "Access denied")
    rows = db.query(models.AccessControl).filter(models.AccessControl.case_id == case_id).all()
    result = []
    for r in rows:
        u = db.query(models.User).filter(models.User.id == r.user_id).first()
        result.append({
            "id": r.id,
            "user": u.username if u else r.user_id,
            "permission": r.permission,
            "granted_at": r.granted_at.isoformat(),
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "revoked_at": r.revoked_at.isoformat() if r.revoked_at else None,
        })
    return result
