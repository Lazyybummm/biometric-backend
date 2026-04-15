from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

CURRENT_USER_ID = 1


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):

    query = text("""

        SELECT

        MIN(check_time)
        FILTER (WHERE attendance_date=CURRENT_DATE)
        as check_in,

        MAX(check_time)
        FILTER (WHERE attendance_date=CURRENT_DATE)
        as check_out,

        COUNT(DISTINCT attendance_date)
        FILTER (
            WHERE DATE_TRUNC('month', attendance_date)
            = DATE_TRUNC('month', CURRENT_DATE)
        )
        as present_days

        FROM attendance_logs

        WHERE employee_id=:user_id

    """)

    result = await db.execute(query, {"user_id": CURRENT_USER_ID})

    return result.mappings().first()