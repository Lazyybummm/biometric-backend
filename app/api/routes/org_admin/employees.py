from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

router = APIRouter()

# =========================
# SCHEMAS
# =========================

class EmployeeCreate(BaseModel):
    name: str
    department_id: int
    finger_id: int | None = None


class EmployeeUpdate(BaseModel):
    name: str
    department_id: int
    finger_id: Optional[int] = None


# =========================
# ROUTES
# =========================

# available fingerprint IDs
@router.get("/employees/available-finger-ids")
async def available_finger_ids(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT generate_series(1,50) as finger_id
        EXCEPT
        SELECT finger_id
        FROM employees
        WHERE tenant_id = :tenant_id
        AND finger_id IS NOT NULL
        ORDER BY finger_id
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# employee statistics
@router.get("/employees/stats")
async def employee_stats(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT
        COUNT(*) as total_employees,
        COUNT(*) FILTER (WHERE is_active = true) as active_employees,
        COUNT(*) FILTER (WHERE is_active = false) as inactive_employees
        FROM employees
        WHERE tenant_id = :tenant_id
    """), {"tenant_id": tenant_id})

    return result.mappings().first()


# find employee by finger id
@router.get("/employees/fingerprint/{finger_id}")
async def employee_by_fingerprint(
    finger_id: int,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT *
        FROM employees
        WHERE tenant_id = :tenant_id
        AND finger_id = :finger_id
    """), {
        "tenant_id": tenant_id,
        "finger_id": finger_id
    })

    return result.mappings().first()


# get all employees
@router.get("/employees")
async def get_employees(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT *
        FROM employees
        WHERE tenant_id = :tenant_id
        ORDER BY employee_id
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# create employee
@router.post("/employees")
async def create_employee(
    data: EmployeeCreate,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        INSERT INTO employees
        (tenant_id, name, department_id, finger_id, is_active)
        VALUES
        (:tenant_id, :name, :department_id, :finger_id, true)
    """), {
        "tenant_id": tenant_id,
        **data.dict()
    })

    await db.commit()

    return {"message": "employee created"}


# update employee
@router.put("/employees/{user_id}")
async def update_employee(
    user_id: int,
    data: EmployeeUpdate,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        UPDATE employees
        SET name = :name,
            department_id = :department_id,
            finger_id = :finger_id
        WHERE employee_id = :user_id
        AND tenant_id = :tenant_id
    """), {
        "user_id": user_id,
        "tenant_id": tenant_id,
        **data.dict()
    })

    await db.commit()

    return {"message": "employee updated"}


# deactivate employee
@router.patch("/employees/{user_id}/deactivate")
async def deactivate_employee(
    user_id: int,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        UPDATE employees
        SET is_active=false,
            finger_id=NULL
        WHERE employee_id=:user_id
        AND tenant_id=:tenant_id
    """), {
        "user_id": user_id,
        "tenant_id": tenant_id
    })

    await db.commit()

    return {"message": "employee deactivated"}


# activate employee
@router.patch("/employees/{user_id}/activate")
async def activate_employee(
    user_id: int,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        UPDATE employees
        SET is_active=true
        WHERE employee_id=:user_id
        AND tenant_id=:tenant_id
    """), {
        "user_id": user_id,
        "tenant_id": tenant_id
    })

    await db.commit()

    return {"message": "employee activated"}


# employee attendance history
@router.get("/employees/{user_id}/attendance")
async def employee_attendance(
    user_id: int,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT
            a.finger_id,
            a.timestamp,
            a.record_type
        FROM attendance_logs a
        JOIN employees e
        ON a.tenant_id = e.tenant_id
        AND a.finger_id = e.finger_id
        WHERE e.employee_id = :user_id
        AND e.tenant_id = :tenant_id
        ORDER BY a.timestamp DESC
    """), {
        "user_id": user_id,
        "tenant_id": tenant_id
    })

    return result.mappings().all()