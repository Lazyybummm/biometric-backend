from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from datetime import date
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

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
async def get_holidays(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT *
        FROM holidays
        WHERE tenant_id = :tenant_id
        ORDER BY holiday_date
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# create holiday
@router.post("/holidays")
async def create_holiday(
    data: HolidayCreate,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        INSERT INTO holidays
        (tenant_id, name, holiday_date)
        VALUES
        (:tenant_id, :name, :holiday_date)
    """), {
        "tenant_id": tenant_id,
        **data.dict()
    })

    await db.commit()

    return {"message": "holiday created"}


# update holiday
@router.put("/holidays/{holiday_id}")
async def update_holiday(
    holiday_id: int,
    data: HolidayUpdate,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        UPDATE holidays
        SET name = :name,
            holiday_date = :holiday_date
        WHERE holiday_id = :holiday_id
        AND tenant_id = :tenant_id
    """), {
        "holiday_id": holiday_id,
        "tenant_id": tenant_id,
        **data.dict()
    })

    await db.commit()

    return {"message": "holiday updated"}


# delete holiday
@router.delete("/holidays/{holiday_id}")
async def delete_holiday(
    holiday_id: int,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        DELETE FROM holidays
        WHERE holiday_id = :holiday_id
        AND tenant_id = :tenant_id
    """), {
        "holiday_id": holiday_id,
        "tenant_id": tenant_id
    })

    await db.commit()

    return {"message": "holiday deleted"}