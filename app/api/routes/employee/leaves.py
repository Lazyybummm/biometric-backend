from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from datetime import date
from typing import Optional
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.domain import User
from app.services.notification_service import create_notification, notify_org_admins

router = APIRouter()


class LeaveApplyRequest(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    reason: Optional[str] = None


# =========================
# SPECIFIC ROUTES FIRST
# =========================

@router.get("/leaves/balance")
async def leave_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get leave balance"""
    result = await db.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE leave_type = 'sick' AND status IN ('approved', 'approved_by_dept')) as sick_taken,
            COUNT(*) FILTER (WHERE leave_type = 'casual' AND status IN ('approved', 'approved_by_dept')) as casual_taken,
            COUNT(*) FILTER (WHERE leave_type = 'earned' AND status IN ('approved', 'approved_by_dept')) as earned_taken
        FROM leaves
        WHERE employee_id = :user_id
        AND EXTRACT(YEAR FROM start_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    """), {"user_id": current_user.id})
    
    taken = result.mappings().first()
    
    return {
        "sick": {"total": 12, "taken": taken["sick_taken"] or 0, "remaining": 12 - (taken["sick_taken"] or 0)},
        "casual": {"total": 12, "taken": taken["casual_taken"] or 0, "remaining": 12 - (taken["casual_taken"] or 0)},
        "earned": {"total": 15, "taken": taken["earned_taken"] or 0, "remaining": 15 - (taken["earned_taken"] or 0)}
    }


@router.get("/leaves/stats")
async def leave_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get leave statistics"""
    result = await db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'approved_by_dept') as dept_approved,
            COUNT(*) FILTER (WHERE status = 'approved') as approved,
            COUNT(*) FILTER (WHERE status = 'rejected') as rejected,
            COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled
        FROM leaves
        WHERE employee_id = :user_id
    """), {"user_id": current_user.id})
    
    stats = result.mappings().first()
    
    return {
        "total": stats["total"] or 0,
        "pending": stats["pending"] or 0,
        "dept_approved": stats["dept_approved"] or 0,
        "approved": stats["approved"] or 0,
        "rejected": stats["rejected"] or 0,
        "cancelled": stats["cancelled"] or 0
    }


# =========================
# GENERIC ROUTES LAST
# =========================

@router.get("/leaves")
async def get_leaves(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get own leave requests"""
    result = await db.execute(text("""
        SELECT *
        FROM leaves
        WHERE employee_id = :user_id
        ORDER BY created_at DESC
    """), {"user_id": current_user.id})
    return result.mappings().all()


@router.post("/leaves")
async def apply_leave(
    data: LeaveApplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Apply for leave"""
    
    # Check for overlapping leaves
    overlap = await db.execute(text("""
        SELECT leave_id FROM leaves
        WHERE employee_id = :user_id
        AND status NOT IN ('rejected', 'cancelled')
        AND (
            (:start_date BETWEEN start_date AND end_date)
            OR (:end_date BETWEEN start_date AND end_date)
            OR (start_date BETWEEN :start_date AND :end_date)
        )
    """), {
        "user_id": current_user.id,
        "start_date": data.start_date,
        "end_date": data.end_date
    })
    
    if overlap.scalar():
        raise HTTPException(400, "Leave request overlaps with existing leave")
    
    await db.execute(text("""
        INSERT INTO leaves (tenant_id, employee_id, leave_type, start_date, end_date, reason, status)
        VALUES (:tenant_id, :employee_id, :leave_type, :start_date, :end_date, :reason, 'pending')
    """), {
        "tenant_id": current_user.tenant_id,
        "employee_id": current_user.id,
        "leave_type": data.leave_type,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "reason": data.reason
    })
    await db.commit()
    
    # NOTIFICATION: Notify employee
    try:
        await create_notification(
            db, current_user.tenant_id, current_user.id,
            "Leave Request Submitted",
            f"Your {data.leave_type} leave request from {data.start_date} to {data.end_date} has been submitted for approval",
            "leave"
        )
        await db.commit()
    except Exception as e:
        print(f"Failed to create employee notification: {e}")
    
    # NOTIFICATION: Notify Org Admins in this department
    try:
        await notify_org_admins(
            db, current_user.tenant_id, current_user.dept_id,
            "New Leave Request",
            f"{current_user.name} ({current_user.employee_code}) requested {data.leave_type} leave from {data.start_date} to {data.end_date}",
            "leave"
        )
        await db.commit()
    except Exception as e:
        print(f"Failed to create org admin notification: {e}")
    
    return {"message": "Leave applied successfully"}


@router.get("/leaves/{leave_id}")
async def leave_detail(
    leave_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get specific leave request"""
    result = await db.execute(text("""
        SELECT * FROM leaves
        WHERE leave_id = :leave_id AND employee_id = :user_id
    """), {"leave_id": leave_id, "user_id": current_user.id})
    
    leave = result.mappings().first()
    if not leave:
        raise HTTPException(404, "Leave request not found")
    return leave


@router.patch("/leaves/{leave_id}/cancel")
async def cancel_leave(
    leave_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Cancel leave request"""
    
    leave_info = await db.execute(text("""
        SELECT leave_type, start_date, end_date FROM leaves
        WHERE leave_id = :leave_id AND employee_id = :user_id
    """), {"leave_id": leave_id, "user_id": current_user.id})
    info = leave_info.mappings().first()
    
    result = await db.execute(text("""
        UPDATE leaves SET status = 'cancelled'
        WHERE leave_id = :leave_id AND employee_id = :user_id AND status = 'pending'
    """), {"leave_id": leave_id, "user_id": current_user.id})
    
    if result.rowcount == 0:
        raise HTTPException(404, "Leave request not found or cannot be cancelled")
    
    await db.commit()
    
    return {"message": "Leave cancelled"}