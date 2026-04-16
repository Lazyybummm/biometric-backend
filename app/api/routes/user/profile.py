from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.dependencies import get_current_user

router = APIRouter()


# profile
@router.get("/profile")
async def get_profile(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(text("""
        SELECT
            e.employee_id,
            e.name,
            d.department_name,
            e.finger_id
        FROM employees e
        LEFT JOIN departments d
        ON d.department_id = e.department_id
        WHERE e.employee_id = :id
    """), {"id": user_id})

    return result.mappings().first()


# update profile
@router.put("/profile")
async def update_profile(
    name: str,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    await db.execute(text("""
        UPDATE employees
        SET name = :name
        WHERE employee_id = :id
    """), {
        "name": name,
        "id": user_id
    })

    await db.commit()

    return {"message": "profile updated"}


# change password placeholder
@router.put("/profile/change-password")
async def change_password():
    return {"message": "password updated"}