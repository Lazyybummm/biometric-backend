from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.future import select
from pydantic import BaseModel
from app.db.session import get_db
from app.api.dependencies import get_current_user, require_role
from app.models.domain import User

router = APIRouter()


# =========================
# SCHEMAS
# =========================

class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    type: str  # leave, attendance, employee, system


# =========================
# SPECIFIC ROUTES FIRST
# =========================

@router.get("/notifications/unread-count")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread notifications"""
    result = await db.execute(text("""
        SELECT COUNT(*) as count
        FROM notifications
        WHERE user_id = :user_id
        AND is_read = false
    """), {"user_id": current_user.id})
    
    data = result.mappings().first()
    return {"count": data["count"] or 0}


@router.patch("/notifications/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read"""
    await db.execute(text("""
        UPDATE notifications
        SET is_read = true
        WHERE user_id = :user_id
    """), {"user_id": current_user.id})
    await db.commit()
    return {"message": "All notifications marked as read"}


@router.patch("/notifications/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a single notification as read"""
    result = await db.execute(text("""
        UPDATE notifications
        SET is_read = true
        WHERE notification_id = :notification_id
        AND user_id = :user_id
    """), {
        "notification_id": notification_id,
        "user_id": current_user.id
    })
    
    if result.rowcount == 0:
        raise HTTPException(404, "Notification not found")
    
    await db.commit()
    return {"message": "Notification marked as read"}


# =========================
# GENERIC ROUTES LAST
# =========================

@router.get("/notifications")
async def get_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications - Org Admins see department notifications too"""
    
    if current_user.role == "org_admin":
        # Org Admin: See own notifications + department employee notifications
        query = text("""
            SELECT n.*, u.name as employee_name, u.employee_code
            FROM notifications n
            LEFT JOIN users u ON n.user_id = u.id
            WHERE n.tenant_id = :tenant_id
            AND (
                n.user_id = :user_id
                OR u.dept_id = :dept_id
            )
            ORDER BY n.created_at DESC
            LIMIT 100
        """)
        result = await db.execute(query, {
            "tenant_id": current_user.tenant_id,
            "user_id": current_user.id,
            "dept_id": current_user.dept_id
        })
    else:
        # Employee: Only see own notifications
        query = text("""
            SELECT *
            FROM notifications
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 50
        """)
        result = await db.execute(query, {"user_id": current_user.id})
    
    return result.mappings().all()


@router.post("/notifications")
async def create_notification_route(  # ← RENAMED
    data: NotificationCreate,
    current_user: User = Depends(require_role("org_admin", "super_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Create a notification for a user"""
    
    # Verify user belongs to same tenant
    user_check = await db.execute(
        select(User).where(
            User.id == data.user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    if not user_check.scalars().first():
        raise HTTPException(404, "User not found in your organization")
    
    await db.execute(text("""
        INSERT INTO notifications (tenant_id, user_id, title, message, type, is_read)
        VALUES (:tenant_id, :user_id, :title, :message, :type, false)
    """), {
        "tenant_id": current_user.tenant_id,
        "user_id": data.user_id,
        "title": data.title,
        "message": data.message,
        "type": data.type
    })
    await db.commit()
    
    return {"message": "Notification created successfully"}