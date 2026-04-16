from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db, verify_device
from app.schemas.schemas import BulkAttendanceRequest, AttendanceLogResponse
from app.services.attendance_service import (
    process_attendance,
    process_bulk_attendance,
    get_attendance_history
)
from typing import List

router = APIRouter()


# =========================
# MARK ATTENDANCE (REAL-TIME)
# =========================

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

    return {
        "status": "success",
        "user_id": log.user_id,                 # ✅ NEW
        "finger_id": log.finger_id,
        "record_type": log.record_type,
        "user_name": user_name,
        "message": f"Successfully marked {log.record_type}"
    }


# =========================
# OFFLINE SYNC
# =========================

@router.post("/sync-offline")
async def sync_offline_attendance(
    payload: BulkAttendanceRequest,
    device = Depends(verify_device),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = device.tenant_id

    count = await process_bulk_attendance(
        tenant_id,
        device.device_id,
        payload.logs,
        db
    )

    return {
        "status": "success",
        "synced_records": count
    }


# =========================
# HISTORY
# =========================

@router.get("/history", response_model=List[AttendanceLogResponse])
async def attendance_history(
    device = Depends(verify_device),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = device.tenant_id

    return await get_attendance_history(tenant_id, db)