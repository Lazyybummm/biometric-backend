from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date
from typing import Optional
from app.db.session import get_db
from app.api.dependencies import verify_tenant_api_key
from app.models.domain import Tenant

router = APIRouter()


@router.get("/attendance/today")
async def today_attendance(
    dept_id: Optional[int] = None,
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: View today's attendance"""
    
    query = """
        SELECT 
            u.id,
            u.name,
            u.employee_code,
            d.department_name,
            MIN(a.timestamp) FILTER (WHERE a.record_type = 'IN') as check_in,
            MAX(a.timestamp) FILTER (WHERE a.record_type = 'OUT') as check_out,
            CASE 
                WHEN MIN(a.timestamp) FILTER (WHERE a.record_type = 'IN') IS NOT NULL 
                THEN 'present' 
                ELSE 'absent' 
            END as status,
            CASE 
                WHEN MIN(a.timestamp) FILTER (WHERE a.record_type = 'IN')::time > '09:15:00'
                THEN 'late'
                ELSE 'on_time'
            END as punctuality
        FROM users u
        LEFT JOIN departments d ON u.dept_id = d.department_id
        LEFT JOIN attendance_logs a ON u.id = a.user_id 
            AND DATE(a.timestamp) = CURRENT_DATE
        WHERE u.tenant_id = :tenant_id
        AND u.role = 'employee'
        AND u.is_active = true
    """
    
    params = {"tenant_id": tenant.id}
    
    if dept_id:
        query += " AND u.dept_id = :dept_id"
        params["dept_id"] = dept_id
    
    query += " GROUP BY u.id, d.department_name ORDER BY u.name"
    
    result = await db.execute(text(query), params)
    return result.mappings().all()


@router.get("/attendance/date/{attendance_date}")
async def attendance_by_date(
    attendance_date: date,
    dept_id: Optional[int] = None,
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: View attendance for a specific date"""
    
    query = """
        SELECT 
            u.id,
            u.name,
            u.employee_code,
            d.department_name,
            MIN(a.timestamp) FILTER (WHERE a.record_type = 'IN') as check_in,
            MAX(a.timestamp) FILTER (WHERE a.record_type = 'OUT') as check_out,
            CASE 
                WHEN MIN(a.timestamp) FILTER (WHERE a.record_type = 'IN') IS NOT NULL 
                THEN 'present' 
                ELSE 'absent' 
            END as status
        FROM users u
        LEFT JOIN departments d ON u.dept_id = d.department_id
        LEFT JOIN attendance_logs a ON u.id = a.user_id 
            AND DATE(a.timestamp) = :attendance_date
        WHERE u.tenant_id = :tenant_id
        AND u.role = 'employee'
        AND u.is_active = true
    """
    
    params = {
        "tenant_id": tenant.id,
        "attendance_date": attendance_date
    }
    
    if dept_id:
        query += " AND u.dept_id = :dept_id"
        params["dept_id"] = dept_id
    
    query += " GROUP BY u.id, d.department_name ORDER BY u.name"
    
    result = await db.execute(text(query), params)
    return result.mappings().all()


@router.get("/attendance/summary")
async def attendance_summary(
    month: int,
    year: int,
    dept_id: Optional[int] = None,
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Get monthly attendance summary"""
    
    query = """
        SELECT 
            u.id,
            u.name,
            u.employee_code,
            d.department_name,
            COUNT(DISTINCT DATE(a.timestamp)) FILTER (WHERE a.record_type = 'IN') as days_present,
            COUNT(DISTINCT DATE(a.timestamp)) FILTER (
                WHERE a.record_type = 'IN' 
                AND EXTRACT(HOUR FROM a.timestamp) >= 9 
                AND EXTRACT(MINUTE FROM a.timestamp) > 15
            ) as days_late,
            COUNT(DISTINCT DATE(a.timestamp)) FILTER (WHERE a.record_type = 'IN') as total_days
        FROM users u
        LEFT JOIN departments d ON u.dept_id = d.department_id
        LEFT JOIN attendance_logs a ON u.id = a.user_id 
            AND EXTRACT(MONTH FROM a.timestamp) = :month
            AND EXTRACT(YEAR FROM a.timestamp) = :year
        WHERE u.tenant_id = :tenant_id
        AND u.role = 'employee'
        AND u.is_active = true
    """
    
    params = {
        "tenant_id": tenant.id,
        "month": month,
        "year": year
    }
    
    if dept_id:
        query += " AND u.dept_id = :dept_id"
        params["dept_id"] = dept_id
    
    query += " GROUP BY u.id, d.department_name ORDER BY u.name"
    
    result = await db.execute(text(query), params)
    return result.mappings().all()


@router.get("/attendance/stats")
async def attendance_statistics(
    month: Optional[int] = None,
    year: Optional[int] = None,
    tenant: Tenant = Depends(verify_tenant_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Tenant Manager: Get overall attendance statistics"""
    
    if not month or not year:
        month = date.today().month
        year = date.today().year
    
    result = await db.execute(text("""
        WITH daily_stats AS (
            SELECT 
                DATE(timestamp) as day,
                COUNT(DISTINCT user_id) as present_count,
                COUNT(DISTINCT user_id) FILTER (
                    WHERE timestamp::time <= '09:15:00'
                ) as on_time_count
            FROM attendance_logs
            WHERE tenant_id = :tenant_id
            AND record_type = 'IN'
            AND EXTRACT(MONTH FROM timestamp) = :month
            AND EXTRACT(YEAR FROM timestamp) = :year
            GROUP BY DATE(timestamp)
        )
        SELECT 
            COUNT(DISTINCT day) as total_working_days,
            AVG(present_count) as avg_daily_present,
            AVG(on_time_count) as avg_daily_on_time,
            MAX(present_count) as max_present,
            MIN(present_count) as min_present
        FROM daily_stats
    """), {
        "tenant_id": tenant.id,
        "month": month,
        "year": year
    })
    
    return result.mappings().first()