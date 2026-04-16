from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

router = APIRouter()


# =========================
# GET ALL DEVICES
# =========================

@router.get("/devices")
async def get_devices(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT *
        FROM devices
        WHERE tenant_id = :tenant_id
        ORDER BY device_id
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# =========================
# DEVICE DETAIL
# =========================

@router.get("/devices/{device_id}")
async def device_detail(
    device_id: str,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT *
        FROM devices
        WHERE device_id = :device_id
        AND tenant_id = :tenant_id
    """), {
        "device_id": device_id,
        "tenant_id": tenant_id
    })

    return result.mappings().first()


# =========================
# DEVICE STATUS
# =========================

@router.get("/devices/status")
async def device_status(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT
        COUNT(*) FILTER (WHERE status = 'online') as online,
        COUNT(*) FILTER (WHERE status != 'online') as offline
        FROM devices
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": tenant_id})

    data = result.mappings().first()

    return {
        "online": data["online"] or 0,
        "offline": data["offline"] or 0
    }