from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
import secrets

from app.api.dependencies import get_db, get_admin_data
from app.schemas.schemas import CommandRequest
from app.models.domain import (
    Command,
    AdminUser,
    Device,
    Tenant,
    RoleEnum
)
from app.mqtt.client import mqtt_manager

router = APIRouter()


# =========================
# SCHEMAS
# =========================

class TenantCreate(BaseModel):
    name: str


class DeviceCreate(BaseModel):
    device_id: str
    tenant_id: int


# =========================
# CREATE TENANT
# =========================

@router.post("/tenants")
async def create_tenant(
    data: TenantCreate,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    if admin.role != RoleEnum.SUPER_ADMIN:
        raise HTTPException(403, "Only super admin can create tenants")

    api_key = secrets.token_hex(16)

    tenant = Tenant(
        name=data.name,
        api_key=api_key
    )

    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    return {
        "message": "Tenant created",
        "tenant_id": tenant.id,
        "api_key": api_key
    }


# =========================
# LIST TENANTS
# =========================

@router.get("/tenants")
async def list_tenants(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Tenant))
    tenants = result.scalars().all()

    return tenants


# =========================
# CREATE DEVICE
# =========================

@router.post("/devices")
async def create_device(
    data: DeviceCreate,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    if admin.role != RoleEnum.SUPER_ADMIN:
        raise HTTPException(403, "Only super admin can create devices")

    # Check tenant exists
    result = await db.execute(
        select(Tenant).where(Tenant.id == data.tenant_id)
    )
    tenant = result.scalars().first()

    if not tenant:
        raise HTTPException(404, "Tenant not found")

    # Check device duplicate
    existing = await db.execute(
        select(Device).where(Device.device_id == data.device_id)
    )
    if existing.scalars().first():
        raise HTTPException(400, "Device already exists")

    secret_key = secrets.token_hex(16)

    device = Device(
        tenant_id=data.tenant_id,
        device_id=data.device_id,
        secret_key=secret_key,
        status="offline"
    )

    db.add(device)
    await db.commit()
    await db.refresh(device)

    return {
        "message": "Device created",
        "device_id": device.device_id,
        "secret_key": secret_key
    }


# =========================
# LIST DEVICES
# =========================

@router.get("/devices")
async def list_devices(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Device))
    devices = result.scalars().all()

    return devices


# =========================
# FIRE COMMAND
# =========================

@router.post("/fire-command")
async def fire_command(
    data: CommandRequest,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    # =========================
    # GET DEVICE
    # =========================
    result = await db.execute(
        select(Device).where(Device.device_id == data.device_id)
    )
    device = result.scalars().first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # =========================
    # DETERMINE TENANT
    # =========================
    tenant_id = device.tenant_id

    # =========================
    # SECURITY CHECK
    # =========================
    if admin.role != RoleEnum.SUPER_ADMIN:
        if admin.tenant_id != tenant_id:
            raise HTTPException(
                status_code=403,
                detail="You cannot control devices of another tenant"
            )

    # =========================
    # SAVE COMMAND
    # =========================
    cmd = Command(
        tenant_id=tenant_id,
        device_id=data.device_id,
        command=data.command,
        target_id=data.target_id
    )

    db.add(cmd)
    await db.commit()
    await db.refresh(cmd)

    # =========================
    # SEND VIA MQTT
    # =========================
    mqtt_manager.publish_command(
        tenant_id,
        data.device_id,
        cmd.id,
        data.command,
        data.target_id
    )

    return {
        "message": "Command dispatched",
        "command_id": cmd.id
    }