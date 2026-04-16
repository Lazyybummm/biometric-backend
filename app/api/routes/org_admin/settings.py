from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

router = APIRouter()


# =========================
# SCHEMA
# =========================

class SettingsUpdate(BaseModel):
    office_start_time: str
    office_end_time: str
    late_threshold_minutes: int


# =========================
# GET SETTINGS
# =========================

@router.get("/settings")
async def get_settings(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT *
        FROM settings
        WHERE tenant_id = :tenant_id
        LIMIT 1
    """), {"tenant_id": tenant_id})

    return result.mappings().first()


# =========================
# UPDATE SETTINGS
# =========================

@router.put("/settings")
async def update_settings(
    data: SettingsUpdate,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        UPDATE settings
        SET office_start_time = :office_start_time,
            office_end_time = :office_end_time,
            late_threshold_minutes = :late_threshold_minutes
        WHERE tenant_id = :tenant_id
    """), {
        "tenant_id": tenant_id,
        **data.dict()
    })

    await db.commit()

    return {"message": "settings updated"}