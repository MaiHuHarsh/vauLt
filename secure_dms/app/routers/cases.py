from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..deps import get_current_user
from ..audit import create_audit_log
from ..permissions import has_access

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=schemas.CaseOut)
def create_case(payload: schemas.CaseCreate, db: Session = Depends(get_db),
                 user: models.User = Depends(get_current_user)):
    if db.query(models.Case).filter(models.Case.case_number == payload.case_number).first():
        raise HTTPException(400, "Case number already exists")

    case = models.Case(
        case_number=payload.case_number, title=payload.title, description=payload.description,
        sensitivity_level=payload.sensitivity_level or "normal", created_by=user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # auto-grant the creator write access to their own case
    db.add(models.AccessControl(user_id=user.id, case_id=case.id, permission="write", granted_by=user.id))
    db.commit()

    create_audit_log(db, user.id, user.username, "case_created", "case", case.id)
    return case


@router.get("", response_model=List[schemas.CaseOut])
def list_cases(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if user.role == "master":
        return db.query(models.Case).all()
    accessible_ids = [
        a.case_id for a in db.query(models.AccessControl).filter(
            models.AccessControl.user_id == user.id,
            models.AccessControl.case_id.isnot(None),
            models.AccessControl.revoked_at.is_(None),
        ).all()
    ]
    if not accessible_ids:
        return []
    return db.query(models.Case).filter(models.Case.id.in_(accessible_ids)).all()


@router.get("/{case_id}", response_model=schemas.CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    if not has_access(db, user, case_id=case_id):
        create_audit_log(db, user.id, user.username, "access_denied", "case", case_id)
        raise HTTPException(403, "Access denied")
    return case
