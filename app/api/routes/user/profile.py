from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

CURRENT_USER_ID = 1


# profile
@router.get("/profile")
async def get_profile(db: AsyncSession = Depends(get_db)):

    result = await db.execute(text("""

        SELECT

        e.employee_id,
        e.name,
        d.department_name,
        e.fingerprint_id

        FROM employees e

        LEFT JOIN departments d
        ON d.department_id = e.department_id

        WHERE employee_id=:id

    """), {"id": CURRENT_USER_ID})

    return result.mappings().first()



# update profile
@router.put("/profile")
async def update_profile(name: str,
                         db: AsyncSession = Depends(get_db)):

    await db.execute(text("""

        UPDATE employees

        SET name=:name

        WHERE employee_id=:id

    """), {
        "name": name,
        "id": CURRENT_USER_ID
    })

    await db.commit()

    return {"message": "profile updated"}



# change password placeholder
@router.put("/profile/change-password")
async def change_password():

    return {"message": "password updated"}