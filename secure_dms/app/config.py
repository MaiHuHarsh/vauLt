import os
import secrets
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# app/config.py -> parent = app/, parent.parent = project root
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Self-init: generate a fresh .env with a unique master key and JWT secret
# the first time this project runs, so it works "out of the box" without
# any manual setup step.
if not ENV_PATH.exists():
    with open(ENV_PATH, "w") as f:
        f.write(f"MASTER_KEY={Fernet.generate_key().decode()}\n")
        f.write(f"JWT_SECRET={secrets.token_hex(32)}\n")
        f.write("DATABASE_URL=sqlite:///./dms.db\n")
        f.write("STORAGE_DIR=./storage\n")

load_dotenv(ENV_PATH)

MASTER_KEY = os.environ["MASTER_KEY"].encode()
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 480

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dms.db")

STORAGE_DIR = BASE_DIR / os.environ.get("STORAGE_DIR", "./storage")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
