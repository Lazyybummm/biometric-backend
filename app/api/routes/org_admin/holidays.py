from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from datetime import date
from app.db.session import get_db

router = APIRouter()

# ======================
# SCHEMA
# ======================

class HolidayCreate(BaseModel):
    name: str
    holiday_date: date


class HolidayUpdate(BaseModel):
    name: str
    holiday_date: date


# ======================
# ROUTES
# ======================


# get holidays
@router.get("/holidays")
async def get_holidays(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""
        SELECT *
        FROM holidays
        ORDER BY holiday_date
    """))

    return result.mappings().all()



# create holiday (JSON BODY)
@router.post("/holidays")
async def create_holiday(
        data: HolidayCreate,
        db: AsyncSession = Depends(get_db)
):

    await db.execute(text("""

        INSERT INTO holidays
        (name, holiday_date)

        VALUES
        (:name, :holiday_date)

    """), data.dict())

    await db.commit()

    return {
        "message": "holiday created"
    }



# update holiday (JSON BODY)
@router.put("/holidays/{holiday_id}")
async def update_holiday(
        holiday_id: int,
        data: HolidayUpdate,
        db: AsyncSession = Depends(get_db)
):

    await db.execute(text("""

        UPDATE holidays

        SET name=:name,
            holiday_date=:holiday_date

        WHERE holiday_id=:holiday_id

    """), {
        "holiday_id": holiday_id,
        **data.dict()
    })

    await db.commit()

    return {
        "message": "holiday updated"
    }



# delete holiday
@router.delete("/holidays/{holiday_id}")
async def delete_holiday(
        holiday_id: int,
        db: AsyncSession = Depends(get_db)
):

    await db.execute(text("""
        DELETE FROM holidays
        WHERE holiday_id=:holiday_id
    """), {
        "holiday_id": holiday_id
    })

    await db.commit()

    return {
        "message": "holiday deleted"
    }