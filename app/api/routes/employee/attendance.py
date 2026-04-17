from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, date
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.domain import User

router = APIRouter()


# =========================
# SPECIFIC ROUTES FIRST!
# =========================

@router.get("/attendance/today")
async def get_today_attendance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get today's attendance status"""
    query = text("""
        SELECT
            MIN(timestamp) FILTER (WHERE record_type = 'IN') as check_in,
            MAX(timestamp) FILTER (WHERE record_type = 'OUT') as check_out,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL 
                THEN 'present' 
                ELSE 'absent' 
            END as status,
            EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/3600 as hours_worked
        FROM attendance_logs
        WHERE user_id = :user_id
        AND DATE(timestamp) = CURRENT_DATE
    """)
    result = await db.execute(query, {"user_id": current_user.id})
    data = result.mappings().first()
    
    if not data or not data["check_in"]:
        return {
            "check_in": None,
            "check_out": None,
            "status": "absent",
            "hours_worked": 0
        }
    
    return {
        "check_in": data["check_in"],
        "check_out": data["check_out"],
        "status": data["status"],
        "hours_worked": round(data["hours_worked"] or 0, 2)
    }


@router.get("/attendance/stats")
async def get_attendance_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get overall attendance statistics"""
    
    # Get daily aggregates
    daily_query = text("""
        SELECT
            DATE(timestamp) as work_date,
            MIN(timestamp) FILTER (WHERE record_type = 'IN') as check_in,
            MAX(timestamp) FILTER (WHERE record_type = 'OUT') as check_out,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN')::time > '09:15:00' THEN 1 ELSE 0
            END as is_late,
            EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/3600 as hours_worked
        FROM attendance_logs
        WHERE user_id = :user_id
        AND record_type IN ('IN', 'OUT')
        GROUP BY DATE(timestamp)
        HAVING MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL
    """)
    
    daily_result = await db.execute(daily_query, {"user_id": current_user.id})
    daily_rows = daily_result.mappings().all()
    
    # Get first and last punch
    punch_query = text("""
        SELECT
            MIN(timestamp) as first_punch,
            MAX(timestamp) as last_punch
        FROM attendance_logs
        WHERE user_id = :user_id
    """)
    punch_result = await db.execute(punch_query, {"user_id": current_user.id})
    punch_data = punch_result.mappings().first()
    
    total_present = len(daily_rows)
    total_late = sum(r["is_late"] or 0 for r in daily_rows)
    total_hours = sum(r["hours_worked"] or 0 for r in daily_rows)
    
    return {
        "total_present_days": total_present,
        "total_late_days": total_late,
        "total_hours_worked": round(total_hours, 2),
        "average_hours_per_day": round(total_hours / max(1, total_present), 2),
        "first_punch": punch_data["first_punch"] if punch_data else None,
        "last_punch": punch_data["last_punch"] if punch_data else None
    }


@router.get("/attendance/stats/monthly")
async def get_monthly_stats(
    month: int = None,
    year: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get monthly attendance statistics"""
    from calendar import monthrange
    
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year
    
    # Get daily aggregates for the month
    daily_query = text("""
        SELECT
            DATE(timestamp) as work_date,
            MIN(timestamp) FILTER (WHERE record_type = 'IN') as check_in,
            MAX(timestamp) FILTER (WHERE record_type = 'OUT') as check_out,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL THEN 1 ELSE 0
            END as is_present,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN')::time > '09:15:00' THEN 1 ELSE 0
            END as is_late,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN')::time <= '09:15:00' THEN 1 ELSE 0
            END as is_on_time,
            EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/3600 as hours_worked
        FROM attendance_logs
        WHERE user_id = :user_id
        AND EXTRACT(MONTH FROM timestamp) = :month
        AND EXTRACT(YEAR FROM timestamp) = :year
        AND record_type IN ('IN', 'OUT')
        GROUP BY DATE(timestamp)
        HAVING MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL
        ORDER BY work_date
    """)
    
    daily_result = await db.execute(daily_query, {
        "user_id": current_user.id,
        "month": month,
        "year": year
    })
    daily_rows = daily_result.mappings().all()
    
    # Calculate aggregates
    present = len(daily_rows)
    late = sum(1 for r in daily_rows if r["is_late"])
    on_time = sum(1 for r in daily_rows if r["is_on_time"])
    total_hours = sum(r["hours_worked"] or 0 for r in daily_rows)
    
    _, total_days = monthrange(year, month)
    working_days = total_days - (total_days // 7 * 2)  # Simplified: exclude weekends
    
    # Overtime calculation (assuming 9 hours standard)
    overtime_hours = sum(max(0, (r["hours_worked"] or 0) - 9) for r in daily_rows)
    
    return {
        "month": month,
        "year": year,
        "total_days_in_month": total_days,
        "estimated_working_days": working_days,
        "present_days": present,
        "absent_days": max(0, working_days - present),
        "late_days": late,
        "on_time_days": on_time,
        "total_hours": round(total_hours, 2),
        "average_hours_per_day": round(total_hours / max(1, present), 2),
        "overtime_hours": round(overtime_hours, 2),
        "attendance_percentage": round((present / max(1, working_days)) * 100, 2)
    }


@router.get("/attendance/hours/summary")
async def get_hours_summary(
    month: int = None,
    year: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get detailed hours worked summary"""
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year
    
    query = text("""
        SELECT
            DATE(timestamp) as work_date,
            MIN(timestamp) FILTER (WHERE record_type = 'IN') as check_in,
            MAX(timestamp) FILTER (WHERE record_type = 'OUT') as check_out,
            EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/3600 as hours_worked,
            CASE 
                WHEN EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/3600 > 9 
                THEN EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/3600 - 9
                ELSE 0
            END as overtime_hours,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN')::time > '09:15:00'
                THEN 'late'
                ELSE 'on_time'
            END as punctuality
        FROM attendance_logs
        WHERE user_id = :user_id
        AND EXTRACT(MONTH FROM timestamp) = :month
        AND EXTRACT(YEAR FROM timestamp) = :year
        AND record_type IN ('IN', 'OUT')
        GROUP BY DATE(timestamp)
        HAVING MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL
        ORDER BY work_date DESC
    """)
    
    result = await db.execute(query, {
        "user_id": current_user.id,
        "month": month,
        "year": year
    })
    rows = result.mappings().all()
    
    total_hours = sum(r["hours_worked"] or 0 for r in rows)
    total_overtime = sum(r["overtime_hours"] or 0 for r in rows)
    
    return {
        "month": month,
        "year": year,
        "daily_breakdown": [
            {
                "date": str(r["work_date"]),
                "check_in": str(r["check_in"]) if r["check_in"] else None,
                "check_out": str(r["check_out"]) if r["check_out"] else None,
                "hours_worked": round(r["hours_worked"] or 0, 2),
                "overtime": round(r["overtime_hours"] or 0, 2),
                "punctuality": r["punctuality"]
            }
            for r in rows
        ],
        "summary": {
            "total_days_worked": len(rows),
            "total_hours": round(total_hours, 2),
            "total_overtime": round(total_overtime, 2),
            "average_hours": round(total_hours / max(1, len(rows)), 2)
        }
    }


@router.get("/attendance/calendar")
async def get_attendance_calendar(
    month: int = None,
    year: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get calendar-style attendance view"""
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year
    
    query = text("""
        SELECT
            EXTRACT(DAY FROM DATE(timestamp)) as day_num,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL 
                THEN 'present' 
                ELSE 'absent' 
            END as status,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN')::time > '09:15:00'
                THEN 'late'
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL
                THEN 'on_time'
                ELSE NULL
            END as punctuality
        FROM attendance_logs
        WHERE user_id = :user_id
        AND EXTRACT(MONTH FROM timestamp) = :month
        AND EXTRACT(YEAR FROM timestamp) = :year
        GROUP BY DATE(timestamp)
        ORDER BY day_num
    """)
    
    result = await db.execute(query, {
        "user_id": current_user.id,
        "month": month,
        "year": year
    })
    rows = result.mappings().all()
    
    from calendar import monthrange
    _, total_days = monthrange(year, month)
    
    calendar_data = {}
    for row in rows:
        day = int(row["day_num"])
        calendar_data[day] = {
            "status": row["status"],
            "punctuality": row["punctuality"]
        }
    
    # Fill missing days as absent or weekend
    for day in range(1, total_days + 1):
        if day not in calendar_data:
            # Check if weekend (Saturday=5, Sunday=6 in Python's weekday)
            import datetime as dt
            weekday = dt.date(year, month, day).weekday()
            is_weekend = weekday >= 5
            calendar_data[day] = {
                "status": "weekend" if is_weekend else "absent",
                "punctuality": None
            }
    
    return {
        "month": month,
        "year": year,
        "total_days": total_days,
        "calendar": calendar_data
    }


# =========================
# GENERIC ROUTES LAST!
# =========================

@router.get("/attendance")
async def get_attendance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get personal attendance history"""
    query = text("""
        SELECT
            DATE(timestamp) as attendance_date,
            MIN(timestamp) FILTER (WHERE record_type = 'IN') as check_in,
            MAX(timestamp) FILTER (WHERE record_type = 'OUT') as check_out,
            EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/3600 as hours_worked,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL 
                THEN 'present' ELSE 'absent' 
            END as status,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN')::time > '09:15:00'
                THEN 'late'
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL
                THEN 'on_time'
                ELSE NULL
            END as punctuality
        FROM attendance_logs
        WHERE user_id = :user_id
        GROUP BY DATE(timestamp)
        ORDER BY attendance_date DESC
        LIMIT 90
    """)
    result = await db.execute(query, {"user_id": current_user.id})
    rows = result.mappings().all()
    
    return [
        {
            "date": str(r["attendance_date"]),
            "check_in": str(r["check_in"]) if r["check_in"] else None,
            "check_out": str(r["check_out"]) if r["check_out"] else None,
            "hours_worked": round(r["hours_worked"] or 0, 2),
            "status": r["status"],
            "punctuality": r["punctuality"]
        }
        for r in rows
    ]


@router.get("/attendance/{date_str}")
async def get_attendance_by_date(
    date_str: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Get attendance for a specific date (YYYY-MM-DD)"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    
    query = text("""
        SELECT
            DATE(timestamp) as attendance_date,
            MIN(timestamp) FILTER (WHERE record_type = 'IN') as check_in,
            MAX(timestamp) FILTER (WHERE record_type = 'OUT') as check_out,
            EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/3600 as hours_worked,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL 
                THEN 'present' ELSE 'absent' 
            END as status,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN')::time > '09:15:00'
                THEN 'late'
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL
                THEN 'on_time'
                ELSE NULL
            END as punctuality
        FROM attendance_logs
        WHERE user_id = :user_id AND DATE(timestamp) = :target_date
        GROUP BY DATE(timestamp)
    """)
    result = await db.execute(query, {
        "user_id": current_user.id,
        "target_date": target_date
    })
    data = result.mappings().first()
    
    if not data or not data["check_in"]:
        return {
            "attendance_date": date_str,
            "check_in": None,
            "check_out": None,
            "hours_worked": 0,
            "status": "absent",
            "punctuality": None
        }
    
    return {
        "attendance_date": str(data["attendance_date"]),
        "check_in": str(data["check_in"]) if data["check_in"] else None,
        "check_out": str(data["check_out"]) if data["check_out"] else None,
        "hours_worked": round(data["hours_worked"] or 0, 2),
        "status": data["status"],
        "punctuality": data["punctuality"]
    }


@router.get("/attendance/export")
async def export_attendance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Employee: Export attendance data as CSV-ready format"""
    query = text("""
        SELECT
            TO_CHAR(DATE(timestamp), 'YYYY-MM-DD') as date,
            TO_CHAR(MIN(timestamp) FILTER (WHERE record_type = 'IN'), 'HH24:MI:SS') as check_in,
            TO_CHAR(MAX(timestamp) FILTER (WHERE record_type = 'OUT'), 'HH24:MI:SS') as check_out,
            ROUND(EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/3600, 2) as hours_worked,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL 
                THEN 'Present' ELSE 'Absent' 
            END as status,
            CASE 
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN')::time > '09:15:00'
                THEN 'Late'
                WHEN MIN(timestamp) FILTER (WHERE record_type = 'IN') IS NOT NULL
                THEN 'On Time'
                ELSE '-'
            END as punctuality
        FROM attendance_logs
        WHERE user_id = :user_id
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
    """)
    result = await db.execute(query, {"user_id": current_user.id})
    rows = result.mappings().all()
    
    return {
        "message": "Export ready",
        "format": "csv",
        "total_records": len(rows),
        "data": [dict(r) for r in rows]
    }