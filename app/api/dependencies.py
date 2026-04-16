from fastapi import Header, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.domain import Device, AdminUser
from app.core.security import decode_token
import datetime


# =========================
# OAUTH2 SECURITY (SWAGGER LOGIN FORM)
# =========================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# =========================
# INTERNAL: TOKEN VALIDATION
# =========================

def verify_jwt_token(token: str):
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload


# =========================
# JWT ADMIN AUTH (OAUTH2)
# =========================

async def get_current_admin(
    token: str = Depends(oauth2_scheme)
) -> int:
    try:
        payload = verify_jwt_token(token)
        return payload["user_id"]

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# =========================
# JWT USER AUTH (OAUTH2)
# =========================

async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> int:
    try:
        payload = verify_jwt_token(token)
        return payload["user_id"]

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# =========================
# FETCH FULL ADMIN
# =========================

async def get_admin_data(
    admin_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == admin_id)
    )
    admin = result.scalars().first()

    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")

    return admin


# =========================
# DEVICE AUTH (NO JWT)
# =========================

async def verify_device(
    x_device_id: str = Header(..., alias="x-device-id"),
    x_secret_key: str = Header(..., alias="x-secret-key"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Device).where(
            Device.device_id == x_device_id,
            Device.secret_key == x_secret_key
        )
    )

    device = result.scalars().first()

    if not device:
        raise HTTPException(status_code=401, detail="Invalid Device Credentials")

    # ✅ Update heartbeat
    device.last_seen = datetime.datetime.utcnow()
    device.status = "online"

    await db.commit()

    return device