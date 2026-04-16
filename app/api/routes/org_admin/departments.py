from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from app.db.session import get_db
from app.api.dependencies import get_admin_data
from app.models.domain import AdminUser

router = APIRouter()


# -------- schemas --------

class DepartmentCreate(BaseModel):
    department_name: str


class DepartmentUpdate(BaseModel):
    department_name: str


# -------- routes --------

# get all departments
@router.get("/departments")
async def get_departments(
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    result = await db.execute(text("""
        SELECT *
        FROM departments
        WHERE tenant_id = :tenant_id
        ORDER BY department_name
    """), {"tenant_id": tenant_id})

    return result.mappings().all()


# create department
@router.post("/departments")
async def create_department(
    data: DepartmentCreate,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        INSERT INTO departments (tenant_id, department_name)
        VALUES (:tenant_id, :department_name)
    """), {
        "tenant_id": tenant_id,
        "department_name": data.department_name
    })

    await db.commit()

    return {"message": "department created"}


# update department
@router.put("/departments/{department_id}")
async def update_department(
    department_id: int,
    data: DepartmentUpdate,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        UPDATE departments
        SET department_name = :department_name
        WHERE department_id = :department_id
        AND tenant_id = :tenant_id
    """), {
        "department_id": department_id,
        "tenant_id": tenant_id,
        "department_name": data.department_name
    })

    await db.commit()

    return {"message": "department updated"}


# delete department
@router.delete("/departments/{department_id}")
async def delete_department(
    department_id: int,
    admin: AdminUser = Depends(get_admin_data),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = admin.tenant_id

    await db.execute(text("""
        DELETE FROM departments
        WHERE department_id = :department_id
        AND tenant_id = :tenant_id
    """), {
        "department_id": department_id,
        "tenant_id": tenant_id
    })

    await db.commit()

    return {"message": "department deleted"}