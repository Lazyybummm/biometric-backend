from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):

    # employee stats
    emp_stats = await db.execute(text("""

        SELECT

        COUNT(*) as total_employees,

        COUNT(*) FILTER (WHERE is_active=true)
        as active_employees,

        COUNT(*) FILTER (WHERE is_active=false)
        as inactive_employees

        FROM employees

    """))

    emp_data = emp_stats.mappings().first()



    # today attendance
    att_stats = await db.execute(text("""

        SELECT

        COUNT(DISTINCT employee_id)
        FILTER (WHERE DATE(check_time)=CURRENT_DATE)
        as present_today

        FROM attendance_logs

    """))

    present_data = att_stats.mappings().first()



    # count active employees
    total_active = emp_data["active_employees"]


    present_today = present_data["present_today"] or 0


    absent_today = total_active - present_today



    return {

        "total_employees": emp_data["total_employees"],

        "active_employees": total_active,

        "inactive_employees": emp_data["inactive_employees"],

        "present_today": present_today,

        "absent_today": absent_today
    }