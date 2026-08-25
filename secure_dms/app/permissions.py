from datetime import datetime
from sqlalchemy.orm import Session
from . import models


def has_access(db: Session, user: models.User, case_id=None, document_id=None, need: str = "read") -> bool:
    """Master always passes. Otherwise check ACCESS_CONTROL rows scoped to
    either the case or the document, ignoring expired/revoked grants."""
    if user.role == "master":
        return True

    rows = (
        db.query(models.AccessControl)
        .filter(models.AccessControl.user_id == user.id)
        .filter(models.AccessControl.revoked_at.is_(None))
        .all()
    )
    now = datetime.utcnow()
    for r in rows:
        if r.expires_at and r.expires_at < now:
            continue
        if need == "write" and r.permission != "write":
            continue
        if case_id and r.case_id == case_id:
            return True
        if document_id and r.document_id == document_id:
            return True
    return False
