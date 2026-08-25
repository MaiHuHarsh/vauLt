from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models
from ..db import get_db
from ..deps import get_current_user
from ..audit import verify_chain

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def list_logs(resource_id: Optional[str] = None, limit: int = 300, db: Session = Depends(get_db),
              user: models.User = Depends(get_current_user)):
    q = db.query(models.AuditLog)
    if resource_id:
        q = q.filter(models.AuditLog.resource_id == resource_id)
    logs = q.order_by(models.AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": l.id, "user": l.username, "action": l.action,
            "resource_type": l.resource_type, "resource_id": l.resource_id,
            "details": l.details, "timestamp": l.timestamp.isoformat(),
            "prev_hash": l.prev_hash, "log_hash": l.log_hash,
        }
        for l in logs
    ]


@router.get("/verify")
def verify(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return verify_chain(db)
