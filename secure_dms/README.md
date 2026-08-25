# Secure Digital Document Management System — MVP

Prototype for SIH Problem Statement 26190 — Secure Digital Document Management
System for Legal and Investigation Documents (Ministry of Home Affairs, NCRB
Women Safety Division).

Stack: **FastAPI + SQLite + Streamlit**, no external services required.
Files are encrypted and stored on local disk (no MinIO/S3 needed for this MVP).

---

## Quick start

### Linux / Mac
```bash
chmod +x start.sh
./start.sh
```

### Windows
```
start.bat
```

Either script will:
1. Create a virtual environment and install dependencies (first run only)
2. Auto-generate a `.env` file with a unique encryption master key and JWT secret
3. Start the FastAPI backend at `http://localhost:8000`
4. Start the Streamlit frontend at `http://localhost:8501` — open this in your browser

On first backend start, a **master account** is created automatically:

```
username: master
password: Master@123
```

**Change this password immediately after first login** (there's no self-service
password-change endpoint in this MVP — the fastest fix is to delete `dms.db`
and restart, which re-seeds a fresh master account, or add a
`PATCH /users/me/password` route before your demo if you want it in-app).

---

## What's implemented

- **Signup / login** — JWT-based auth, bcrypt password hashing
- **Master account** — the only role that can promote/demote other users'
  roles and suspend/reactivate accounts (Admin page in the sidebar)
- **Cases** — create, list (scoped to what each user has access to)
- **Documents** — upload, versioning (new versions never overwrite old ones),
  encrypted download
- **Encryption** — envelope encryption: each file gets its own random
  AES-256-GCM key (DEK), and that DEK is itself encrypted with a master key
  that lives only in `.env`, never in the database
- **Integrity** — SHA-256 hash of every file's original content is stored and
  re-checked on every download; mismatch blocks delivery and logs it
- **Hash-chain audit log** — every action (including denied access attempts)
  is written as a chained, tamper-evident log entry; `/audit/verify` walks
  the whole chain and reports the exact break point if anything was altered
  outside the app
- **Access control** — per-case and per-document grants, read/write,
  expiry support; master always has full access

## Roles

`master`, `investigating_officer`, `judge`, `prosecutor`, `forensic`, `clerk`

New signups start as `clerk` with no case access — a master account must
grant access or raise the role via the Admin page.

---

## Demoing the tamper-evidence (the key "wow" moment)

1. Log in, upload a document, go to **Audit log**, click **Verify chain
   integrity** — should show "Chain intact".
2. Open `dms.db` directly with a SQLite browser (e.g. `sqlite3 dms.db` or
   DB Browser for SQLite), find a row in `audit_logs`, and edit its `action`
   or `details` field directly — bypassing the app entirely.
3. Go back to **Audit log** → **Verify chain integrity** again — it will
   report `TAMPERED` and the exact log ID / timestamp where the break
   happened.

This demonstrates the core evidentiary-integrity claim live, in front of
judges, without needing a real blockchain network.

---

## Project structure

```
secure_dms/
  app/
    main.py            FastAPI app, table creation, master account seeding
    config.py           .env auto-generation, paths
    db.py                SQLAlchemy engine/session
    models.py           ORM schema
    schemas.py          Pydantic request/response models
    security.py         password hashing + JWT
    crypto.py             envelope encryption (AES-256-GCM + master key)
    audit.py               hash-chain audit log logic
    deps.py               auth dependencies
    permissions.py       access-control checks
    routers/
      auth.py, users.py, cases.py, documents.py, access.py, audit_routes.py
  frontend/
    app.py               Streamlit UI (login, dashboard, case detail, audit, admin)
    api_client.py       thin wrapper around backend REST calls
  storage/                encrypted document blobs land here
  requirements.txt
  start.sh / start.bat
  .env                  auto-generated on first run (never commit this)
```

## Notes for the judges' Q&A

- **Why local disk instead of MinIO?** This MVP swaps MinIO for local
  filesystem storage to cut deployment complexity; the storage layer is a
  single module (`app/crypto.py` handles encryption, the upload/download
  routes in `app/routers/documents.py` handle the file I/O), so swapping in
  MinIO/S3 later is a contained change, not a rewrite.
- **Why SQLite instead of Postgres?** Same reasoning — zero external
  dependencies for a hackathon judging round. The schema is plain SQLAlchemy
  ORM and migrates to Postgres by changing one connection string.
- **Where does the master encryption key live?** In `.env`, generated fresh
  on first run, never written to the database — so a database-only breach
  exposes only ciphertext and wrapped keys, both useless without it.
