from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from pydantic import BaseModel
from app.db.session import get_db
from app.api.dependencies import verify_tenant_api_key
from app.models.domain import Tenant, Device, Command
from app.mqtt.client import mqtt_manager

router = APIRouter()


class FireCommandRequest(BaseModel):
    device_id: str
    command: str
    target_id: int = None


@router.get("/devices")
async def list_devices(
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: List all devices in organization"""
    
    result = await db.execute(
        select(Device).where(Device.tenant_id == tenant.id).order_by(Device.device_id)
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
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Get device details"""
    
    result = await db.execute(
        select(Device).where(
            Device.device_id == device_id,
            Device.tenant_id == tenant.id
        )
    )
    device = result.scalars().first()
    
    if not device:
        raise HTTPException(404, "Device not found")
    
    commands = await db.execute(text("""
        SELECT id, command, target_id, status, created_at
        FROM commands
        WHERE device_id = :device_id
        AND tenant_id = :tenant_id
        ORDER BY created_at DESC
        LIMIT 20
    """), {
        "device_id": device_id,
        "tenant_id": tenant.id
    })
    
    return {
        "device_id": device.device_id,
        "status": device.status,
        "last_seen": device.last_seen,
        "recent_commands": commands.mappings().all()
    }


@router.get("/devices/status")
async def devices_status(
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Get devices status summary"""
    
    result = await db.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'online') as online,
            COUNT(*) FILTER (WHERE status != 'online') as offline
        FROM devices
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": tenant.id})
    
    return result.mappings().first()


@router.post("/devices/fire-command")
async def fire_device_command(
    data: FireCommandRequest,
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Send command to device"""
    
    result = await db.execute(
        select(Device).where(
            Device.device_id == data.device_id,
            Device.tenant_id == tenant.id
        )
    )
    device = result.scalars().first()
    
    if not device:
        raise HTTPException(404, "Device not found")
    
    cmd = Command(
        tenant_id=tenant.id,
        device_id=data.device_id,
        command=data.command,
        target_id=data.target_id
    )
    
    db.add(cmd)
    await db.commit()
    await db.refresh(cmd)
    
    mqtt_manager.publish_command(
        tenant.id,
        data.device_id,
        cmd.id,
        data.command,
        data.target_id
    )
    
    return {
        "message": "Command dispatched",
        "command_id": cmd.id
    }