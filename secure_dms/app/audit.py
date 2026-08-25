"""
Hash-chain audit log: every action writes one row whose hash depends on
the previous row's hash. Editing any past row breaks the chain from that
point forward -- this is the tamper-evidence ("blockchain-style") layer,
implemented as a single append-only table instead of a distributed ledger.
"""
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from . import models

GENESIS_HASH = "0" * 64


def _compute_hash(user_id, username, action, resource_type, resource_id, details, timestamp_iso, prev_hash):
    # Every stored field is part of the hash input -- altering ANY of them,
    # not just action/resource, invalidates the entry and breaks the chain.
    payload = f"{user_id}|{username}|{action}|{resource_type}|{resource_id}|{details}|{timestamp_iso}|{prev_hash}"
    return hashlib.sha256(payload.encode()).hexdigest()


def create_audit_log(db: Session, user_id, username, action, resource_type=None, resource_id=None, details=None):
    last = db.query(models.AuditLog).order_by(desc(models.AuditLog.timestamp)).first()
    prev_hash = last.log_hash if last else GENESIS_HASH
    ts = datetime.utcnow()
    log_hash = _compute_hash(user_id, username, action, resource_type, resource_id, details, ts.isoformat(), prev_hash)
    entry = models.AuditLog(
        user_id=user_id, username=username, action=action,
        resource_type=resource_type, resource_id=resource_id,
        details=details, timestamp=ts, prev_hash=prev_hash, log_hash=log_hash,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def verify_chain(db: Session):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.asc()).all()
    expected_prev = GENESIS_HASH
    for log in logs:
        recomputed = _compute_hash(
            log.user_id, log.username, log.action, log.resource_type, log.resource_id,
            log.details, log.timestamp.isoformat(), log.prev_hash,
        )
        if log.prev_hash != expected_prev:
            return {
                "status": "broken", "broken_at_log_id": log.id,
                "reason": "prev_hash does not match previous entry",
                "timestamp": log.timestamp.isoformat(),
            }
        if recomputed != log.log_hash:
            return {
                "status": "tampered", "broken_at_log_id": log.id,
                "reason": "stored content does not match its recorded hash",
                "timestamp": log.timestamp.isoformat(),
            }
        expected_prev = log.log_hash
    return {"status": "intact", "total_logs": len(logs)}
