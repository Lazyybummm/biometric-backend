from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.future import select
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.domain import User

router = APIRouter()


# =========================
# HELPER → GET USER
# =========================

async def get_user(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# =========================
# ATTENDANCE LIST
# =========================

@router.get("/attendance")
async def get_attendance(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user = await get_user(user_id, db)

    query = text("""
        SELECT
            DATE(timestamp) as attendance_date,
            MIN(timestamp) FILTER (WHERE record_type='IN') as check_in,
            MAX(timestamp) FILTER (WHERE record_type='OUT') as check_out
        FROM attendance_logs
        WHERE tenant_id = :tenant_id
        AND finger_id = :finger_id
        GROUP BY DATE(timestamp)
        ORDER BY attendance_date DESC
    """)

    result = await db.execute(query, {
        "tenant_id": user.tenant_id,
        "finger_id": user.finger_id
    })

    return result.mappings().all()


# =========================
# ATTENDANCE DETAIL
# =========================

@router.get("/attendance/{date}")
async def attendance_detail(
    date: str,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user = await get_user(user_id, db)

    query = text("""
        SELECT
            DATE(timestamp) as attendance_date,
            MIN(timestamp) FILTER (WHERE record_type='IN') as check_in,
            MAX(timestamp) FILTER (WHERE record_type='OUT') as check_out
        FROM attendance_logs
        WHERE tenant_id = :tenant_id
        AND finger_id = :finger_id
        AND DATE(timestamp) = :date
        GROUP BY DATE(timestamp)
    """)

    result = await db.execute(query, {
        "tenant_id": user.tenant_id,
        "finger_id": user.finger_id,
        "date": date
    })

    return result.mappings().first()


# =========================
# STATS
# =========================

@router.get("/attendance/stats")
async def attendance_stats(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user = await get_user(user_id, db)

    query = text("""
        SELECT
        COUNT(DISTINCT DATE(timestamp))
        FILTER (WHERE record_type='IN') as present_days,

        COUNT(*) FILTER (
            WHERE record_type='IN'
            AND timestamp::time > '09:15'
        ) as late_days

        FROM attendance_logs
        WHERE tenant_id = :tenant_id
        AND finger_id = :finger_id
    """)

    result = await db.execute(query, {
        "tenant_id": user.tenant_id,
        "finger_id": user.finger_id
    })

    stats = result.mappings().first()

    stats["present_days"] = stats["present_days"] or 0
    stats["late_days"] = stats["late_days"] or 0
    stats["absent_days"] = 30 - stats["present_days"]

    return stats


# =========================
# EXPORT
# =========================

@router.get("/attendance/export")
async def export_attendance():
    return {
        "message": "export ready",
        "format": "csv"
    }