from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


@router.get("/notifications")
async def get_notifications(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT *
        FROM notifications
        ORDER BY created_at DESC

    """))

    return result.mappings().all()



@router.get("/notifications/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT COUNT(*) as count
        FROM notifications
        WHERE is_read=false

    """))

    return result.mappings().first()



@router.patch("/notifications/{notification_id}/read")
async def mark_read(notification_id: int,
                    db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        UPDATE notifications
        SET is_read=true
        WHERE notification_id=:notification_id

    """), {"notification_id": notification_id})

    await db.commit()

    return {"message": "notification read"}



@router.patch("/notifications/read-all")
async def read_all(db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        UPDATE notifications
        SET is_read=true

    """))

    await db.commit()

    return {"message": "all notifications read"}