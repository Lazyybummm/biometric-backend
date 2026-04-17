from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import uuid

SECRET_KEY = "CHANGE_THIS_SECRET_IN_PRODUCTION"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =====================
# PASSWORD HASH
# =====================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


# =====================
# ACCESS TOKEN
# =====================

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["type"] = "access"
    payload["jti"] = str(uuid.uuid4())  # Unique token ID
    payload["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# =====================
# REFRESH TOKEN
# =====================

def create_refresh_token(data: dict) -> tuple[str, str]:
    """
    Returns: (refresh_token_string, jti)
    jti is stored in DB for rotation/revocation
    """
    payload = data.copy()
    payload["type"] = "refresh"
    jti = str(uuid.uuid4())
    payload["jti"] = jti
    payload["exp"] = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti


# =====================
# DECODE TOKEN
# =====================

def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None