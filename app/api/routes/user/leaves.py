from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.dependencies import get_current_user

router = APIRouter()


# list leaves
@router.get("/leaves")
async def get_leaves(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(text("""
        SELECT *
        FROM leaves
        WHERE employee_id = :user_id
        ORDER BY start_date DESC
    """), {"user_id": user_id})

    return result.mappings().all()


# apply leave
@router.post("/leaves")
async def apply_leave(
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    await db.execute(text("""
        INSERT INTO leaves
        (employee_id, leave_type, start_date, end_date, reason, status)
        VALUES
        (:employee_id, :leave_type, :start_date, :end_date, :reason, 'pending')
    """), {
        "employee_id": user_id,
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason
    })

    await db.commit()

    return {"message": "leave applied"}


# leave detail
@router.get("/leaves/{leave_id}")
async def leave_detail(
    leave_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(text("""
        SELECT *
        FROM leaves
        WHERE leave_id = :leave_id
        AND employee_id = :user_id
    """), {
        "leave_id": leave_id,
        "user_id": user_id
    })

    return result.mappings().first()


# cancel leave
@router.patch("/leaves/{leave_id}/cancel")
async def cancel_leave(
    leave_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    await db.execute(text("""
        UPDATE leaves
        SET status = 'cancelled'
        WHERE leave_id = :leave_id
        AND employee_id = :user_id
    """), {
        "leave_id": leave_id,
        "user_id": user_id
    })

    await db.commit()

    return {"message": "leave cancelled"}


# leave stats
@router.get("/leaves/stats")
async def leave_stats(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(text("""
        SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE status = 'pending') as pending,
        COUNT(*) FILTER (WHERE status = 'approved') as approved,
        COUNT(*) FILTER (WHERE status = 'rejected') as rejected
        FROM leaves
        WHERE employee_id = :user_id
    """), {"user_id": user_id})

    stats = result.mappings().first()

    # null safety
    return {
        "total": stats["total"] or 0,
        "pending": stats["pending"] or 0,
        "approved": stats["approved"] or 0,
        "rejected": stats["rejected"] or 0
    }