from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db, verify_tenant, verify_device
from app.schemas.schemas import BulkAttendanceRequest, AttendanceLogResponse
from app.services.attendance_service import process_attendance, process_bulk_attendance, get_attendance_history
from typing import List

router = APIRouter()

@router.post("/mark")
async def mark_attendance(
    finger_id: int,
    tenant_id: int = Depends(verify_tenant),
    device: dict = Depends(verify_device),
    db: AsyncSession = Depends(get_db)
):
    # Unpack the log and the fetched user_name
    log, user_name = await process_attendance(tenant_id, device.device_id, finger_id, db)
    
    # Send the state and user name right back to the hardware
    return {
        "status": "success", 
        "record_type": log.record_type,
        "user_name": user_name,
        "message": f"Successfully marked {log.record_type}"
    }

@router.post("/sync-offline")
async def sync_offline_attendance(
    payload: BulkAttendanceRequest,
    tenant_id: int = Depends(verify_tenant),
    device: dict = Depends(verify_device),
    db: AsyncSession = Depends(get_db)
):
    count = await process_bulk_attendance(tenant_id, device.device_id, payload.logs, db)
    return {"status": "success", "synced_records": count}

@router.get("/history", response_model=List[AttendanceLogResponse])
async def attendance_history(
    tenant_id: int = Depends(verify_tenant),
    db: AsyncSession = Depends(get_db)
):
    return await get_attendance_history(tenant_id, db)