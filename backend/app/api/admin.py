from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional, List
import uuid

from app.db.models import User, EmployeeRequest, EmployeeRequestStatus, Role, OnboardingStatus, Application
from app.core.security import get_db
from app.api.deps import require_permissions, get_current_active_user

router = APIRouter()

class EmployeeRequestResponse(BaseModel):
    id: str
    user_id: str
    organization: str
    department: Optional[str]
    employee_id: Optional[str]
    designation: Optional[str]
    work_email: Optional[str]
    reason: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    admin_note: Optional[str]
    # Joined fields
    full_name: Optional[str]
    email: Optional[str]
    phone_number: Optional[str]

    class Config:
        from_attributes = True

class RejectRequest(BaseModel):
    reason: str

class RequestInfoRequest(BaseModel):
    note: str

class EmployeeItemResponse(BaseModel):
    id: str
    full_name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None
    role: str
    onboarding_status: str
    employee_id: Optional[str] = None
    organization: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    work_email: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CustomerApplicationSummary(BaseModel):
    id: str
    loan_type: str
    requested_amount: int
    tenure: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class CustomerItemResponse(BaseModel):
    id: str
    full_name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None
    role: str
    onboarding_status: str
    city: Optional[str] = None
    state: Optional[str] = None
    application_count: int
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CustomerDetailResponse(BaseModel):
    id: str
    full_name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    language: Optional[str] = None
    role: str
    onboarding_status: str
    application_count: int
    applications: List[CustomerApplicationSummary]
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

@router.get("/employee-requests", response_model=List[EmployeeRequestResponse])
def list_employee_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_USER_MANAGEMENT"]))
):
    requests = db.query(EmployeeRequest).order_by(EmployeeRequest.created_at.desc()).all()
    
    response = []
    for req in requests:
        user = req.user
        resp = EmployeeRequestResponse(
            id=str(req.id),
            user_id=str(req.user_id),
            organization=req.organization,
            department=req.department,
            employee_id=req.employee_id,
            designation=req.designation,
            work_email=req.work_email,
            reason=req.reason,
            status=req.status,
            created_at=req.created_at,
            updated_at=req.updated_at,
            reviewed_by=str(req.reviewed_by) if req.reviewed_by else None,
            reviewed_at=req.reviewed_at,
            rejection_reason=req.rejection_reason,
            admin_note=req.admin_note,
            full_name=user.full_name if user else None,
            email=user.email if user else None,
            phone_number=user.phone_number if user else None
        )
        response.append(resp)
        
    return response

@router.get("/employee-requests/{id}", response_model=EmployeeRequestResponse)
def get_employee_request(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_USER_MANAGEMENT"]))
):
    try:
        req_id = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID")
        
    req = db.query(EmployeeRequest).filter(EmployeeRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    user = req.user
    return EmployeeRequestResponse(
        id=str(req.id),
        user_id=str(req.user_id),
        organization=req.organization,
        department=req.department,
        employee_id=req.employee_id,
        designation=req.designation,
        work_email=req.work_email,
        reason=req.reason,
        status=req.status,
        created_at=req.created_at,
        updated_at=req.updated_at,
        reviewed_by=str(req.reviewed_by) if req.reviewed_by else None,
        reviewed_at=req.reviewed_at,
        rejection_reason=req.rejection_reason,
        admin_note=req.admin_note,
        full_name=user.full_name if user else None,
        email=user.email if user else None,
        phone_number=user.phone_number if user else None
    )

@router.post("/employee-requests/{id}/approve")
def approve_employee_request(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_USER_MANAGEMENT"]))
):
    try:
        req_id = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID")
        
    req = db.query(EmployeeRequest).filter(EmployeeRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.status == EmployeeRequestStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="Request is already approved")
        
    req.status = EmployeeRequestStatus.APPROVED.value
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    
    user = req.user
    if user:
        user.role = Role.EMPLOYEE.value
        user.onboarding_status = OnboardingStatus.COMPLETED.value
    
    db.commit()
    return {"message": "Request approved successfully"}

@router.post("/employee-requests/{id}/reject")
def reject_employee_request(
    id: str,
    data: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_USER_MANAGEMENT"]))
):
    try:
        req_id = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID")
        
    req = db.query(EmployeeRequest).filter(EmployeeRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    req.status = EmployeeRequestStatus.REJECTED.value
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    req.rejection_reason = data.reason
    
    db.commit()
    return {"message": "Request rejected successfully"}

@router.post("/employee-requests/{id}/request-information")
def request_information(
    id: str,
    data: RequestInfoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_USER_MANAGEMENT"]))
):
    try:
        req_id = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID")
        
    req = db.query(EmployeeRequest).filter(EmployeeRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    req.admin_note = data.note
    db.commit()
    return {"message": "Information requested successfully"}

@router.get("/employees", response_model=List[EmployeeItemResponse])
def list_employees(
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_USER_MANAGEMENT"]))
):
    query = db.query(User).filter(User.role == Role.EMPLOYEE.value)
    if status:
        query = query.filter(User.onboarding_status == status)
        
    users = query.order_by(User.created_at.desc()).all()
    results = []
    for u in users:
        emp_req = db.query(EmployeeRequest).filter(
            EmployeeRequest.user_id == u.id
        ).order_by(EmployeeRequest.created_at.desc()).first()

        item = EmployeeItemResponse(
            id=str(u.id),
            full_name=u.full_name,
            email=u.email,
            phone_number=u.phone_number,
            role=u.role,
            onboarding_status=u.onboarding_status,
            employee_id=emp_req.employee_id if emp_req else None,
            organization=emp_req.organization if emp_req else None,
            department=emp_req.department if emp_req else None,
            designation=emp_req.designation if emp_req else None,
            work_email=emp_req.work_email if emp_req else None,
            created_at=u.created_at,
            last_login_at=u.last_login_at
        )

        if search:
            s = search.lower()
            match = (
                (u.full_name and s in u.full_name.lower()) or
                (s in u.email.lower()) or
                (item.employee_id and s in item.employee_id.lower()) or
                (item.organization and s in item.organization.lower()) or
                (item.department and s in item.department.lower())
            )
            if not match:
                continue

        results.append(item)
    return results

@router.get("/employees/{id}", response_model=EmployeeItemResponse)
def get_employee(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_USER_MANAGEMENT"]))
):
    try:
        user_id = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid employee ID")
        
    user = db.query(User).filter(User.id == user_id, User.role == Role.EMPLOYEE.value).first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp_req = db.query(EmployeeRequest).filter(
        EmployeeRequest.user_id == user.id
    ).order_by(EmployeeRequest.created_at.desc()).first()

    return EmployeeItemResponse(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        role=user.role,
        onboarding_status=user.onboarding_status,
        employee_id=emp_req.employee_id if emp_req else None,
        organization=emp_req.organization if emp_req else None,
        department=emp_req.department if emp_req else None,
        designation=emp_req.designation if emp_req else None,
        work_email=emp_req.work_email if emp_req else None,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )

@router.get("/customers", response_model=List[CustomerItemResponse])
def list_customers(
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_USER_MANAGEMENT"]))
):
    query = db.query(User).filter(User.role == Role.CUSTOMER.value)
    if status:
        query = query.filter(User.onboarding_status == status)
        
    users = query.order_by(User.created_at.desc()).all()
    results = []
    for u in users:
        app_count = db.query(Application).filter(Application.user_id == u.id).count()
        item = CustomerItemResponse(
            id=str(u.id),
            full_name=u.full_name,
            email=u.email,
            phone_number=u.phone_number,
            role=u.role,
            onboarding_status=u.onboarding_status,
            city=u.city,
            state=u.state,
            application_count=app_count,
            created_at=u.created_at,
            last_login_at=u.last_login_at
        )

        if search:
            s = search.lower()
            match = (
                (u.full_name and s in u.full_name.lower()) or
                (s in u.email.lower()) or
                (u.phone_number and s in u.phone_number.lower())
            )
            if not match:
                continue

        results.append(item)
    return results

@router.get("/customers/{id}", response_model=CustomerDetailResponse)
def get_customer(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_USER_MANAGEMENT"]))
):
    try:
        user_id = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID")
        
    user = db.query(User).filter(User.id == user_id, User.role == Role.CUSTOMER.value).first()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    apps = db.query(Application).filter(Application.user_id == user.id).order_by(Application.created_at.desc()).all()
    app_summaries = [
        CustomerApplicationSummary(
            id=str(a.id),
            loan_type=a.loan_type,
            requested_amount=a.requested_amount,
            tenure=a.tenure,
            status=a.status,
            created_at=a.created_at
        )
        for a in apps
    ]

    return CustomerDetailResponse(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        date_of_birth=user.date_of_birth,
        address=user.address,
        city=user.city,
        state=user.state,
        pincode=user.pincode,
        language=user.language,
        role=user.role,
        onboarding_status=user.onboarding_status,
        application_count=len(apps),
        applications=app_summaries,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )
