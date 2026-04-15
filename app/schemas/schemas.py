from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
from app.models.domain import CommandStatus

# -- Users --
class UserEnrollRequest(BaseModel):
    finger_id: int = Field(..., ge=1, le=127)
    name: str
    target_tenant_id: Optional[int] = None

class UserDeleteRequest(BaseModel):
    finger_id: int = Field(..., ge=1, le=127)
    target_tenant_id: Optional[int] = None

# -- Devices --
class DeviceRegisterRequest(BaseModel):
    device_id: str
    secret_key: str

class DeviceResponse(BaseModel):
    device_id: str
    status: str
    last_seen: Optional[datetime.datetime]

# -- Attendance --
class SyncItem(BaseModel):
    finger_id: int
    timestamp: datetime.datetime

class BulkAttendanceRequest(BaseModel):
    logs: List[SyncItem]

class AttendanceLogResponse(BaseModel):
    timestamp: datetime.datetime
    finger_id: int
    device_id: str
    record_type: str # <--- NEW FIELD
    user_name: Optional[str] = "Unknown"

# -- Commands --
class CommandRequest(BaseModel):
    device_id: str
    command: str
    target_id: Optional[int] = None