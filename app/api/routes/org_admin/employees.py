from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from app.db.session import get_db

router = APIRouter()

# =========================
# SCHEMAS
# =========================

class EmployeeCreate(BaseModel):
    name: str
    department_id: int
    fingerprint_id: int | None = None


from typing import Optional

class EmployeeUpdate(BaseModel):
    name: str
    department_id: int
    fingerprint_id: Optional[int] = None

# =========================
# STATIC ROUTES FIRST
# =========================


# available fingerprint IDs
@router.get("/employees/available-finger-ids")
async def available_finger_ids(db: AsyncSession = Depends(get_db)):

    query = text("""
        SELECT generate_series(1,50) as fingerprint_id
        EXCEPT
        SELECT fingerprint_id
        FROM employees
        WHERE fingerprint_id IS NOT NULL
        ORDER BY fingerprint_id
    """)

    result = await db.execute(query)

    return result.mappings().all()



# employee statistics
@router.get("/employees/stats")
async def employee_stats(db: AsyncSession = Depends(get_db)):

    query = text("""
        SELECT
        COUNT(*) as total_employees,
        COUNT(*) FILTER (WHERE is_active = true) as active_employees,
        COUNT(*) FILTER (WHERE is_active = false) as inactive_employees
        FROM employees
    """)

    result = await db.execute(query)

    return result.mappings().first()



# find employee by fingerprint id
@router.get("/employees/fingerprint/{fingerprint_id}")
async def employee_by_fingerprint(fingerprint_id: int,
                                  db: AsyncSession = Depends(get_db)):

    query = text("""
        SELECT *
        FROM employees
        WHERE fingerprint_id = :fingerprint_id
    """)

    result = await db.execute(query,
                              {"fingerprint_id": fingerprint_id})

    return result.mappings().first()



# =========================
# NORMAL ROUTES
# =========================


# get all employees
@router.get("/employees")
async def get_employees(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""
        SELECT *
        FROM employees
        ORDER BY employee_id
    """))

    return result.mappings().all()



# create employee
@router.post("/employees")
async def create_employee(data: EmployeeCreate,
                          db: AsyncSession = Depends(get_db)):

    await db.execute(text("""
        INSERT INTO employees
        (name, department_id, fingerprint_id)
        VALUES
        (:name, :department_id, :fingerprint_id)
    """), data.dict())

    await db.commit()

    return {"message": "employee created"}



# update employee
@router.put("/employees/{user_id}")
async def update_employee(user_id: int,
                          data: EmployeeUpdate,
                          db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        UPDATE employees

        SET name = :name,
            department_id = :department_id,
            fingerprint_id = :fingerprint_id

        WHERE employee_id = :user_id

    """), {
        "user_id": user_id,
        **data.dict()
    })

    await db.commit()

    return {
        "message": "employee updated"
    }



# deactivate employee
@router.patch("/employees/{user_id}/deactivate")
async def deactivate_employee(user_id: int,
                              db: AsyncSession = Depends(get_db)):

    await db.execute(text("""
        UPDATE employees
        SET is_active=false,
            fingerprint_id=NULL
        WHERE employee_id=:user_id
    """), {"user_id": user_id})

    await db.commit()

    return {"message": "employee deactivated"}



# activate employee
@router.patch("/employees/{user_id}/activate")
async def activate_employee(user_id: int,
                            db: AsyncSession = Depends(get_db)):

    await db.execute(text("""
        UPDATE employees
        SET is_active=true
        WHERE employee_id=:user_id
    """), {"user_id": user_id})

    await db.commit()

    return {"message": "employee activated"}



# employee attendance history
@router.get("/employees/{user_id}/attendance")
async def employee_attendance(user_id: int,
                              db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""
        SELECT *
        FROM attendance_logs
        WHERE employee_id=:user_id
        ORDER BY check_time DESC
    """), {"user_id": user_id})

    return result.mappings().all()