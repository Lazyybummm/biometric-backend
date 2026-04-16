from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db, get_admin_data
from app.schemas.schemas import UserEnrollRequest, UserDeleteRequest
from app.services.user_service import enroll_user, delete_user
from app.models.domain import AdminUser, RoleEnum

router = APIRouter()


# =========================
# ENROLL USER
# =========================

@router.post("/enroll")
async def register_user(
    data: UserEnrollRequest,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    # =========================
    # TENANT LOGIC
    # =========================

    target_tenant_id = admin.tenant_id

    # Super Admin override
    if admin.role == RoleEnum.SUPER_ADMIN:
        if not data.target_tenant_id:
            raise HTTPException(
                status_code=400,
                detail="Super Admins must specify a target_tenant_id"
            )
        target_tenant_id = data.target_tenant_id

    elif not target_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant Admin is not assigned to an organization"
        )

    # =========================
    # ENROLL USER
    # =========================

    user = await enroll_user(
        target_tenant_id,
        data.finger_id,
        data.name,
        data.employee_code,
        db
    )

    return {
        "status": "success",
        "message": "User enrolled locally. Fire MQTT command to sync hardware.",
        "data": {
            "id": user.id,
            "name": user.name,
            "employee_code": user.employee_code,
            "finger_id": user.finger_id,
            "tenant_id": user.tenant_id
        }
    }


# =========================
# DELETE USER
# =========================

@router.post("/delete")  # 🔁 keep for now (can upgrade later)
async def remove_user(
    data: UserDeleteRequest,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    # =========================
    # TENANT LOGIC
    # =========================

    target_tenant_id = admin.tenant_id

    if admin.role == RoleEnum.SUPER_ADMIN:
        if not data.target_tenant_id:
            raise HTTPException(
                status_code=400,
                detail="Super Admins must specify a target_tenant_id"
            )
        target_tenant_id = data.target_tenant_id

    elif not target_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant Admin is not assigned to an organization"
        )

    # =========================
    # DELETE USER
    # =========================

    result = await delete_user(
        target_tenant_id,
        data.finger_id,
        db
    )

    return {
        "status": "success",
        "message": "User deleted locally. Fire MQTT command to sync hardware.",
        "data": result
    }