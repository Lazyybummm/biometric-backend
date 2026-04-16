from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.dependencies import get_current_user

router = APIRouter()


# get all notifications
@router.get("/notifications")
async def get_notifications(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(text("""
        SELECT *
        FROM notifications
        WHERE user_id = :user_id
        ORDER BY created_at DESC
    """), {"user_id": user_id})

    return result.mappings().all()


# unread count
@router.get("/notifications/unread-count")
async def unread_count(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(text("""
        SELECT COUNT(*) as count
        FROM notifications
        WHERE user_id = :user_id
        AND is_read = false
    """), {"user_id": user_id})

    data = result.mappings().first()

    return {
        "count": data["count"] or 0
    }


# mark single notification as read
@router.patch("/notifications/{notification_id}/read")
async def mark_read(
    notification_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    await db.execute(text("""
        UPDATE notifications
        SET is_read = true
        WHERE notification_id = :notification_id
        AND user_id = :user_id
    """), {
        "notification_id": notification_id,
        "user_id": user_id
    })

    await db.commit()

    return {"message": "notification read"}


# mark all notifications as read
@router.patch("/notifications/read-all")
async def mark_all_read(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    await db.execute(text("""
        UPDATE notifications
        SET is_read = true
        WHERE user_id = :user_id
    """), {"user_id": user_id})

    await db.commit()

    return {"message": "all notifications marked as read"}