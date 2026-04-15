from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


@router.get("/activity")
async def activity_log(db: AsyncSession = Depends(get_db)):

    query = text("""

        SELECT 
            'attendance_marked' as activity,
            employee_id,
            check_time as time
        FROM attendance_logs

        UNION ALL

        SELECT
            'leave_requested' as activity,
            employee_id,
            created_at as time
        FROM leaves

        ORDER BY time DESC
        LIMIT 20

    """)

    result = await db.execute(query)

    activities = result.mappings().all()

    return activities