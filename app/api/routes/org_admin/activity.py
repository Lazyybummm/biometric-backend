from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

router = APIRouter()


@router.get("/activity")
async def activity_log(
    admin: AdminUser = Depends(get_admin_data),   # ✅ FIXED
    db: AsyncSession = Depends(get_db)
):
    # =========================
    # GET TENANT
    # =========================
    tenant_id = admin.tenant_id

    # =========================
    # ACTIVITY QUERY
    # =========================
    query = text("""
        SELECT 
            'attendance_marked' as activity,
            finger_id,
            timestamp as time
        FROM attendance_logs
        WHERE tenant_id = :tenant_id

        UNION ALL

        SELECT
            'leave_requested' as activity,
            employee_id,
            created_at as time
        FROM leaves
        WHERE tenant_id = :tenant_id

        ORDER BY time DESC
        LIMIT 20
    """)

    result = await db.execute(query, {"tenant_id": tenant_id})

    return result.mappings().all()