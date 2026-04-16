from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from datetime import date
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

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
async def get_leaves(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

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
        WHERE l.tenant_id = :tenant_id
        ORDER BY l.start_date DESC
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# approve leave
@router.patch("/leaves/{leave_id}/approve")
async def approve_leave(
    leave_id: int,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        UPDATE leaves
        SET status = 'approved'
        WHERE leave_id = :leave_id
        AND tenant_id = :tenant_id
    """), {
        "leave_id": leave_id,
        "tenant_id": tenant_id
    })

    await db.commit()

    return {"message": "leave approved"}


# reject leave
@router.patch("/leaves/{leave_id}/reject")
async def reject_leave(
    leave_id: int,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        UPDATE leaves
        SET status = 'rejected'
        WHERE leave_id = :leave_id
        AND tenant_id = :tenant_id
    """), {
        "leave_id": leave_id,
        "tenant_id": tenant_id
    })

    await db.commit()

    return {"message": "leave rejected"}


# leave statistics
@router.get("/leaves/stats")
async def leave_stats(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT
        COUNT(*) FILTER (WHERE status = 'pending') as pending,
        COUNT(*) FILTER (WHERE status = 'approved') as approved,
        COUNT(*) FILTER (WHERE status = 'rejected') as rejected
        FROM leaves
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": tenant_id})

    data = result.mappings().first()

    return {
        "pending": data["pending"] or 0,
        "approved": data["approved"] or 0,
        "rejected": data["rejected"] or 0
    }