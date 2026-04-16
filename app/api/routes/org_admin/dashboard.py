from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    # =========================
    # GET TENANT
    # =========================
    tenant_id = admin.tenant_id

    # =========================
    # EMPLOYEE STATS
    # =========================
    emp_stats = await db.execute(text("""
        SELECT
        COUNT(*) as total_employees,
        COUNT(*) FILTER (WHERE is_active = true) as active_employees,
        COUNT(*) FILTER (WHERE is_active = false) as inactive_employees
        FROM employees
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": tenant_id})

    emp_data = emp_stats.mappings().first()

    # =========================
    # TODAY ATTENDANCE
    # =========================
    att_stats = await db.execute(text("""
        SELECT
        COUNT(DISTINCT finger_id)
        FILTER (WHERE DATE(timestamp) = CURRENT_DATE)
        as present_today
        FROM attendance_logs
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": tenant_id})

    present_data = att_stats.mappings().first()

    # =========================
    # CALCULATIONS
    # =========================
    total_employees = emp_data["total_employees"] or 0
    active_employees = emp_data["active_employees"] or 0
    inactive_employees = emp_data["inactive_employees"] or 0

    present_today = present_data["present_today"] or 0
    absent_today = active_employees - present_today

    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "inactive_employees": inactive_employees,
        "present_today": present_today,
        "absent_today": absent_today
    }