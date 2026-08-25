import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, BigInteger
from .db import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    password_hash = Column(Text, nullable=False)
    # master, investigating_officer, judge, prosecutor, forensic, clerk
    role = Column(String, default="clerk", nullable=False)
    status = Column(String, default="active")  # active, suspended
    created_at = Column(DateTime, default=datetime.utcnow)


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, default=gen_uuid)
    case_number = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="open")  # open, closed
    sensitivity_level = Column(String, default="normal")  # normal, sensitive
    legal_hold = Column(Boolean, default=False)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=gen_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)  # nullable: doc can exist pre-FIR
    doc_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    classification = Column(String, default="internal")  # internal, confidential, restricted
    current_version_id = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    version_no = Column(Integer, default=1)
    file_path = Column(String, nullable=False)          # path to encrypted blob on disk
    nonce = Column(String, nullable=False)               # hex-encoded AES-GCM nonce
    encrypted_dek = Column(Text, nullable=False)          # DEK wrapped by master key (envelope encryption)
    file_hash = Column(String, nullable=False)            # SHA-256 of ORIGINAL plaintext (legal hash)
    mime_type = Column(String, nullable=True)
    original_filename = Column(String, nullable=True)
    file_size = Column(BigInteger, default=0)
    uploaded_by = Column(String, ForeignKey("users.id"))
    is_original = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AccessControl(Base):
    __tablename__ = "access_control"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    permission = Column(String, default="read")  # read, write
    granted_by = Column(String, ForeignKey("users.id"))
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    prev_hash = Column(String, nullable=False)   # hash-chain: links to previous entry
    log_hash = Column(String, nullable=False)    # hash-chain: this entry's own hash
