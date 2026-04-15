from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

CURRENT_USER_ID = 1


@router.get("/notifications")
async def get_notifications(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT *
        FROM notifications

        WHERE user_id=:user_id

        ORDER BY created_at DESC

    """), {"user_id": CURRENT_USER_ID})

    return result.mappings().all()



@router.get("/notifications/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT COUNT(*) as count

        FROM notifications

        WHERE user_id=:user_id
        AND is_read=false

    """), {"user_id": CURRENT_USER_ID})

    return result.mappings().first()



@router.patch("/notifications/{notification_id}/read")
async def mark_read(notification_id: int,
                    db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        UPDATE notifications

        SET is_read=true

        WHERE notification_id=:id
        AND user_id=:user_id

    """), {
        "id": notification_id,
        "user_id": CURRENT_USER_ID
    })

    await db.commit()

    return {"message": "notification read"}



@router.patch("/notifications/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        UPDATE notifications

        SET is_read=true

        WHERE user_id=:user_id

    """), {"user_id": CURRENT_USER_ID})

    await db.commit()

    return {"message": "all read"}