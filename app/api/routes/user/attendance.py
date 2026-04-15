from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

CURRENT_USER_ID = 1


# attendance list
@router.get("/attendance")
async def get_attendance(db: AsyncSession = Depends(get_db)):

    query = text("""

        SELECT
            attendance_date,
            MIN(check_time) FILTER (WHERE record_type='IN') as check_in,
            MAX(check_time) FILTER (WHERE record_type='OUT') as check_out

        FROM attendance_logs

        WHERE employee_id = :user_id

        GROUP BY attendance_date

        ORDER BY attendance_date DESC

    """)

    result = await db.execute(query, {"user_id": CURRENT_USER_ID})

    return result.mappings().all()



# attendance detail
@router.get("/attendance/{date}")
async def attendance_detail(date: str,
                            db: AsyncSession = Depends(get_db)):

    query = text("""

        SELECT
            attendance_date,
            MIN(check_time) FILTER (WHERE record_type='IN') as check_in,
            MAX(check_time) FILTER (WHERE record_type='OUT') as check_out

        FROM attendance_logs

        WHERE employee_id = :user_id
        AND attendance_date = :date

        GROUP BY attendance_date

    """)

    result = await db.execute(query, {
        "user_id": CURRENT_USER_ID,
        "date": date
    })

    return result.mappings().first()



# stats
@router.get("/attendance/stats")
async def attendance_stats(db: AsyncSession = Depends(get_db)):

    query = text("""

        SELECT

        COUNT(DISTINCT attendance_date)
        FILTER (WHERE record_type='IN')
        as present_days,

        COUNT(*) FILTER (
            WHERE record_type='IN'
            AND check_time::time > '09:15'
        )
        as late_days

        FROM attendance_logs

        WHERE employee_id=:user_id

    """)

    result = await db.execute(query, {"user_id": CURRENT_USER_ID})

    stats = result.mappings().first()

    stats["absent_days"] = 30 - stats["present_days"]

    return stats



# export attendance
@router.get("/attendance/export")
async def export_attendance():

    return {
        "message": "export ready",
        "format": "csv"
    }