from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables from root .env
root_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(root_dir / ".env")

from app.db.session import check_db_connection
from app.api.auth import router as auth_router
from app.api.onboarding import router as onboarding_router
from app.api.admin import router as admin_router
from app.api.customer import router as customer_router
from app.api.applications import router as applications_router
from app.api.documents import router as documents_router
from app.api.notifications import router as notifications_router
from app.api.employee import router as employee_router

app = FastAPI(title="PolicyPilot API", description="Banking Policy & Compliance Platform API")

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(onboarding_router, prefix="/onboarding", tags=["onboarding"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(customer_router, prefix="/api/customer", tags=["customer"])
app.include_router(employee_router, prefix="/api/employee", tags=["employee"])
app.include_router(applications_router, prefix="/api/applications", tags=["applications"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])

# Configure CORS for frontend access
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
ADMIN_FRONTEND_URL = os.getenv("ADMIN_FRONTEND_URL", "http://localhost:3001")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000",
        ADMIN_FRONTEND_URL, "http://localhost:3001", "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthResponse(BaseModel):
    status: str
    database: str

@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Check the health of the backend and the database connection.
    """
    db_ok = check_db_connection()
    if db_ok:
        return {"status": "Backend available", "database": "Database available"}
    else:
        # We still return 200 for backend being up, but mark database as unavailable
        # so the frontend knows the backend is running but DB is not.
        return {"status": "Backend available", "database": "Database unavailable"}
