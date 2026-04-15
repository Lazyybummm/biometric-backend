from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from datetime import date
from app.db.session import get_db

router = APIRouter()


# ========================
# SCHEMA
# ========================

class LeaveCreate(BaseModel):
    employee_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str


# ========================
# ROUTES
# ========================


# get all leave requests
@router.get("/leaves")
async def get_leaves(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT
            l.leave_id,
            e.name,
            l.leave_type,
            l.start_date,
            l.end_date,
            l.status

        FROM leaves l

        JOIN employees e
        ON l.employee_id = e.employee_id

        ORDER BY l.start_date DESC

    """))

    return result.mappings().all()



# approve leave
@router.patch("/leaves/{leave_id}/approve")
async def approve_leave(leave_id: int,
                        db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        UPDATE leaves
        SET status='approved'

        WHERE leave_id=:leave_id

    """), {"leave_id": leave_id})

    await db.commit()

    return {"message": "leave approved"}



# reject leave
@router.patch("/leaves/{leave_id}/reject")
async def reject_leave(leave_id: int,
                       db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        UPDATE leaves
        SET status='rejected'

        WHERE leave_id=:leave_id

    """), {"leave_id": leave_id})

    await db.commit()

    return {"message": "leave rejected"}



# leave statistics
@router.get("/leaves/stats")
async def leave_stats(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT

        COUNT(*) FILTER (WHERE status='pending')
        as pending,

        COUNT(*) FILTER (WHERE status='approved')
        as approved,

        COUNT(*) FILTER (WHERE status='rejected')
        as rejected

        FROM leaves

    """))

    return result.mappings().first()