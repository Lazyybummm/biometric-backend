from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


@router.get("/reports/attendance")
async def attendance_report(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT *
        FROM attendance_logs
        ORDER BY check_time DESC

    """))

    return result.mappings().all()



@router.get("/reports/leaves")
async def leave_report(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT *
        FROM leaves

    """))

    return result.mappings().all()



@router.get("/reports/attendance/export")
async def export_attendance_report():

    return {
        "message": "export ready",
        "format": "csv"
    }