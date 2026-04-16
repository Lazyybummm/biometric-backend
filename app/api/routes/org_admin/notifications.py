from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

router = APIRouter()


# =========================
# ROUTES
# =========================

# get notifications
@router.get("/notifications")
async def get_notifications(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT *
        FROM notifications
        WHERE tenant_id = :tenant_id
        ORDER BY created_at DESC
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# unread count
@router.get("/notifications/unread-count")
async def unread_count(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT COUNT(*) as count
        FROM notifications
        WHERE tenant_id = :tenant_id
        AND is_read = false
    """), {"tenant_id": tenant_id})

    data = result.mappings().first()

    return {"count": data["count"] or 0}


# mark single notification as read
@router.patch("/notifications/{notification_id}/read")
async def mark_read(
    notification_id: int,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        UPDATE notifications
        SET is_read = true
        WHERE notification_id = :notification_id
        AND tenant_id = :tenant_id
    """), {
        "notification_id": notification_id,
        "tenant_id": tenant_id
    })

    await db.commit()

    return {"message": "notification read"}


# mark all as read
@router.patch("/notifications/read-all")
async def read_all(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        UPDATE notifications
        SET is_read = true
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": tenant_id})

    await db.commit()

    return {"message": "all notifications read"}