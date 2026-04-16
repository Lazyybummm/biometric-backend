from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.domain import AdminUser, RoleEnum, User
from pydantic import BaseModel
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
import secrets

router = APIRouter()


# =========================
# SIGNUP (ADMIN)
# =========================

class SignupRequest(BaseModel):
    username: str
    password: str


@router.post("/signup")   # ✅ FIXED
async def signup(
    data: SignupRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == data.username)
    )
    existing = result.scalars().first()

    if existing:
        raise HTTPException(400, "User already exists")

    new_user = AdminUser(
        username=data.username,
        password=hash_password(data.password),
        api_token=secrets.token_hex(32),
        role=RoleEnum.SUPER_ADMIN
    )

    db.add(new_user)
    await db.commit()

    return {"message": "User created"}


# =========================
# LOGIN (ADMIN - OAUTH2)
# =========================

@router.post("/login")   # ✅ FIXED
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == form_data.username)
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(401, "Invalid credentials")

    payload = {
        "user_id": user.id,
        "role": "admin",
        "tenant_id": user.tenant_id
    }

    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type": "bearer"
    }


# =========================
# EMPLOYEE LOGIN (TENANT SAFE)
# =========================

class EmployeeLogin(BaseModel):
    employee_code: str
    tenant_id: int   # ✅ REQUIRED


@router.post("/employee-login")   # ✅ FIXED
async def employee_login(
    data: EmployeeLogin,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(
            User.employee_code == data.employee_code,
            User.tenant_id == data.tenant_id
        )
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(404, "User not found")

    payload = {
        "user_id": user.id,
        "role": "employee",
        "tenant_id": user.tenant_id
    }

    return {
        "access_token": create_access_token(payload),
        "token_type": "bearer"
    }


# =========================
# REFRESH TOKEN
# =========================

class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")   # ✅ FIXED
async def refresh_token(data: RefreshRequest):
    try:
        payload = decode_token(data.refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token")

        user_id = payload.get("user_id")
        role = payload.get("role")
        tenant_id = payload.get("tenant_id")

        return {
            "access_token": create_access_token({
                "user_id": user_id,
                "role": role,
                "tenant_id": tenant_id
            }),
            "token_type": "bearer"
        }

    except:
        raise HTTPException(401, "Invalid refresh token")