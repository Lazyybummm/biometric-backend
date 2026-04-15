from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


@router.get("/devices")
async def get_devices(db: AsyncSession = Depends(get_db)):

    query = text("SELECT * FROM devices")

    result = await db.execute(query)

    return result.mappings().all()



@router.get("/devices/{device_id}")
async def device_detail(device_id: str,
                        db: AsyncSession = Depends(get_db)):

    query = text("""

        SELECT *
        FROM devices
        WHERE device_id = :device_id

    """)

    result = await db.execute(query, {"device_id": device_id})

    return result.mappings().first()



@router.get("/devices/status")
async def device_status(db: AsyncSession = Depends(get_db)):

    query = text("""

        SELECT

        COUNT(*) FILTER (WHERE is_active = true) as online,

        COUNT(*) FILTER (WHERE is_active = false) as offline

        FROM devices

    """)

    result = await db.execute(query)

    return result.mappings().first()