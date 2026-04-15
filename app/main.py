from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from contextlib import asynccontextmanager
from app.api.routes import attendance, admin, users
from app.mqtt.client import mqtt_manager
import logging
import os

from app.api.routes.org_admin import (
    dashboard as org_dashboard,
    employees,
    attendance as org_attendance,
    leaves as org_leaves,
    departments,
    holidays as org_holidays,
    reports,
    settings,
    notifications as org_notifications,
    devices,
    activity
)

from app.api.routes.user import (
    dashboard as user_dashboard,
    attendance as user_attendance,
    leaves as user_leaves,
    holidays as user_holidays,
    profile,
    notifications as user_notifications
)





logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting GridSphere IoT Core...")
    mqtt_manager.start() # [cite: 74, 84]
    yield
    logger.info("Shutting down...")
    mqtt_manager.stop()

app = FastAPI(title="GridSphere Multi-Tenant API", lifespan=lifespan)

# --- UI ROUTE (Placed at the top for priority) ---
@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def serve_dashboard():
    # Looks for index.html in the biomet root folder
    # This goes up one level from app/main.py
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "index.html")
    
    if os.path.exists(file_path):
        return FileResponse(file_path)
    
    return HTMLResponse(
        content=f"<h1>Dashboard File Not Found</h1><p>Looked in: {file_path}</p>", 
        status_code=404
    )

# --- REGISTER ROUTERS ---
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"]) # [cite: 74, 79]
app.include_router(admin.router, prefix="/api/admin", tags=["Admin/Commands"]) # [cite: 78]


# ================================
# ORG ADMIN ROUTES
# ================================

app.include_router(org_dashboard.router, prefix="/api/org-admin", tags=["Org Admin"])
app.include_router(employees.router, prefix="/api/org-admin", tags=["Org Admin"])
app.include_router(org_attendance.router, prefix="/api/org-admin", tags=["Org Admin"])
app.include_router(org_leaves.router, prefix="/api/org-admin", tags=["Org Admin"])
app.include_router(departments.router, prefix="/api/org-admin", tags=["Org Admin"])
app.include_router(org_holidays.router, prefix="/api/org-admin", tags=["Org Admin"])
app.include_router(reports.router, prefix="/api/org-admin", tags=["Org Admin"])
app.include_router(settings.router, prefix="/api/org-admin", tags=["Org Admin"])
app.include_router(org_notifications.router, prefix="/api/org-admin", tags=["Org Admin"])
app.include_router(devices.router, prefix="/api/org-admin", tags=["Org Admin"])
app.include_router(activity.router, prefix="/api/org-admin", tags=["Org Admin"])


# ================================
# USER ROUTES
# ================================

app.include_router(user_dashboard.router, prefix="/api/user", tags=["User"])
app.include_router(user_attendance.router, prefix="/api/user", tags=["User"])
app.include_router(user_leaves.router, prefix="/api/user", tags=["User"])
app.include_router(user_holidays.router, prefix="/api/user", tags=["User"])
app.include_router(profile.router, prefix="/api/user", tags=["User"])
app.include_router(user_notifications.router, prefix="/api/user", tags=["User"])






# --- GLOBAL ERROR HANDLING ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"System Error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})