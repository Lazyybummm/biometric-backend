from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.db.session import get_db

router = APIRouter()

# ========================
# SCHEMA
# ========================

class ManualAttendance(BaseModel):
    employee_id: int
    datetime: datetime
    record_type: str   # IN or OUT


# ========================
# ROUTES
# ========================


# GET full attendance list
@router.get("/attendance")
async def get_attendance(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT
            a.attendance_id,
            a.employee_id,
            e.name,
            a.check_time,
            a.record_type

        FROM attendance_logs a

        JOIN employees e
        ON a.employee_id = e.employee_id

        ORDER BY a.check_time DESC

    """))

    return result.mappings().all()



# GET today's attendance
@router.get("/attendance/today")
async def today_attendance(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT
            a.employee_id,
            e.name,
            a.check_time,
            a.record_type

        FROM attendance_logs a

        JOIN employees e
        ON a.employee_id = e.employee_id

        WHERE DATE(a.check_time) = CURRENT_DATE

        ORDER BY a.check_time DESC

    """))

    return result.mappings().all()


#manal attendance
from pydantic import BaseModel
from datetime import datetime


class ManualAttendance(BaseModel):
    employee_id: int
    check_time: datetime
    record_type: str   # IN or OUT


@router.post("/attendance/manual")
async def manual_attendance(
        data: ManualAttendance,
        db: AsyncSession = Depends(get_db)
):

    await db.execute(text("""

        INSERT INTO attendance_logs
        (employee_id, check_time, record_type)

        VALUES
        (:employee_id, :check_time, :record_type)

    """), data.dict())

    await db.commit()

    return {
        "message": "attendance added manually"
    }



# attendance statistics
@router.get("/attendance/stats")
async def attendance_stats(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT

        COUNT(DISTINCT employee_id)
        FILTER (WHERE DATE(check_time)=CURRENT_DATE)
        as present_today,

        (SELECT COUNT(*)
         FROM employees
         WHERE is_active=true)

         -

        COUNT(DISTINCT employee_id)
        FILTER (WHERE DATE(check_time)=CURRENT_DATE)
        as absent_today

        FROM attendance_logs

    """))

    return result.mappings().first()