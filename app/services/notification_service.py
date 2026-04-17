"""
Notification Service - Handles creation of notifications for various events
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    title: str,
    message: str,
    notification_type: str
):
    """Create a single notification for a specific user"""
    try:
        await db.execute(text("""
            INSERT INTO notifications (tenant_id, user_id, title, message, type, is_read)
            VALUES (:tenant_id, :user_id, :title, :message, :type, false)
        """), {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type
        })
        await db.commit()
        logger.info(f"Notification created for user {user_id}: {title}")
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        await db.rollback()


async def create_notification_for_role(
    db: AsyncSession,
    tenant_id: int,
    role: str,
    title: str,
    message: str,
    notification_type: str,
    dept_id: Optional[int] = None
):
    """Create notifications for all users with a specific role"""
    try:
        query = """
            INSERT INTO notifications (tenant_id, user_id, title, message, type, is_read)
            SELECT :tenant_id, id, :title, :message, :type, false
            FROM users
            WHERE tenant_id = :tenant_id
            AND role = :role
            AND is_active = true
        """
        params = {
            "tenant_id": tenant_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "role": role
        }
        
        if dept_id is not None:
            query += " AND dept_id = :dept_id"
            params["dept_id"] = dept_id
        
        await db.execute(text(query), params)
        await db.commit()
        logger.info(f"Notifications created for role {role} in tenant {tenant_id}")
    except Exception as e:
        logger.error(f"Failed to create role notifications: {e}")
        await db.rollback()


async def broadcast_to_tenant(
    db: AsyncSession,
    tenant_id: int,
    title: str,
    message: str,
    notification_type: str,
    roles: Optional[List[str]] = None
):
    """Broadcast notification to entire tenant or specific roles"""
    try:
        query = """
            INSERT INTO notifications (tenant_id, user_id, title, message, type, is_read)
            SELECT :tenant_id, id, :title, :message, :type, false
            FROM users
            WHERE tenant_id = :tenant_id
            AND is_active = true
        """
        params = {
            "tenant_id": tenant_id,
            "title": title,
            "message": message,
            "type": notification_type
        }
        
        if roles:
            query += " AND role = ANY(:roles)"
            params["roles"] = roles
        
        await db.execute(text(query), params)
        await db.commit()
        logger.info(f"Broadcast notification sent in tenant {tenant_id}")
    except Exception as e:
        logger.error(f"Failed to broadcast notification: {e}")
        await db.rollback()


async def notify_employee(
    db: AsyncSession,
    tenant_id: int,
    employee_id: int,
    title: str,
    message: str,
    notification_type: str
):
    """Shortcut for notifying an employee"""
    await create_notification(db, tenant_id, employee_id, title, message, notification_type)


async def notify_org_admins(
    db: AsyncSession,
    tenant_id: int,
    dept_id: int,
    title: str,
    message: str,
    notification_type: str
):
    """Notify all org admins in a department"""
    await create_notification_for_role(
        db, tenant_id, "org_admin", title, message, notification_type, dept_id
    )