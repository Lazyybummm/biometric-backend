"""
Org Admin Attendance Routes
Handles attendance viewing for department administrators
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date, datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from app.db.session import get_db
from app.api.dependencies import require_role
from app.models.domain import User
from app.services.tenant_settings_service import (
    get_tenant_settings, 
    calculate_valid_working_hours, 
    calculate_late_status,
    ensure_timezone_aware
)

router = APIRouter()


@router.get("/attendance/today")
async def today_attendance(
    current_user: User = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Org Admin: Today's attendance for department with working hours calculation
    """
    try:
        # Get tenant settings
        settings = await get_tenant_settings(current_user.tenant_id, db)
        
        # Get today's date as date object (not string)
        today_date = date.today()
        
        # Query to fetch attendance for today
        result = await db.execute(text("""
            SELECT 
                u.id, 
                u.name, 
                u.employee_code,
                MIN(CASE WHEN a.record_type = 'IN' THEN a.timestamp END) as check_in,
                MAX(CASE WHEN a.record_type = 'OUT' THEN a.timestamp END) as check_out
            FROM users u
            LEFT JOIN attendance_logs a ON u.id = a.user_id 
                AND DATE(a.timestamp AT TIME ZONE 'UTC') = :today_date
            WHERE u.tenant_id = :tenant_id 
                AND u.dept_id = :dept_id 
                AND u.role = 'employee' 
                AND u.is_active = true
            GROUP BY u.id, u.name, u.employee_code
            ORDER BY u.name
        """), {
            "tenant_id": current_user.tenant_id, 
            "dept_id": current_user.dept_id,
            "today_date": today_date
        })
        
        rows = result.mappings().all()
        
        # Calculate working hours for each employee
        enriched_rows = []
        for row in rows:
            check_in = row["check_in"]
            check_out = row["check_out"]
            
            if check_in is None:
                enriched_rows.append({
                    "id": row["id"],
                    "name": row["name"],
                    "employee_code": row["employee_code"],
                    "check_in": None,
                    "check_out": None,
                    "hours_worked": 0,
                    "actual_duration": 0,
                    "lost_hours": 0,
                    "met_min_hours": False,
                    "is_late": False,
                    "late_message": "",
                    "status_message": "No check-in recorded",
                    "status": "absent"
                })
                continue
            
            # Ensure timestamps are timezone-aware
            check_in = ensure_timezone_aware(check_in)
            if check_out:
                check_out = ensure_timezone_aware(check_out)
            
            valid_hours, actual_duration, lost_hours, met_min_hours, status_msg = calculate_valid_working_hours(
                check_in,
                check_out,
                settings
            )
            
            is_late, late_msg = calculate_late_status(check_in, settings)
            
            enriched_rows.append({
                "id": row["id"],
                "name": row["name"],
                "employee_code": row["employee_code"],
                "check_in": check_in.isoformat() if check_in else None,
                "check_out": check_out.isoformat() if check_out else None,
                "hours_worked": round(valid_hours, 2),
                "actual_duration": round(actual_duration, 2),
                "lost_hours": round(lost_hours, 2),
                "met_min_hours": met_min_hours,
                "is_late": is_late,
                "late_message": late_msg,
                "status_message": status_msg,
                "status": "present"
            })
        
        # Calculate summary
        total = len(enriched_rows)
        present = len([r for r in enriched_rows if r["status"] == "present"])
        late = len([r for r in enriched_rows if r.get("is_late", False)])
        on_time = present - late
        met_min = len([r for r in enriched_rows if r.get("met_min_hours", False)])
        total_hours = sum([r.get("hours_worked", 0) for r in enriched_rows])
        
        return {
            "date": today_date.isoformat(),
            "summary": {
                "total_employees": total,
                "present": present,
                "absent": total - present,
                "late": late,
                "on_time": on_time if on_time > 0 else 0,
                "met_minimum_hours": met_min,
                "attendance_rate": round((present / total * 100), 1) if total > 0 else 0,
                "compliance_rate": round((met_min / present * 100), 1) if present > 0 else 0,
                "total_valid_hours": round(total_hours, 1),
                "average_hours": round(total_hours / present, 1) if present > 0 else 0
            },
            "employees": enriched_rows
        }
        
    except Exception as e:
        import traceback
        print(f"Error in today_attendance: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching today's attendance: {str(e)}"
        )


@router.get("/attendance/date/{attendance_date}")
async def attendance_by_date(
    attendance_date: date,
    current_user: User = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Org Admin: Attendance for specific date with working hours calculation
    """
    try:
        # Get tenant settings
        settings = await get_tenant_settings(current_user.tenant_id, db)
        
        # Use the date object directly (not converting to string)
        # For the date range approach (more reliable)
        start_datetime = datetime.combine(attendance_date, datetime.min.time(), tzinfo=timezone.utc)
        end_datetime = datetime.combine(attendance_date, datetime.max.time(), tzinfo=timezone.utc)
        
        # Query using timestamp range instead of DATE() function
        result = await db.execute(text("""
            SELECT 
                u.id, 
                u.name, 
                u.employee_code,
                MIN(CASE WHEN a.record_type = 'IN' THEN a.timestamp END) as check_in,
                MAX(CASE WHEN a.record_type = 'OUT' THEN a.timestamp END) as check_out
            FROM users u
            LEFT JOIN attendance_logs a ON u.id = a.user_id 
                AND a.timestamp >= :start_datetime
                AND a.timestamp <= :end_datetime
            WHERE u.tenant_id = :tenant_id 
                AND u.dept_id = :dept_id 
                AND u.role = 'employee' 
                AND u.is_active = true
            GROUP BY u.id, u.name, u.employee_code
            ORDER BY u.name
        """), {
            "tenant_id": current_user.tenant_id,
            "dept_id": current_user.dept_id,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime
        })
        
        rows = result.mappings().all()
        
        # Debug: Print to verify data is fetched
        print(f"Found {len(rows)} employees for date {attendance_date}")
        for row in rows[:3]:  # Print first 3 for debugging
            print(f"Employee: {row['name']}, IN: {row['check_in']}, OUT: {row['check_out']}")
        
        # Calculate working hours for each employee
        enriched_rows = []
        for row in rows:
            check_in = row["check_in"]
            check_out = row["check_out"]
            
            if check_in is None:
                enriched_rows.append({
                    "id": row["id"],
                    "name": row["name"],
                    "employee_code": row["employee_code"],
                    "check_in": None,
                    "check_out": None,
                    "hours_worked": 0,
                    "actual_duration": 0,
                    "lost_hours": 0,
                    "met_min_hours": False,
                    "is_late": False,
                    "late_message": "",
                    "status_message": "No check-in recorded",
                    "status": "absent"
                })
                continue
            
            # Ensure timestamps are timezone-aware
            check_in = ensure_timezone_aware(check_in)
            if check_out:
                check_out = ensure_timezone_aware(check_out)
                print(f"Processing {row['name']}: IN={check_in}, OUT={check_out}")
            else:
                print(f"Processing {row['name']}: IN={check_in}, OUT=None (not checked out yet)")
            
            valid_hours, actual_duration, lost_hours, met_min_hours, status_msg = calculate_valid_working_hours(
                check_in,
                check_out,
                settings
            )
            
            is_late, late_msg = calculate_late_status(check_in, settings)
            
            enriched_rows.append({
                "id": row["id"],
                "name": row["name"],
                "employee_code": row["employee_code"],
                "check_in": check_in.isoformat() if check_in else None,
                "check_out": check_out.isoformat() if check_out else None,
                "hours_worked": round(valid_hours, 2),
                "actual_duration": round(actual_duration, 2),
                "lost_hours": round(lost_hours, 2),
                "met_min_hours": met_min_hours,
                "is_late": is_late,
                "late_message": late_msg,
                "status_message": status_msg,
                "status": "present"
            })
        
        # Calculate summary
        total = len(enriched_rows)
        present = len([r for r in enriched_rows if r["status"] == "present"])
        late = len([r for r in enriched_rows if r.get("is_late", False)])
        on_time = present - late
        met_min = len([r for r in enriched_rows if r.get("met_min_hours", False)])
        total_hours = sum([r.get("hours_worked", 0) for r in enriched_rows])
        
        return {
            "date": attendance_date.isoformat(),
            "summary": {
                "total_employees": total,
                "present": present,
                "absent": total - present,
                "late": late,
                "on_time": on_time if on_time > 0 else 0,
                "met_minimum_hours": met_min,
                "attendance_rate": round((present / total * 100), 1) if total > 0 else 0,
                "compliance_rate": round((met_min / present * 100), 1) if present > 0 else 0,
                "total_valid_hours": round(total_hours, 1),
                "average_hours": round(total_hours / present, 1) if present > 0 else 0
            },
            "employees": enriched_rows
        }
        
    except Exception as e:
        import traceback
        print(f"Error in attendance_by_date: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching attendance for {attendance_date}: {str(e)}"
        )


@router.get("/attendance/summary/{year}/{month}")
async def attendance_summary(
    year: int,
    month: int,
    current_user: User = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Org Admin: Monthly attendance summary with statistics
    """
    try:
        # Validate month range
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        
        # Create date range for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # Convert to datetime for range query
        start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_datetime = datetime.combine(end_date, datetime.min.time(), tzinfo=timezone.utc)
        
        # Query for monthly summary
        result = await db.execute(text("""
            SELECT 
                u.id,
                u.name,
                u.employee_code,
                COUNT(DISTINCT DATE(a.timestamp AT TIME ZONE 'UTC')) as days_present,
                COUNT(DISTINCT CASE WHEN a.record_type = 'IN' THEN DATE(a.timestamp AT TIME ZONE 'UTC') END) as days_with_checkin,
                SUM(CASE 
                    WHEN a.record_type = 'IN' AND a.timestamp IS NOT NULL THEN 1 
                    ELSE 0 
                END) as total_checkins,
                MIN(a.timestamp) as first_checkin_of_month,
                MAX(a.timestamp) as last_checkout_of_month
            FROM users u
            LEFT JOIN attendance_logs a ON u.id = a.user_id 
                AND a.timestamp >= :start_datetime
                AND a.timestamp < :end_datetime
            WHERE u.tenant_id = :tenant_id 
                AND u.dept_id = :dept_id 
                AND u.role = 'employee' 
                AND u.is_active = true
            GROUP BY u.id, u.name, u.employee_code
            ORDER BY u.name
        """), {
            "tenant_id": current_user.tenant_id,
            "dept_id": current_user.dept_id,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime
        })
        
        rows = result.mappings().all()
        
        # Get working days in the month (excluding weekends if needed)
        total_days_in_month = (end_date - start_date).days
        
        enriched_summary = []
        for row in rows:
            days_present = row["days_present"] or 0
            attendance_percentage = (days_present / total_days_in_month * 100) if total_days_in_month > 0 else 0
            
            enriched_summary.append({
                "id": row["id"],
                "name": row["name"],
                "employee_code": row["employee_code"],
                "days_present": days_present,
                "days_absent": total_days_in_month - days_present,
                "attendance_percentage": round(attendance_percentage, 1),
                "total_checkins": row["total_checkins"] or 0,
                "first_checkin": row["first_checkin_of_month"].isoformat() if row["first_checkin_of_month"] else None,
                "last_checkout": row["last_checkout_of_month"].isoformat() if row["last_checkout_of_month"] else None
            })
        
        # Calculate department-wide statistics
        total_employees = len(enriched_summary)
        total_present_days = sum([r["days_present"] for r in enriched_summary])
        avg_attendance = (total_present_days / (total_employees * total_days_in_month) * 100) if total_employees > 0 else 0
        
        return {
            "year": year,
            "month": month,
            "month_name": start_date.strftime("%B"),
            "total_days": total_days_in_month,
            "total_employees": total_employees,
            "department_stats": {
                "total_present_days": total_present_days,
                "total_absent_days": (total_employees * total_days_in_month) - total_present_days,
                "average_attendance_percentage": round(avg_attendance, 1),
                "employees_with_perfect_attendance": len([r for r in enriched_summary if r["attendance_percentage"] == 100]),
                "employees_with_poor_attendance": len([r for r in enriched_summary if r["attendance_percentage"] < 75])
            },
            "employees": enriched_summary
        }
        
    except Exception as e:
        import traceback
        print(f"Error in attendance_summary: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching attendance summary: {str(e)}"
        )


@router.get("/attendance/employee/{employee_id}")
async def employee_attendance_history(
    employee_id: int,
    current_user: User = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db),
    limit: int = 30,
    offset: int = 0
):
    """
    Org Admin: View attendance history for a specific employee
    """
    try:
        # Verify employee belongs to the same department
        verify_result = await db.execute(text("""
            SELECT id FROM users 
            WHERE id = :employee_id 
                AND tenant_id = :tenant_id 
                AND dept_id = :dept_id
                AND role = 'employee'
        """), {
            "employee_id": employee_id,
            "tenant_id": current_user.tenant_id,
            "dept_id": current_user.dept_id
        })
        
        if not verify_result.mappings().first():
            raise HTTPException(status_code=404, detail="Employee not found in your department")
        
        # Get employee attendance history
        result = await db.execute(text("""
            SELECT 
                DATE(a.timestamp AT TIME ZONE 'UTC') as attendance_date,
                MIN(CASE WHEN a.record_type = 'IN' THEN a.timestamp END) as check_in,
                MAX(CASE WHEN a.record_type = 'OUT' THEN a.timestamp END) as check_out
            FROM attendance_logs a
            WHERE a.user_id = :employee_id
            GROUP BY DATE(a.timestamp AT TIME ZONE 'UTC')
            ORDER BY attendance_date DESC
            LIMIT :limit OFFSET :offset
        """), {
            "employee_id": employee_id,
            "limit": limit,
            "offset": offset
        })
        
        rows = result.mappings().all()
        
        # Get employee details
        employee_result = await db.execute(text("""
            SELECT name, employee_code, email 
            FROM users 
            WHERE id = :employee_id
        """), {"employee_id": employee_id})
        
        employee = employee_result.mappings().first()
        
        # Get settings for calculations
        settings = await get_tenant_settings(current_user.tenant_id, db)
        
        # Process attendance records
        attendance_records = []
        total_hours = 0
        days_with_checkout = 0
        
        for row in rows:
            check_in = ensure_timezone_aware(row["check_in"]) if row["check_in"] else None
            check_out = ensure_timezone_aware(row["check_out"]) if row["check_out"] else None
            
            if check_in and check_out:
                valid_hours, _, _, _, _ = calculate_valid_working_hours(
                    check_in, check_out, settings
                )
                total_hours += valid_hours
                days_with_checkout += 1
            else:
                valid_hours = 0
            
            attendance_records.append({
                "date": row["attendance_date"].isoformat() if row["attendance_date"] else None,
                "check_in": check_in.isoformat() if check_in else None,
                "check_out": check_out.isoformat() if check_out else None,
                "hours_worked": round(valid_hours, 2),
                "has_checkout": check_out is not None
            })
        
        # Get total count for pagination
        count_result = await db.execute(text("""
            SELECT COUNT(DISTINCT DATE(timestamp AT TIME ZONE 'UTC')) as total
            FROM attendance_logs
            WHERE user_id = :employee_id
        """), {"employee_id": employee_id})
        
        total_count = count_result.mappings().first()["total"] or 0
        
        return {
            "employee": {
                "id": employee_id,
                "name": employee["name"] if employee else "Unknown",
                "employee_code": employee["employee_code"] if employee else "N/A",
                "email": employee["email"] if employee else "N/A"
            },
            "summary": {
                "total_days_recorded": total_count,
                "total_hours_worked": round(total_hours, 1),
                "average_hours_per_day": round(total_hours / days_with_checkout, 1) if days_with_checkout > 0 else 0,
                "days_with_checkout": days_with_checkout
            },
            "attendance_records": attendance_records,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "has_more": offset + limit < total_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in employee_attendance_history: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching employee attendance history: {str(e)}"
        )