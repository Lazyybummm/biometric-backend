from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

router = APIRouter()

# ========================
# SCHEMA
# ========================

class ManualAttendance(BaseModel):
    finger_id: int
    timestamp: datetime
    record_type: str   # IN or OUT


# ========================
# ROUTES
# ========================

# GET full attendance list
@router.get("/attendance")
async def get_attendance(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT
            a.finger_id,
            u.name,
            a.timestamp,
            a.record_type
        FROM attendance_logs a
        LEFT JOIN users u
        ON a.tenant_id = u.tenant_id
        AND a.finger_id = u.finger_id   -- ⚠️ TEMP FIX (see note below)
        WHERE a.tenant_id = :tenant_id
        ORDER BY a.timestamp DESC
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# GET today's attendance
@router.get("/attendance/today")
async def today_attendance(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT
            a.finger_id,
            u.name,
            a.timestamp,
            a.record_type
        FROM attendance_logs a
        LEFT JOIN users u
        ON a.tenant_id = u.tenant_id
        AND a.finger_id = u.finger_id   -- ⚠️ TEMP FIX
        WHERE a.tenant_id = :tenant_id
        AND DATE(a.timestamp) = CURRENT_DATE
        ORDER BY a.timestamp DESC
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# MANUAL attendance
@router.post("/attendance/manual")
async def manual_attendance(
    data: ManualAttendance,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        INSERT INTO attendance_logs
        (tenant_id, device_id, finger_id, timestamp, record_type)
        VALUES
        (:tenant_id, 'manual', :finger_id, :timestamp, :record_type)
    """), {
        "tenant_id": tenant_id,
        "finger_id": data.finger_id,
        "timestamp": data.timestamp,
        "record_type": data.record_type
    })

    await db.commit()

    return {"message": "attendance added manually"}


# attendance statistics
@router.get("/attendance/stats")
async def attendance_stats(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT
        COUNT(DISTINCT finger_id)
        FILTER (WHERE DATE(timestamp)=CURRENT_DATE)
        as present_today
        FROM attendance_logs
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": tenant_id})

    data = result.mappings().first()

    total_users = await db.execute(text("""
        SELECT COUNT(*) as total
        FROM users
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": tenant_id})

    total = total_users.mappings().first()["total"]
    present = data["present_today"] or 0

    return {
        "present_today": present,
        "absent_today": total - present
    }