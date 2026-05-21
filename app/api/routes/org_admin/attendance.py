from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date, datetime
from typing import Optional
from app.db.session import get_db
from app.api.dependencies import get_current_user, require_role
from app.models.domain import User
from app.services.tenant_settings_service import (
    get_tenant_settings, 
    calculate_valid_working_hours, 
    calculate_late_status
)

router = APIRouter()


@router.get("/attendance/today")
async def today_attendance(
    current_user: User = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Org Admin: Today's attendance for department with working hours calculation"""
    
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
        LEFT JOIN attendance_logs a ON u.id = a.user_id AND DATE(a.timestamp) = CURRENT_DATE
        WHERE u.tenant_id = :tenant_id 
        AND u.dept_id = :dept_id 
        AND u.role = 'employee' 
        AND u.is_active = true
        GROUP BY u.id 
        ORDER BY u.name
    """), {
        "tenant_id": current_user.tenant_id, 
        "dept_id": current_user.dept_id
    })
    
    rows = result.mappings().all()
    
    # Calculate working hours for each employee
    enriched_rows = []
    for row in rows:
        valid_hours, actual_duration, lost_hours, met_min_hours, status_msg = calculate_valid_working_hours(
            row["check_in"],
            row["check_out"],
            settings
        )
        
        is_late = False
        if row["check_in"]:
            is_late, _ = calculate_late_status(row["check_in"], settings)
        
        enriched_rows.append({
            "id": row["id"],
            "name": row["name"],
            "employee_code": row["employee_code"],
            "check_in": row["check_in"],
            "check_out": row["check_out"],
            "hours_worked": round(valid_hours, 2),
            "met_min_hours": met_min_hours,
            "is_late": is_late,
            "status": "present" if row["check_in"] else "absent"
        })
    
    return enriched_rows


@router.get("/attendance/date/{attendance_date}")
async def attendance_by_date(
    attendance_date: date,
    current_user: User = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Org Admin: Attendance for specific date with working hours calculation"""
    
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
        LEFT JOIN attendance_logs a ON u.id = a.user_id AND DATE(a.timestamp) = :attendance_date
        WHERE u.tenant_id = :tenant_id 
        AND u.dept_id = :dept_id 
        AND u.role = 'employee' 
        AND u.is_active = true
        GROUP BY u.id 
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
        valid_hours, actual_duration, lost_hours, met_min_hours, status_msg = calculate_valid_working_hours(
            row["check_in"],
            row["check_out"],
            settings
        )
        
        is_late = False
        if row["check_in"]:
            is_late, _ = calculate_late_status(row["check_in"], settings)
        
        enriched_rows.append({
            "id": row["id"],
            "name": row["name"],
            "employee_code": row["employee_code"],
            "check_in": row["check_in"],
            "check_out": row["check_out"],
            "hours_worked": round(valid_hours, 2),
            "met_min_hours": met_min_hours,
            "is_late": is_late,
            "status": "present" if row["check_in"] else "absent"
        })
    
    # Calculate summary
    total = len(enriched_rows)
    present = len([r for r in enriched_rows if r["check_in"]])
    met_min = len([r for r in enriched_rows if r["met_min_hours"]])
    
    return {
        "date": attendance_date,
        "summary": {
            "total_employees": total,
            "present": present,
            "absent": total - present,
            "met_minimum_hours": met_min,
            "attendance_rate": round((present / total * 100), 1) if total > 0 else 0,
            "compliance_rate": round((met_min / present * 100), 1) if present > 0 else 0
        },
        "employees": enriched_rows
    }