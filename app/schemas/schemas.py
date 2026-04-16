from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
from app.models.domain import CommandStatus


# =========================
# USERS
# =========================

class UserEnrollRequest(BaseModel):
    finger_id: int = Field(..., ge=1, le=127)
    name: str
    employee_code: str   # ✅ REQUIRED
    target_tenant_id: Optional[int] = None


class UserDeleteRequest(BaseModel):
    finger_id: int = Field(..., ge=1, le=127)
    target_tenant_id: Optional[int] = None


# =========================
# DEVICES
# =========================

class DeviceRegisterRequest(BaseModel):
    device_id: str
    secret_key: str


class DeviceResponse(BaseModel):
    device_id: str
    status: str
    last_seen: Optional[datetime.datetime]


# =========================
# ATTENDANCE
# =========================

class SyncItem(BaseModel):
    finger_id: int
    timestamp: datetime.datetime


class BulkAttendanceRequest(BaseModel):
    logs: List[SyncItem]


class AttendanceLogResponse(BaseModel):
    timestamp: datetime.datetime
    finger_id: int
    device_id: str
    record_type: str

    # ✅ NEW (important)
    user_id: Optional[int] = None
    employee_code: Optional[str] = None

    # existing
    user_name: Optional[str] = "Unknown"


# =========================
# COMMANDS
# =========================

class CommandRequest(BaseModel):
    device_id: str
    command: str
    target_id: Optional[int] = None