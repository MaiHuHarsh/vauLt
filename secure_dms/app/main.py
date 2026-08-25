from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine, SessionLocal
from . import models
from .security import hash_password
from .routers import auth, users, cases, documents, access, audit_routes

app = FastAPI(title="Secure Digital Document Management System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(access.router)
app.include_router(audit_routes.router)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(models.User).filter(models.User.role == "master").first():
            master = models.User(
                username="master", email="master@dms.local", full_name="Master Administrator",
                password_hash=hash_password("Master@123"), role="master", status="active",
            )
            db.add(master)
            db.commit()
            print("=" * 64)
            print(" MASTER ACCOUNT CREATED")
            print(" username: master")
            print(" password: Master@123")
            print(" Change this password after first login (see README).")
            print("=" * 64)
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok", "service": "Secure Digital Document Management System"}
