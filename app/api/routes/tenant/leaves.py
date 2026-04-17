from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from app.db.session import get_db
from app.api.dependencies import verify_tenant_api_key
from app.models.domain import Tenant
from app.services.notification_service import create_notification

router = APIRouter()


@router.get("/leaves")
async def list_leave_requests(
    status: Optional[str] = None,
    dept_id: Optional[int] = None,
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: List all leave requests"""
    query = """
        SELECT l.leave_id, l.employee_id, u.name as employee_name, u.employee_code,
            d.department_name, l.leave_type, l.start_date, l.end_date, l.reason, l.status, l.created_at
        FROM leaves l
        JOIN users u ON l.employee_id = u.id
        LEFT JOIN departments d ON u.dept_id = d.department_id
        WHERE l.tenant_id = :tenant_id
    """
    params = {"tenant_id": tenant.id}
    
    if status:
        query += " AND l.status = :status"
        params["status"] = status
    if dept_id:
        query += " AND u.dept_id = :dept_id"
        params["dept_id"] = dept_id
    
    query += " ORDER BY l.created_at DESC"
    
    result = await db.execute(text(query), params)
    return result.mappings().all()


@router.get("/leaves/pending")
async def pending_leaves(
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Get pending leave requests count"""
    result = await db.execute(text("""
        SELECT COUNT(*) as pending_count
        FROM leaves
        WHERE tenant_id = :tenant_id AND status = 'pending'
    """), {"tenant_id": tenant.id})
    return result.mappings().first()


@router.patch("/leaves/{leave_id}/approve")
async def approve_leave(
    leave_id: int,
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Approve a leave request (final approval)"""
    
    # Get leave details
    leave_info = await db.execute(text("""
        SELECT l.employee_id, l.leave_type, l.start_date, l.end_date
        FROM leaves l
        WHERE l.leave_id = :leave_id AND l.tenant_id = :tenant_id
    """), {"leave_id": leave_id, "tenant_id": tenant.id})
    info = leave_info.mappings().first()
    
    if not info:
        raise HTTPException(404, "Leave request not found")
    
    result = await db.execute(text("""
        UPDATE leaves
        SET status = 'approved', approved_at = NOW(), approved_by = :tenant_id
        WHERE leave_id = :leave_id AND tenant_id = :tenant_id
        AND status IN ('pending', 'approved_by_dept')
    """), {"leave_id": leave_id, "tenant_id": tenant.id})
    
    if result.rowcount == 0:
        raise HTTPException(404, "Leave request not found or cannot be approved")
    
    await db.commit()
    
    # NOTIFICATION: Notify employee
    await create_notification(
        db, tenant.id, info["employee_id"],
        "Leave Fully Approved",
        f"Your {info['leave_type']} leave from {info['start_date']} to {info['end_date']} has been fully approved",
        "leave"
    )
    
    return {"message": "Leave approved successfully"}


@router.patch("/leaves/{leave_id}/reject")
async def reject_leave(
    leave_id: int,
    reason: str = None,
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Reject a leave request"""
    
    # Get leave details
    leave_info = await db.execute(text("""
        SELECT l.employee_id, l.leave_type, l.start_date, l.end_date
        FROM leaves l
        WHERE l.leave_id = :leave_id AND l.tenant_id = :tenant_id
    """), {"leave_id": leave_id, "tenant_id": tenant.id})
    info = leave_info.mappings().first()
    
    result = await db.execute(text("""
        UPDATE leaves
        SET status = 'rejected', rejection_reason = :reason, rejected_at = NOW()
        WHERE leave_id = :leave_id AND tenant_id = :tenant_id
    """), {"leave_id": leave_id, "tenant_id": tenant.id, "reason": reason})
    
    if result.rowcount == 0:
        raise HTTPException(404, "Leave request not found")
    
    await db.commit()
    
    # NOTIFICATION: Notify employee
    message = f"Your {info['leave_type']} leave from {info['start_date']} to {info['end_date']} was rejected"
    if reason:
        message += f". Reason: {reason}"
    
    await create_notification(
        db, tenant.id, info["employee_id"],
        "Leave Rejected",
        message,
        "leave"
    )
    
    return {"message": "Leave rejected"}


@router.get("/leaves/stats")
async def leave_statistics(
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Get leave statistics"""
    result = await db.execute(text("""
        SELECT 
            COUNT(*) as total_requests,
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'approved_by_dept') as dept_approved,
            COUNT(*) FILTER (WHERE status = 'approved') as approved,
            COUNT(*) FILTER (WHERE status = 'rejected') as rejected,
            COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled
        FROM leaves
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": tenant.id})
    return result.mappings().first()