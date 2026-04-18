from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from pydantic import BaseModel
from app.db.session import get_db
from app.api.dependencies import get_current_user, require_role
from app.models.domain import User, Device, Command
from app.mqtt.client import mqtt_manager

router = APIRouter()


# =========================
# SCHEMAS
# =========================

class FireCommandRequest(BaseModel):
    device_id: str
    command: str  # 'enroll' or 'delete'
    target_id: int  # finger_id


# =========================
# ROUTES
# =========================

@router.get("/devices")
async def list_devices(
    current_user: User = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Org Admin: List all devices in their tenant"""
    
    result = await db.execute(
        select(Device)
        .where(Device.tenant_id == current_user.tenant_id)
        .order_by(Device.device_id)
    )
    devices = result.scalars().all()
    
    return [
        {
            "device_id": d.device_id,
            "status": d.status,
            "last_seen": d.last_seen
        }
        for d in devices
    ]


@router.get("/devices/{device_id}")
async def get_device(
    device_id: str,
    current_user: User = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Org Admin: Get device details"""
    
    result = await db.execute(
        select(Device).where(
            Device.device_id == device_id,
            Device.tenant_id == current_user.tenant_id
        )
    )
    device = result.scalars().first()
    
    if not device:
        raise HTTPException(404, "Device not found")
    
    # Get recent commands for this device
    commands = await db.execute(text("""
        SELECT id, command, target_id, status, created_at
        FROM commands
        WHERE device_id = :device_id
        AND tenant_id = :tenant_id
        ORDER BY created_at DESC
        LIMIT 20
    """), {
        "device_id": device_id,
        "tenant_id": current_user.tenant_id
    })
    
    return {
        "device_id": device.device_id,
        "status": device.status,
        "last_seen": device.last_seen,
        "recent_commands": commands.mappings().all()
    }


@router.get("/devices/status")
async def devices_status(
    current_user: User = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Org Admin: Get devices status summary"""
    
    result = await db.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'online') as online,
            COUNT(*) FILTER (WHERE status != 'online') as offline
        FROM devices
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": current_user.tenant_id})
    
    return result.mappings().first()


@router.post("/devices/fire-command")
async def fire_device_command(
    data: FireCommandRequest,
    current_user: User = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Org Admin: Send command to device (enroll/delete fingerprint)
    
    This allows Org Admin to directly enroll fingerprints without
    going through Tenant Manager.
    """
    
    # Verify device belongs to this tenant
    result = await db.execute(
        select(Device).where(
            Device.device_id == data.device_id,
            Device.tenant_id == current_user.tenant_id
        )
    )
    device = result.scalars().first()
    
    if not device:
        raise HTTPException(404, "Device not found in your organization")
    
    # Validate command type
    if data.command not in ["enroll", "delete"]:
        raise HTTPException(400, "Command must be 'enroll' or 'delete'")
    
    # Validate target_id (finger_id) range
    if data.target_id < 1 or data.target_id > 127:
        raise HTTPException(400, "Finger ID must be between 1 and 127")
    
    # For enroll command, verify the finger_id is assigned to an employee
    if data.command == "enroll":
        from app.models.domain import User
        emp_result = await db.execute(
            select(User).where(
                User.tenant_id == current_user.tenant_id,
                User.finger_id == data.target_id,
                User.is_active == True
            )
        )
        employee = emp_result.scalars().first()
        if not employee:
            raise HTTPException(400, f"No active employee assigned to finger ID {data.target_id}")
    
    # Create command record
    cmd = Command(
        tenant_id=current_user.tenant_id,
        device_id=data.device_id,
        command=data.command,
        target_id=data.target_id
    )
    
    db.add(cmd)
    await db.commit()
    await db.refresh(cmd)
    
    # Publish MQTT command
    mqtt_manager.publish_command(
        current_user.tenant_id,
        data.device_id,
        cmd.id,
        data.command,
        data.target_id
    )
    
    return {
        "message": f"Command '{data.command}' dispatched successfully",
        "command_id": cmd.id,
        "device_id": data.device_id,
        "target_id": data.target_id
    }