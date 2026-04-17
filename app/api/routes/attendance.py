from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db, verify_device
from app.schemas.schemas import BulkAttendanceRequest, AttendanceLogResponse
from app.services.attendance_service import (
    process_attendance,
    process_bulk_attendance,
    get_attendance_history
)
from app.services.notification_service import create_notification
from typing import List

router = APIRouter()


@router.post("/mark")
async def mark_attendance(
    finger_id: int,
    device = Depends(verify_device),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = device.tenant_id

    log, user_name = await process_attendance(
        tenant_id,
        device.device_id,
        finger_id,
        db
    )
    
    # NOTIFICATION: Notify employee of punch
    if log.user_id:
        punch_time = log.timestamp.strftime("%H:%M")
        await create_notification(
            db, tenant_id, log.user_id,
            f"Attendance {log.record_type}",
            f"You punched {log.record_type} at {punch_time}",
            "attendance"
        )
        
        # NOTIFICATION: Check for late arrival
        if log.record_type == "IN" and log.timestamp.time() > log.timestamp.replace(hour=9, minute=15, second=0).time():
            await create_notification(
                db, tenant_id, log.user_id,
                "Late Arrival",
                f"You arrived late today at {punch_time}",
                "attendance"
            )

    return {
        "status": "success",
        "user_id": log.user_id,
        "finger_id": log.finger_id,
        "record_type": log.record_type,
        "user_name": user_name,
        "message": f"Successfully marked {log.record_type}"
    }


@router.post("/sync-offline")
async def sync_offline_attendance(
    payload: BulkAttendanceRequest,
    device = Depends(verify_device),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = device.tenant_id
    count = await process_bulk_attendance(tenant_id, device.device_id, payload.logs, db)
    return {"status": "success", "synced_records": count}


@router.get("/history", response_model=List[AttendanceLogResponse])
async def attendance_history(
    device = Depends(verify_device),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = device.tenant_id
    return await get_attendance_history(tenant_id, db)