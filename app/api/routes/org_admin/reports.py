from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

router = APIRouter()


# =========================
# ATTENDANCE REPORT
# =========================

@router.get("/reports/attendance")
async def attendance_report(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT *
        FROM attendance_logs
        WHERE tenant_id = :tenant_id
        ORDER BY timestamp DESC
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# =========================
# LEAVE REPORT
# =========================

@router.get("/reports/leaves")
async def leave_report(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT *
        FROM leaves
        WHERE tenant_id = :tenant_id
        ORDER BY start_date DESC
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# =========================
# EXPORT (PLACEHOLDER)
# =========================

@router.get("/reports/attendance/export")
async def export_attendance_report(
    admin: AdminUser = Depends(get_admin_data)
):
    # future: generate CSV file
    return {
        "message": "export ready",
        "format": "csv"
    }