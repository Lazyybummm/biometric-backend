# api/routes/tenant/settings.py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from app.db.session import get_db
from app.api.dependencies import verify_tenant_api_key
from app.models.domain import Tenant

router = APIRouter()


# =========================
# SCHEMAS
# =========================

class SettingsUpdate(BaseModel):
    office_start_time: str = "09:00:00"
    office_end_time: str = "18:00:00"
    late_threshold_minutes: int = 15
    working_days: str = "1,2,3,4,5"  # Mon-Fri


# =========================
# PUBLIC GET ROUTE - No Auth Required
# =========================

@router.get("/settings/public")
async def get_public_settings(
    tenant_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    PUBLIC endpoint - Get organization settings (no authentication required).
    Used for frontend calculations without requiring API key.
    """
    
    result = await db.execute(text("""
        SELECT office_start_time, office_end_time, late_threshold_minutes, working_days
        FROM settings
        WHERE tenant_id = :tenant_id
        LIMIT 1
    """), {"tenant_id": tenant_id})
    
    settings = result.mappings().first()
    
    if not settings:
        # Return defaults
        return {
            "office_start_time": "09:00:00",
            "office_end_time": "18:00:00",
            "late_threshold_minutes": 15,
            "working_days": "1,2,3,4,5"
        }
    
    return {
        "office_start_time": settings["office_start_time"],
        "office_end_time": settings["office_end_time"],
        "late_threshold_minutes": settings["late_threshold_minutes"],
        "working_days": settings["working_days"]
    }


# =========================
# AUTHENTICATED GET ROUTE - API Key Required
# =========================

@router.get("/settings")
async def get_settings(
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Get organization settings (requires API key)"""
    
    result = await db.execute(text("""
        SELECT *
        FROM settings
        WHERE tenant_id = :tenant_id
        LIMIT 1
    """), {"tenant_id": tenant.id})
    
    settings = result.mappings().first()
    
    if not settings:
        # Return defaults
        return {
            "office_start_time": "09:00:00",
            "office_end_time": "18:00:00",
            "late_threshold_minutes": 15,
            "working_days": "1,2,3,4,5"
        }
    
    return settings


# =========================
# UPDATE ROUTE - API Key Required
# =========================

@router.put("/settings")
async def update_settings(
    data: SettingsUpdate,
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Update organization settings (requires API key)"""
    
    # Upsert settings
    await db.execute(text("""
        INSERT INTO settings (tenant_id, office_start_time, office_end_time, late_threshold_minutes, working_days)
        VALUES (:tenant_id, :office_start_time, :office_end_time, :late_threshold_minutes, :working_days)
        ON CONFLICT (tenant_id) DO UPDATE SET
            office_start_time = EXCLUDED.office_start_time,
            office_end_time = EXCLUDED.office_end_time,
            late_threshold_minutes = EXCLUDED.late_threshold_minutes,
            working_days = EXCLUDED.working_days,
            updated_at = NOW()
    """), {
        "tenant_id": tenant.id,
        "office_start_time": data.office_start_time,
        "office_end_time": data.office_end_time,
        "late_threshold_minutes": data.late_threshold_minutes,
        "working_days": data.working_days
    })
    
    await db.commit()
    
    return {"message": "Settings updated successfully"}


@router.get("/profile")
async def get_tenant_profile(
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Get own profile"""
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "api_key": tenant.api_key,
        "created_at": tenant.created_at
    }