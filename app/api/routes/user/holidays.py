from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


@router.get("/holidays")
async def get_holidays(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT *
        FROM holidays
        ORDER BY holiday_date

    """))

    return result.mappings().all()



@router.get("/holidays/upcoming")
async def upcoming_holiday(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT *
        FROM holidays

        WHERE holiday_date >= CURRENT_DATE

        ORDER BY holiday_date
        LIMIT 1

    """))

    return result.mappings().first()