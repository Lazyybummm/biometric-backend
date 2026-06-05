"""
Org Admin Attendance Routes
Handles attendance viewing for department administrators
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date, datetime, timezone
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
        
        result = await db.execute(text("""
            SELECT 
                u.id, 
                u.name, 
                u.employee_code,
                MIN(a.timestamp) FILTER (WHERE a.record_type = 'IN') as check_in,
                MAX(a.timestamp) FILTER (WHERE a.record_type = 'OUT') as check_out
            FROM users u
            LEFT JOIN attendance_logs a ON u.id = a.user_id AND DATE(a.timestamp AT TIME ZONE 'UTC') = CURRENT_DATE
            WHERE u.tenant_id = :tenant_id 
            AND u.dept_id = :dept_id 
            AND u.role = 'employee' 
            AND u.is_active = true
            GROUP BY u.id, u.name, u.employee_code
            ORDER BY u.name
        """), {
            "tenant_id": current_user.tenant_id, 
            "dept_id": current_user.dept_id
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
                    "met_min_hours": False,
                    "is_late": False,
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
                "check_in": check_in,
                "check_out": check_out,
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
        met_min = len([r for r in enriched_rows if r.get("met_min_hours", False)])
        total_hours = sum([r.get("hours_worked", 0) for r in enriched_rows])
        
        return {
            "date": date.today().isoformat(),
            "summary": {
                "total_employees": total,
                "present": present,
                "absent": total - present,
                "late": late,
                "on_time": present - late,
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
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching today's attendance: {str(e)}\n{traceback.format_exc()}"
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
        
        result = await db.execute(text("""
            SELECT 
                u.id, 
                u.name, 
                u.employee_code,
                MIN(CASE WHEN a.record_type = 'IN' THEN a.timestamp END) as check_in,
                MAX(CASE WHEN a.record_type = 'OUT' THEN a.timestamp END) as check_out
            FROM users u
            LEFT JOIN attendance_logs a ON u.id = a.user_id AND DATE(a.timestamp AT TIME ZONE 'UTC') = :attendance_date
            WHERE u.tenant_id = :tenant_id 
            AND u.dept_id = :dept_id 
            AND u.role = 'employee' 
            AND u.is_active = true
            GROUP BY u.id, u.name, u.employee_code
            ORDER BY u.name
        """), {
            "tenant_id": current_user.tenant_id,
            "dept_id": current_user.dept_id,
            "attendance_date": attendance_date
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
                    "met_min_hours": False,
                    "is_late": False,
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
                "check_in": check_in,
                "check_out": check_out,
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
        met_min = len([r for r in enriched_rows if r.get("met_min_hours", False)])
        total_hours = sum([r.get("hours_worked", 0) for r in enriched_rows])
        
        return {
            "date": attendance_date.isoformat(),
            "summary": {
                "total_employees": total,
                "present": present,
                "absent": total - present,
                "late": late,
                "on_time": present - late,
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
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching attendance for {attendance_date}: {str(e)}\n{traceback.format_exc()}"
        )