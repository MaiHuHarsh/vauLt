from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    status: str

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: str
    username: str


class RoleUpdate(BaseModel):
    role: str


class StatusUpdate(BaseModel):
    status: str


class CaseCreate(BaseModel):
    case_number: str
    title: str
    description: Optional[str] = None
    sensitivity_level: Optional[str] = "normal"


class CaseOut(BaseModel):
    id: str
    case_number: str
    title: str
    description: Optional[str] = None
    status: str
    sensitivity_level: str
    legal_hold: bool
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: str
    case_id: Optional[str] = None
    doc_type: str
    title: str
    classification: str
    current_version_id: Optional[str] = None
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class AccessGrant(BaseModel):
    user_id: str
    case_id: Optional[str] = None
    document_id: Optional[str] = None
    permission: str = "read"
    expires_at: Optional[datetime] = None
