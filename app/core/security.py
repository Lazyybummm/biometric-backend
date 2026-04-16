from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException
import hashlib

# =========================
# CONFIG
# =========================

SECRET_KEY = "your_super_secret_key"   # ⚠️ move to .env later
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========================
# PASSWORD (FIXED)
# =========================

def hash_password(password: str) -> str:
    """
    Secure password hashing:
    SHA256 → bcrypt (avoids bcrypt 72-byte limit)
    """
    password = password.strip()

    if not password:
        raise HTTPException(status_code=400, detail="Password cannot be empty")

    sha_hash = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(sha_hash)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify password using same SHA256 + bcrypt logic
    """
    if not plain or not hashed:
        return False

    plain = plain.strip()
    sha_hash = hashlib.sha256(plain.encode()).hexdigest()

    return pwd_context.verify(sha_hash, hashed)


# =========================
# TOKENS
# =========================

def create_access_token(data: dict) -> str:
    """
    Create JWT access token
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "type": "access"
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode JWT token safely
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )