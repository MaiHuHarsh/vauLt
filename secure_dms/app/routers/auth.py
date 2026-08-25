from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..security import hash_password, verify_password, create_access_token
from ..audit import create_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.UserOut)
def signup(payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(400, "Username already taken")
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")

    # New accounts start at the lowest-privilege role; a master account
    # must explicitly grant a higher role and case/document access.
    user = models.User(
        username=payload.username, email=payload.email, full_name=payload.full_name,
        password_hash=hash_password(payload.password), role="clerk", status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    create_audit_log(db, user.id, user.username, "user_signup", "user", user.id)
    return user


@router.post("/login", response_model=schemas.TokenOut)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        create_audit_log(db, None, form_data.username, "login_failed", "user", None)
        raise HTTPException(401, "Incorrect username or password")
    if user.status != "active":
        create_audit_log(db, user.id, user.username, "login_blocked_suspended", "user", user.id)
        raise HTTPException(403, "Account suspended")

    token = create_access_token({"sub": user.id, "role": user.role})
    create_audit_log(db, user.id, user.username, "login_success", "user", user.id)
    return {
        "access_token": token, "token_type": "bearer",
        "role": user.role, "user_id": user.id, "username": user.username,
    }
