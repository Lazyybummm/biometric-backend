from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.domain import Tenant, Device, AdminUser

async def verify_admin(access_token: str = Header(alias="access-token"), db: AsyncSession = Depends(get_db)):
    """Verifies the Admin logging into the dashboard."""
    result = await db.execute(select(AdminUser).where(AdminUser.api_token == access_token))
    admin = result.scalars().first()
    
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid Admin Credentials")
    
    return admin

async def verify_tenant(access_token: str = Header(...), db: AsyncSession = Depends(get_db)):
    """Verifies the API key directly against the database (Legacy/Hardware)."""
    result = await db.execute(select(Tenant).where(Tenant.api_key == access_token))
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    return tenant.id

async def verify_device(x_device_id: str = Header(...), x_secret_key: str = Header(...), db: AsyncSession = Depends(get_db)):
    """Verifies hardware device credentials."""
    result = await db.execute(select(Device).where(Device.device_id == x_device_id, Device.secret_key == x_secret_key))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=401, detail="Invalid Device Credentials")
    return device