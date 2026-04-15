from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("SELECT * FROM settings LIMIT 1"))

    return result.mappings().first()



@router.put("/settings")
async def update_settings(office_start_time: str,
                          office_end_time: str,
                          late_threshold_minutes: int,
                          db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        UPDATE settings

        SET office_start_time=:office_start_time,
            office_end_time=:office_end_time,
            late_threshold_minutes=:late_threshold_minutes

        WHERE setting_id=1

    """), {
        "office_start_time": office_start_time,
        "office_end_time": office_end_time,
        "late_threshold_minutes": late_threshold_minutes
    })

    await db.commit()

    return {"message": "settings updated"}