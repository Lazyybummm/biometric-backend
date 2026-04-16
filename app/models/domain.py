from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, Enum, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# =========================
# ENUMS
# =========================

class CommandStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class RoleEnum(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"


# =========================
# ADMIN USER
# =========================

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    api_token = Column(String, unique=True, index=True, nullable=False)

    role = Column(
        Enum(RoleEnum, name="roleenum", values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)


# =========================
# TENANT
# =========================

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =========================
# DEVICE
# =========================

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    device_id = Column(String, index=True, nullable=False)
    secret_key = Column(String, nullable=False)
    status = Column(String, default="offline")
    last_seen = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('ix_tenant_device', 'tenant_id', 'device_id', unique=True),
    )


# =========================
# USER
# =========================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    # Multi-tenant safe identity
    employee_code = Column(String, nullable=False, index=True)

    # Hardware mapping (reusable)
    finger_id = Column(Integer, nullable=False)

    name = Column(String, nullable=False)

    __table_args__ = (
        Index('ix_tenant_finger', 'tenant_id', 'finger_id', unique=True),
        Index('ix_tenant_employee_code', 'tenant_id', 'employee_code', unique=True),
    )


# =========================
# ATTENDANCE LOG (UPDATED ✅)
# =========================

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    device_id = Column(String, nullable=False)

    # ✅ NEW: stable identity reference
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # hardware mapping (still required)
    finger_id = Column(Integer, nullable=False)

    record_type = Column(String, nullable=False, default="IN")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_tenant_timestamp', 'tenant_id', 'timestamp'),
        UniqueConstraint(
            'tenant_id',
            'device_id',
            'finger_id',
            'timestamp',
            name='uix_attendance_record'
        )
    )


# =========================
# COMMAND
# =========================

class Command(Base):
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    device_id = Column(String, nullable=False)
    command = Column(String, nullable=False)
    target_id = Column(Integer, nullable=True)
    status = Column(Enum(CommandStatus), default=CommandStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())