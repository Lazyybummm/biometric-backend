from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from app.db.session import get_db

router = APIRouter()


# -------- schemas --------

class DepartmentCreate(BaseModel):
    department_name: str


class DepartmentUpdate(BaseModel):
    department_name: str


# -------- routes --------

# get all departments
@router.get("/departments")
async def get_departments(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT *
        FROM departments
        ORDER BY department_name

    """))

    return result.mappings().all()



# create department
@router.post("/departments")
async def create_department(data: DepartmentCreate,
                            db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        INSERT INTO departments (department_name)

        VALUES (:department_name)

    """), data.dict())

    await db.commit()

    return {
        "message": "department created"
    }



# update department
@router.put("/departments/{department_id}")
async def update_department(department_id: int,
                            data: DepartmentUpdate,
                            db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        UPDATE departments

        SET department_name = :department_name

        WHERE department_id = :department_id

    """), {
        "department_id": department_id,
        **data.dict()
    })

    await db.commit()

    return {
        "message": "department updated"
    }



# delete department
@router.delete("/departments/{department_id}")
async def delete_department(department_id: int,
                            db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        DELETE FROM departments

        WHERE department_id = :department_id

    """), {
        "department_id": department_id
    })

    await db.commit()

    return {
        "message": "department deleted"
    }