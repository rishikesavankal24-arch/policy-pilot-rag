from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.models import User, EmployeeRequest, OnboardingStatus, Role, EmployeeRequestStatus
from app.core.security import get_current_user, get_db

router = APIRouter()

from typing import Optional

class CustomerOnboardingData(BaseModel):
    phone_number: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    language: str = "en"
    consent_accepted: bool

class EmployeeOnboardingData(BaseModel):
    phone_number: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    language: str = "en"
    consent_accepted: bool
    organization: str
    department: str
    employee_id: str
    designation: str
    work_email: str
    reason: str

@router.get("/")
def get_onboarding_status(current_user: User = Depends(get_current_user)):
    return {
        "status": current_user.onboarding_status,
        "requested_role": current_user.requested_role
    }

@router.post("/customer")
def onboard_customer(data: CustomerOnboardingData, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not data.consent_accepted:
        raise HTTPException(status_code=400, detail="Consent is required")
        
    current_user.phone_number = data.phone_number
    current_user.language = data.language
    current_user.consent_accepted = data.consent_accepted
    if data.full_name:
        current_user.full_name = data.full_name
    if data.email:
        # Check if email is available, but for now just set it
        current_user.email = data.email
    
    current_user.onboarding_status = OnboardingStatus.COMPLETED.value
    current_user.requested_role = Role.CUSTOMER.value
    current_user.role = Role.CUSTOMER.value
    
    db.commit()
    return {"message": "Onboarding completed successfully"}

@router.post("/employee")
def onboard_employee(data: EmployeeOnboardingData, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if a request already exists
    existing = db.query(EmployeeRequest).filter(EmployeeRequest.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee request already submitted")
        
    if not data.consent_accepted:
        raise HTTPException(status_code=400, detail="Consent is required")
        
    current_user.phone_number = data.phone_number
    current_user.language = data.language
    current_user.consent_accepted = data.consent_accepted
    if data.full_name:
        current_user.full_name = data.full_name
    if data.email:
        current_user.email = data.email
        
    import os
    from datetime import datetime, timezone
    
    is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"
    auto_approve = os.getenv("EMPLOYEE_AUTO_APPROVE", "false").lower() == "true"
    
    req_status = EmployeeRequestStatus.PENDING.value
    if is_dev and auto_approve:
        req_status = EmployeeRequestStatus.APPROVED.value
        current_user.role = Role.EMPLOYEE.value
        current_user.onboarding_status = OnboardingStatus.COMPLETED.value
    else:
        current_user.onboarding_status = OnboardingStatus.PENDING_VERIFICATION.value
        
    current_user.requested_role = Role.EMPLOYEE.value
        
    req = EmployeeRequest(
        user_id=current_user.id,
        organization=data.organization,
        department=data.department,
        employee_id=data.employee_id,
        designation=data.designation,
        work_email=data.work_email,
        reason=data.reason,
        status=req_status
    )
    
    if is_dev and auto_approve:
        req.admin_note = "SYSTEM_DEVELOPMENT_AUTO_APPROVAL"
        req.reviewed_at = datetime.now(timezone.utc)
        
    db.add(req)
    
    db.commit()
    return {"message": "Employee access requested successfully"}
