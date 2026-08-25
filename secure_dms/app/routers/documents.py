import uuid
from io import BytesIO
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..deps import get_current_user
from ..audit import create_audit_log
from ..permissions import has_access
from ..crypto import encrypt_file, decrypt_file, hash_bytes
from ..config import STORAGE_DIR

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=schemas.DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: str = Form(...),
    classification: str = Form("internal"),
    case_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if case_id:
        case = db.query(models.Case).filter(models.Case.id == case_id).first()
        if not case:
            raise HTTPException(404, "Case not found")
        if not has_access(db, user, case_id=case_id, need="write"):
            create_audit_log(db, user.id, user.username, "access_denied", "case", case_id)
            raise HTTPException(403, "No write access to this case")

    plaintext = await file.read()
    file_hash = hash_bytes(plaintext)
    ciphertext, nonce, encrypted_dek = encrypt_file(plaintext)

    stored_name = f"{uuid.uuid4()}.enc"
    file_path = STORAGE_DIR / stored_name
    with open(file_path, "wb") as f:
        f.write(ciphertext)

    doc = models.Document(
        case_id=case_id, doc_type=doc_type, title=title,
        classification=classification, created_by=user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    version = models.DocumentVersion(
        document_id=doc.id, version_no=1, file_path=str(file_path),
        nonce=nonce.hex(), encrypted_dek=encrypted_dek.decode(),
        file_hash=file_hash, mime_type=file.content_type,
        original_filename=file.filename, file_size=len(plaintext),
        uploaded_by=user.id, is_original=True,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    doc.current_version_id = version.id
    db.commit()
    db.refresh(doc)

    # auto-grant the uploader access to the document itself
    db.add(models.AccessControl(user_id=user.id, document_id=doc.id, permission="write", granted_by=user.id))
    db.commit()

    create_audit_log(db, user.id, user.username, "document_upload", "document", doc.id,
                      details=f"hash={file_hash[:12]}")
    return doc


@router.get("", response_model=List[schemas.DocumentOut])
def list_documents(case_id: Optional[str] = None, db: Session = Depends(get_db),
                    user: models.User = Depends(get_current_user)):
    q = db.query(models.Document)
    if case_id:
        q = q.filter(models.Document.case_id == case_id)
    docs = q.all()
    if user.role == "master":
        return docs
    return [d for d in docs if has_access(db, user, case_id=d.case_id, document_id=d.id)]


@router.post("/{document_id}/new-version", response_model=schemas.DocumentOut)
async def upload_new_version(
    document_id: str, file: UploadFile = File(...), change_reason: str = Form(""),
    db: Session = Depends(get_db), user: models.User = Depends(get_current_user),
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if not has_access(db, user, case_id=doc.case_id, document_id=doc.id, need="write"):
        create_audit_log(db, user.id, user.username, "access_denied", "document", document_id)
        raise HTTPException(403, "No write access to this document")

    plaintext = await file.read()
    file_hash = hash_bytes(plaintext)
    ciphertext, nonce, encrypted_dek = encrypt_file(plaintext)
    stored_name = f"{uuid.uuid4()}.enc"
    file_path = STORAGE_DIR / stored_name
    with open(file_path, "wb") as f:
        f.write(ciphertext)

    last_version = (
        db.query(models.DocumentVersion)
        .filter(models.DocumentVersion.document_id == doc.id)
        .order_by(models.DocumentVersion.version_no.desc())
        .first()
    )
    next_no = (last_version.version_no + 1) if last_version else 1

    version = models.DocumentVersion(
        document_id=doc.id, version_no=next_no, file_path=str(file_path),
        nonce=nonce.hex(), encrypted_dek=encrypted_dek.decode(),
        file_hash=file_hash, mime_type=file.content_type,
        original_filename=file.filename, file_size=len(plaintext),
        uploaded_by=user.id, is_original=False,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    doc.current_version_id = version.id
    db.commit()
    db.refresh(doc)

    create_audit_log(db, user.id, user.username, "document_new_version", "document", doc.id,
                      details=f"v{next_no}, reason={change_reason}")
    return doc


@router.get("/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db),
                       user: models.User = Depends(get_current_user)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if not has_access(db, user, case_id=doc.case_id, document_id=doc.id):
        create_audit_log(db, user.id, user.username, "access_denied", "document", document_id)
        raise HTTPException(403, "Access denied")

    version = db.query(models.DocumentVersion).filter(models.DocumentVersion.id == doc.current_version_id).first()
    if not version:
        raise HTTPException(404, "No version found for this document")

    with open(version.file_path, "rb") as f:
        ciphertext = f.read()

    try:
        plaintext = decrypt_file(ciphertext, bytes.fromhex(version.nonce), version.encrypted_dek.encode())
    except Exception:
        create_audit_log(db, user.id, user.username, "integrity_failure", "document", document_id,
                          details="decryption failed")
        raise HTTPException(500, "Decryption failed -- file may be corrupted or tampered")

    if hash_bytes(plaintext) != version.file_hash:
        create_audit_log(db, user.id, user.username, "integrity_failure", "document", document_id,
                          details="hash mismatch")
        raise HTTPException(409, "Integrity check failed: file hash mismatch, possible tampering")

    create_audit_log(db, user.id, user.username, "document_download", "document", document_id,
                      details=f"v{version.version_no}")

    filename = version.original_filename or "document"
    mime = version.mime_type or "application/octet-stream"
    return StreamingResponse(
        BytesIO(plaintext), media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{document_id}/versions")
def list_versions(document_id: str, db: Session = Depends(get_db),
                   user: models.User = Depends(get_current_user)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if not has_access(db, user, case_id=doc.case_id, document_id=doc.id):
        raise HTTPException(403, "Access denied")
    versions = (
        db.query(models.DocumentVersion)
        .filter(models.DocumentVersion.document_id == document_id)
        .order_by(models.DocumentVersion.version_no)
        .all()
    )
    return [
        {
            "id": v.id, "version_no": v.version_no, "file_hash": v.file_hash,
            "uploaded_by": v.uploaded_by, "is_original": v.is_original,
            "created_at": v.created_at.isoformat(), "filename": v.original_filename,
        }
        for v in versions
    ]
