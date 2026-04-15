from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, Enum, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class CommandStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class RoleEnum(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    api_token = Column(String, unique=True, index=True, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.TENANT_ADMIN, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True) 

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    device_id = Column(String, index=True, nullable=False)
    secret_key = Column(String, nullable=False)
    status = Column(String, default="offline")
    last_seen = Column(DateTime(timezone=True))
    
    __table_args__ = (Index('ix_tenant_device', 'tenant_id', 'device_id', unique=True),)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    finger_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)

    __table_args__ = (Index('ix_tenant_finger', 'tenant_id', 'finger_id', unique=True),)

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    device_id = Column(String, nullable=False)
    finger_id = Column(Integer, nullable=False)
    record_type = Column(String, nullable=False, default="IN") # <--- NEW FIELD
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_tenant_timestamp', 'tenant_id', 'timestamp'),
        UniqueConstraint('tenant_id', 'device_id', 'finger_id', 'timestamp', name='uix_attendance_record')
    )

class Command(Base):
    __tablename__ = "commands"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    device_id = Column(String, nullable=False)
    command = Column(String, nullable=False)
    target_id = Column(Integer, nullable=True)
    status = Column(Enum(CommandStatus), default=CommandStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())