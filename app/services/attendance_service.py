from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.future import select
from sqlalchemy import desc
from app.models.domain import AttendanceLog, User
import datetime
from datetime import timedelta


# =========================
# HELPER: GET USER BY FINGER
# =========================

async def get_user_by_finger(tenant_id: int, finger_id: int, db: AsyncSession):
    result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.finger_id == finger_id
        )
    )
    return result.scalars().first()


# =========================
# SINGLE ATTENDANCE
# =========================

async def process_attendance(
    tenant_id: int,
    device_id: str,
    finger_id: int,
    db: AsyncSession
):
    now = datetime.datetime.now(datetime.timezone.utc)

    # =========================
    # 1. GET USER
    # =========================
    user = await get_user_by_finger(tenant_id, finger_id, db)

    user_id = user.id if user else None
    user_name = user.name if user else "Unknown User"
    employee_code = user.employee_code if user else None

    # =========================
    # 2. TODAY START
    # =========================
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # =========================
    # 3. LAST LOG
    # =========================
    result = await db.execute(
        select(AttendanceLog)
        .where(
            AttendanceLog.tenant_id == tenant_id,
            AttendanceLog.finger_id == finger_id,
            AttendanceLog.timestamp >= today
        )
        .order_by(desc(AttendanceLog.timestamp))
        .limit(1)
    )

    last_log = result.scalars().first()

    # =========================
    # 4. SMART LOGIC
    # =========================
    current_type = "IN"

    if last_log:
        time_diff = now - last_log.timestamp

        # 🚨 Prevent duplicate scan within 5 minutes
        if time_diff < timedelta(minutes=1):
            return last_log, user_name

        current_type = "OUT" if last_log.record_type == "IN" else "IN"

    # =========================
    # 5. SAVE LOG
    # =========================
    log = AttendanceLog(
        tenant_id=tenant_id,
        device_id=device_id,
        finger_id=finger_id,
        user_id=user_id,   # ✅ NEW
        timestamp=now,
        record_type=current_type
    )

    db.add(log)
    await db.commit()
    await db.refresh(log)

    return log, user_name


# =========================
# BULK ATTENDANCE (OFFLINE)
# =========================

async def process_bulk_attendance(
    tenant_id: int,
    device_id: str,
    logs: list,
    db: AsyncSession
):
    if not logs:
        return 0

    values = []

    for l in logs:
        user = await get_user_by_finger(tenant_id, l.finger_id, db)

        values.append({
            "tenant_id": tenant_id,
            "device_id": device_id,
            "finger_id": l.finger_id,
            "user_id": user.id if user else None,  # ✅ NEW
            "timestamp": l.timestamp,
            "record_type": "IN"
        })

    stmt = insert(AttendanceLog).values(values)
    stmt = stmt.on_conflict_do_nothing(
        constraint='uix_attendance_record'
    )

    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount or 0


# =========================
# HISTORY
# =========================

async def get_attendance_history(
    tenant_id: int,
    db: AsyncSession
):
    stmt = (
        select(
            AttendanceLog,
            User.name,
            User.employee_code
        )
        .outerjoin(
            User,
            AttendanceLog.user_id == User.id   # ✅ FIXED JOIN
        )
        .where(AttendanceLog.tenant_id == tenant_id)
        .order_by(AttendanceLog.timestamp.desc())
        .limit(50)
    )

    result = await db.execute(stmt)

    response_data = []

    for row in result.mappings():
        log = row["AttendanceLog"]
        user_name = row["name"]
        employee_code = row["employee_code"]

        response_data.append({
            "timestamp": log.timestamp,
            "finger_id": log.finger_id,
            "user_id": log.user_id,              # ✅ NEW
            "employee_code": employee_code,      # ✅ NEW
            "device_id": log.device_id,
            "record_type": log.record_type,
            "user_name": user_name or "Unknown"
        })

    return response_data