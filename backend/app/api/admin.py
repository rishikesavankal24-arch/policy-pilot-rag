from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid

from app.db.models import (
    User, EmployeeRequest, EmployeeRequestStatus, Role, OnboardingStatus, Application,
    Policy, PolicyVersion, PolicyStatus, RegulatoryAuthority, PolicyApplicability
)
from app.core.security import get_db
from app.api.deps import require_permissions, get_current_active_user
from app.services.policy_file_service import PolicyFileService
from app.services.policy_lifecycle_service import (
    PolicyLifecycleService,
    PolicyLifecycleError,
    PolicyLifecycleValidationError,
    PolicyLifecycleNotFoundError,
    PolicyLifecycleConflictError
)
from app.services.policy_metadata_service import (
    RegulatoryAuthorityService,
    PolicyMetadataService,
    PolicyApplicabilityService,
    PolicyMetadataValidationError,
    PolicyMetadataNotFoundError,
    PolicyMetadataConflictError,
    parse_uuid
)

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


# ==============================================================================
# M08.3 — Policy Document Upload & File Access (Admin Controlled)
# ==============================================================================

class PolicyVersionUploadResponse(BaseModel):
    id: str
    policy_id: str
    version_number: str
    changelog: Optional[str] = None
    file_url: Optional[str] = None
    file_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/policies/{policy_id}/versions/upload", response_model=PolicyVersionUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_policy_version_document(
    policy_id: uuid.UUID,
    file: UploadFile = File(...),
    changelog: Optional[str] = Form(None),
    effective_from: Optional[datetime] = Form(None),
    effective_to: Optional[datetime] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """
    Authorized admin endpoint for uploading and attaching a validated policy source document.
    Enforces ADMIN_POLICY_MANAGEMENT permission.
    """
    try:
        file_bytes = await file.read()
        version = PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy_id,
            filename=file.filename or "policy_document.pdf",
            file_bytes=file_bytes,
            changelog=changelog,
            effective_from=effective_from,
            effective_to=effective_to,
            created_by=current_user.id
        )
        return PolicyVersionUploadResponse(
            id=str(version.id),
            policy_id=str(version.policy_id),
            version_number=version.version_number,
            changelog=version.changelog,
            file_url=version.file_url,
            file_hash=version.file_hash,
            file_size_bytes=version.file_size_bytes,
            page_count=version.page_count,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
            created_by=str(version.created_by) if version.created_by else None,
            created_at=version.created_at
        )
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyMetadataConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PolicyMetadataValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/policies/{policy_id}/versions/{version_id}/file")
def get_policy_version_document_file(
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """
    Authorized endpoint to retrieve the stored policy document file.
    Does not expose arbitrary filesystem paths.
    """
    try:
        file_path, version = PolicyFileService.get_policy_version_file(
            db=db,
            policy_id=policy_id,
            version_id=version_id
        )
        media_type = "application/pdf"
        if file_path.suffix.lower() == ".png":
            media_type = "image/png"
        elif file_path.suffix.lower() in (".jpg", ".jpeg"):
            media_type = "image/jpeg"

        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type=media_type
        )
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


class PolicyLifecycleResponse(BaseModel):
    id: str
    policy_code: str
    title: str
    status: str
    current_version_id: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.post("/policies/{policy_id}/publish", response_model=PolicyLifecycleResponse)
def publish_policy_endpoint(
    policy_id: uuid.UUID,
    version_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Publish a draft policy."""
    try:
        policy = PolicyLifecycleService.publish_policy(
            db=db,
            policy_id=policy_id,
            actor_id=current_user.id,
            version_id=version_id
        )
        return PolicyLifecycleResponse(
            id=str(policy.id),
            policy_code=policy.policy_code,
            title=policy.title,
            status=policy.status.value,
            current_version_id=str(policy.current_version_id) if policy.current_version_id else None,
            updated_at=policy.updated_at
        )
    except PolicyLifecycleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyLifecycleConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PolicyLifecycleValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/policies/{policy_id}/activate", response_model=PolicyLifecycleResponse)
def activate_policy_endpoint(
    policy_id: uuid.UUID,
    version_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Activate a published policy version."""
    try:
        policy = PolicyLifecycleService.activate_policy_version(
            db=db,
            policy_id=policy_id,
            version_id=version_id,
            actor_id=current_user.id
        )
        return PolicyLifecycleResponse(
            id=str(policy.id),
            policy_code=policy.policy_code,
            title=policy.title,
            status=policy.status.value,
            current_version_id=str(policy.current_version_id) if policy.current_version_id else None,
            updated_at=policy.updated_at
        )
    except PolicyLifecycleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyLifecycleConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PolicyLifecycleValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/policies/{policy_id}/supersede", response_model=PolicyLifecycleResponse)
def supersede_policy_endpoint(
    policy_id: uuid.UUID,
    new_version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Supersede an active policy with a new version."""
    try:
        policy = PolicyLifecycleService.supersede_policy(
            db=db,
            policy_id=policy_id,
            new_version_id=new_version_id,
            actor_id=current_user.id
        )
        return PolicyLifecycleResponse(
            id=str(policy.id),
            policy_code=policy.policy_code,
            title=policy.title,
            status=policy.status.value,
            current_version_id=str(policy.current_version_id) if policy.current_version_id else None,
            updated_at=policy.updated_at
        )
    except PolicyLifecycleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyLifecycleConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PolicyLifecycleValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/policies/{policy_id}/archive", response_model=PolicyLifecycleResponse)
def archive_policy_endpoint(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Archive a policy."""
    try:
        policy = PolicyLifecycleService.archive_policy(
            db=db,
            policy_id=policy_id,
            actor_id=current_user.id
        )
        return PolicyLifecycleResponse(
            id=str(policy.id),
            policy_code=policy.policy_code,
            title=policy.title,
            status=policy.status.value,
            current_version_id=str(policy.current_version_id) if policy.current_version_id else None,
            updated_at=policy.updated_at
        )
    except PolicyLifecycleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyLifecycleConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PolicyLifecycleValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/policies/{policy_id}/history")
def get_policy_history_endpoint(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Retrieve full version history with status context for a policy."""
    try:
        history = PolicyLifecycleService.get_policy_version_history(db=db, policy_id=policy_id)
        return history
    except PolicyLifecycleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==============================================================================
# M08.5 — Admin Management APIs: Schemas & Endpoints
# ==============================================================================

# --- Regulatory Authority Schemas ---

class RegulatoryAuthorityCreateRequest(BaseModel):
    name: str
    short_name: str
    authority_type: Optional[str] = "CENTRAL_BANK"
    jurisdiction: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = True


class RegulatoryAuthorityUpdateRequest(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    authority_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RegulatoryAuthorityResponse(BaseModel):
    id: str
    name: str
    short_name: str
    authority_type: str
    jurisdiction: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Policy Metadata Schemas ---

class PolicyCreateRequest(BaseModel):
    policy_code: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    policy_type: Optional[str] = None
    institution: Optional[str] = None
    jurisdiction: Optional[str] = None
    regulatory_authority_id: Optional[str] = None


class PolicyUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    policy_type: Optional[str] = None
    institution: Optional[str] = None
    jurisdiction: Optional[str] = None
    regulatory_authority_id: Optional[str] = None


class PolicyResponse(BaseModel):
    id: str
    policy_code: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    policy_type: Optional[str] = None
    status: str
    institution: Optional[str] = None
    jurisdiction: Optional[str] = None
    current_version_id: Optional[str] = None
    regulatory_authority_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PolicyListResponse(BaseModel):
    items: List[PolicyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Policy Applicability Schemas ---

class ApplicabilityCreateRequest(BaseModel):
    institution: Optional[str] = None
    jurisdiction: Optional[str] = None
    loan_type: Optional[str] = None
    department: Optional[str] = None


class ApplicabilityResponse(BaseModel):
    id: str
    policy_id: str
    institution: Optional[str] = None
    jurisdiction: Optional[str] = None
    loan_type: Optional[str] = None
    department: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Policy Version Update Schemas ---

class PolicyVersionUpdateRequest(BaseModel):
    changelog: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    file_hash: Optional[str] = None
    file_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    version_number: Optional[str] = None


class PolicyVersionResponse(BaseModel):
    id: str
    policy_id: str
    version_number: str
    changelog: Optional[str] = None
    file_url: Optional[str] = None
    file_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    created_by: Optional[str] = None
    published_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==============================================================================
# A. Regulatory Authority Endpoints
# ==============================================================================

@router.post("/regulatory-authorities", response_model=RegulatoryAuthorityResponse, status_code=status.HTTP_201_CREATED)
def create_regulatory_authority(
    body: RegulatoryAuthorityCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Create a new regulatory authority."""
    try:
        auth = RegulatoryAuthorityService.create_authority(
            db=db,
            name=body.name,
            short_name=body.short_name,
            authority_type=body.authority_type or "CENTRAL_BANK",
            jurisdiction=body.jurisdiction,
            website_url=body.website_url,
            description=body.description,
            is_active=body.is_active if body.is_active is not None else True
        )
        return RegulatoryAuthorityResponse(
            id=str(auth.id),
            name=auth.name,
            short_name=auth.short_name,
            authority_type=auth.authority_type,
            jurisdiction=auth.jurisdiction,
            website_url=auth.website_url,
            description=auth.description,
            is_active=auth.is_active,
            created_at=auth.created_at,
            updated_at=auth.updated_at
        )
    except PolicyMetadataConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PolicyMetadataValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/regulatory-authorities", response_model=List[RegulatoryAuthorityResponse])
def list_regulatory_authorities(
    is_active: Optional[bool] = None,
    authority_type: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """List regulatory authorities with optional filters."""
    try:
        items = RegulatoryAuthorityService.list_authorities(
            db=db,
            is_active=is_active,
            authority_type=authority_type,
            jurisdiction=jurisdiction
        )
        return [
            RegulatoryAuthorityResponse(
                id=str(a.id),
                name=a.name,
                short_name=a.short_name,
                authority_type=a.authority_type,
                jurisdiction=a.jurisdiction,
                website_url=a.website_url,
                description=a.description,
                is_active=a.is_active,
                created_at=a.created_at,
                updated_at=a.updated_at
            )
            for a in items
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/regulatory-authorities/{authority_id}", response_model=RegulatoryAuthorityResponse)
def get_regulatory_authority(
    authority_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Retrieve a regulatory authority by ID."""
    try:
        auth = RegulatoryAuthorityService.get_authority(db=db, authority_id=authority_id)
        return RegulatoryAuthorityResponse(
            id=str(auth.id),
            name=auth.name,
            short_name=auth.short_name,
            authority_type=auth.authority_type,
            jurisdiction=auth.jurisdiction,
            website_url=auth.website_url,
            description=auth.description,
            is_active=auth.is_active,
            created_at=auth.created_at,
            updated_at=auth.updated_at
        )
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyMetadataValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/regulatory-authorities/{authority_id}", response_model=RegulatoryAuthorityResponse)
def update_regulatory_authority(
    authority_id: uuid.UUID,
    body: RegulatoryAuthorityUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Update regulatory authority metadata."""
    try:
        auth = RegulatoryAuthorityService.update_authority(
            db=db,
            authority_id=authority_id,
            name=body.name,
            short_name=body.short_name,
            authority_type=body.authority_type,
            jurisdiction=body.jurisdiction,
            website_url=body.website_url,
            description=body.description,
            is_active=body.is_active
        )
        return RegulatoryAuthorityResponse(
            id=str(auth.id),
            name=auth.name,
            short_name=auth.short_name,
            authority_type=auth.authority_type,
            jurisdiction=auth.jurisdiction,
            website_url=auth.website_url,
            description=auth.description,
            is_active=auth.is_active,
            created_at=auth.created_at,
            updated_at=auth.updated_at
        )
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyMetadataConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PolicyMetadataValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/regulatory-authorities/{authority_id}/deactivate", response_model=RegulatoryAuthorityResponse)
def deactivate_regulatory_authority(
    authority_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Deactivate a regulatory authority."""
    try:
        auth = RegulatoryAuthorityService.deactivate_authority(db=db, authority_id=authority_id)
        return RegulatoryAuthorityResponse(
            id=str(auth.id),
            name=auth.name,
            short_name=auth.short_name,
            authority_type=auth.authority_type,
            jurisdiction=auth.jurisdiction,
            website_url=auth.website_url,
            description=auth.description,
            is_active=auth.is_active,
            created_at=auth.created_at,
            updated_at=auth.updated_at
        )
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyMetadataValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==============================================================================
# B. Policy Metadata Endpoints
# ==============================================================================

@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    body: PolicyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Create a new policy in DRAFT status."""
    try:
        policy = PolicyMetadataService.create_policy_metadata(
            db=db,
            policy_code=body.policy_code,
            title=body.title,
            description=body.description,
            category=body.category,
            policy_type=body.policy_type,
            institution=body.institution,
            jurisdiction=body.jurisdiction,
            regulatory_authority_id=body.regulatory_authority_id,
            created_by=current_user.id
        )
        return PolicyResponse(
            id=str(policy.id),
            policy_code=policy.policy_code,
            title=policy.title,
            description=policy.description,
            category=policy.category,
            policy_type=policy.policy_type,
            status=policy.status.value,
            institution=policy.institution,
            jurisdiction=policy.jurisdiction,
            current_version_id=str(policy.current_version_id) if policy.current_version_id else None,
            regulatory_authority_id=str(policy.regulatory_authority_id) if policy.regulatory_authority_id else None,
            created_by=str(policy.created_by) if policy.created_by else None,
            created_at=policy.created_at,
            updated_at=policy.updated_at
        )
    except PolicyMetadataConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (PolicyMetadataValidationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/policies", response_model=PolicyListResponse)
def list_policies(
    status: Optional[str] = None,
    policy_code: Optional[str] = None,
    title: Optional[str] = None,
    category: Optional[str] = None,
    policy_type: Optional[str] = None,
    institution: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    regulatory_authority_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """List policies with administrative filtering and pagination."""
    try:
        query = db.query(Policy)
        if status:
            norm_status = status.strip().upper()
            try:
                p_status = PolicyStatus(norm_status)
                query = query.filter(Policy.status == p_status)
            except ValueError:
                raise PolicyMetadataValidationError(f"Invalid status '{status}'.")
        if policy_code:
            query = query.filter(func.lower(Policy.policy_code) == policy_code.strip().lower())
        if title:
            query = query.filter(func.lower(Policy.title).contains(title.strip().lower()))
        if category:
            query = query.filter(func.lower(Policy.category) == category.strip().lower())
        if policy_type:
            query = query.filter(func.lower(Policy.policy_type) == policy_type.strip().lower())
        if institution:
            query = query.filter(func.lower(Policy.institution) == institution.strip().lower())
        if jurisdiction:
            query = query.filter(func.lower(Policy.jurisdiction) == jurisdiction.strip().lower())
        if regulatory_authority_id:
            auth_id = parse_uuid(regulatory_authority_id, "regulatory_authority_id")
            query = query.filter(Policy.regulatory_authority_id == auth_id)
        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(func.lower(Policy.title).like(s) | func.lower(Policy.policy_code).like(s))

        total = query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        items = query.order_by(Policy.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return PolicyListResponse(
            items=[
                PolicyResponse(
                    id=str(p.id),
                    policy_code=p.policy_code,
                    title=p.title,
                    description=p.description,
                    category=p.category,
                    policy_type=p.policy_type,
                    status=p.status.value,
                    institution=p.institution,
                    jurisdiction=p.jurisdiction,
                    current_version_id=str(p.current_version_id) if p.current_version_id else None,
                    regulatory_authority_id=str(p.regulatory_authority_id) if p.regulatory_authority_id else None,
                    created_by=str(p.created_by) if p.created_by else None,
                    created_at=p.created_at,
                    updated_at=p.updated_at
                )
                for p in items
            ],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except PolicyMetadataValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Retrieve a policy by ID."""
    try:
        policy = PolicyMetadataService.get_policy(db=db, policy_id=policy_id)
        return PolicyResponse(
            id=str(policy.id),
            policy_code=policy.policy_code,
            title=policy.title,
            description=policy.description,
            category=policy.category,
            policy_type=policy.policy_type,
            status=policy.status.value,
            institution=policy.institution,
            jurisdiction=policy.jurisdiction,
            current_version_id=str(policy.current_version_id) if policy.current_version_id else None,
            regulatory_authority_id=str(policy.regulatory_authority_id) if policy.regulatory_authority_id else None,
            created_by=str(policy.created_by) if policy.created_by else None,
            created_at=policy.created_at,
            updated_at=policy.updated_at
        )
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyMetadataValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/policies/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: uuid.UUID,
    body: PolicyUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Update mutable policy metadata (DRAFT only)."""
    try:
        policy = PolicyMetadataService.update_policy_metadata(
            db=db,
            policy_id=policy_id,
            title=body.title,
            description=body.description,
            category=body.category,
            policy_type=body.policy_type,
            institution=body.institution,
            jurisdiction=body.jurisdiction,
            regulatory_authority_id=body.regulatory_authority_id
        )
        return PolicyResponse(
            id=str(policy.id),
            policy_code=policy.policy_code,
            title=policy.title,
            description=policy.description,
            category=policy.category,
            policy_type=policy.policy_type,
            status=policy.status.value,
            institution=policy.institution,
            jurisdiction=policy.jurisdiction,
            current_version_id=str(policy.current_version_id) if policy.current_version_id else None,
            regulatory_authority_id=str(policy.regulatory_authority_id) if policy.regulatory_authority_id else None,
            created_by=str(policy.created_by) if policy.created_by else None,
            created_at=policy.created_at,
            updated_at=policy.updated_at
        )
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (PolicyMetadataValidationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PolicyMetadataConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# ==============================================================================
# C. Policy Applicability Endpoints
# ==============================================================================

@router.post("/policies/{policy_id}/applicability", response_model=ApplicabilityResponse, status_code=status.HTTP_201_CREATED)
def add_policy_applicability(
    policy_id: uuid.UUID,
    body: ApplicabilityCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Add an applicability scope rule to a policy."""
    try:
        app_rule = PolicyApplicabilityService.add_applicability(
            db=db,
            policy_id=policy_id,
            institution=body.institution,
            jurisdiction=body.jurisdiction,
            loan_type=body.loan_type,
            department=body.department
        )
        return ApplicabilityResponse(
            id=str(app_rule.id),
            policy_id=str(app_rule.policy_id),
            institution=app_rule.institution,
            jurisdiction=app_rule.jurisdiction,
            loan_type=app_rule.loan_type,
            department=app_rule.department,
            created_at=app_rule.created_at,
            updated_at=app_rule.updated_at
        )
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyMetadataConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PolicyMetadataValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/policies/{policy_id}/applicability", response_model=List[ApplicabilityResponse])
def list_policy_applicability(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """List all applicability rules defined for a policy."""
    try:
        items = PolicyApplicabilityService.list_applicabilities(db=db, policy_id=policy_id)
        return [
            ApplicabilityResponse(
                id=str(a.id),
                policy_id=str(a.policy_id),
                institution=a.institution,
                jurisdiction=a.jurisdiction,
                loan_type=a.loan_type,
                department=a.department,
                created_at=a.created_at,
                updated_at=a.updated_at
            )
            for a in items
        ]
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyMetadataValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/policies/{policy_id}/applicability/{applicability_id}")
def delete_policy_applicability(
    policy_id: uuid.UUID,
    applicability_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """Delete an applicability rule from a policy."""
    try:
        PolicyMetadataService.get_policy(db=db, policy_id=policy_id)
        PolicyApplicabilityService.remove_applicability(db=db, applicability_id=applicability_id)
        return {"status": "deleted", "applicability_id": str(applicability_id)}
    except PolicyMetadataNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyMetadataValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==============================================================================
# D. Policy Version Metadata Management
# ==============================================================================

@router.patch("/policies/{policy_id}/versions/{version_id}", response_model=PolicyVersionResponse)
def update_policy_version_metadata(
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    body: PolicyVersionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["ADMIN_POLICY_MANAGEMENT"]))
):
    """
    Update mutable version metadata (changelog, effective dates) while strictly enforcing
    immutability of file_hash, file_url, file_size_bytes, page_count, and version_number.
    """
    try:
        attempted = {}
        for f in ["file_hash", "file_url", "file_size_bytes", "page_count", "version_number"]:
            val = getattr(body, f)
            if val is not None:
                attempted[f] = val

        v = PolicyLifecycleService.update_policy_version_metadata(
            db=db,
            policy_id=policy_id,
            version_id=version_id,
            changelog=body.changelog,
            effective_from=body.effective_from,
            effective_to=body.effective_to,
            attempted_immutable_fields=attempted
        )
        return PolicyVersionResponse(
            id=str(v.id),
            policy_id=str(v.policy_id),
            version_number=v.version_number,
            changelog=v.changelog,
            file_url=v.file_url,
            file_hash=v.file_hash,
            file_size_bytes=v.file_size_bytes,
            page_count=v.page_count,
            effective_from=v.effective_from,
            effective_to=v.effective_to,
            created_by=str(v.created_by) if v.created_by else None,
            published_by=str(v.published_by) if v.published_by else None,
            created_at=v.created_at,
            updated_at=v.updated_at
        )
    except (PolicyMetadataNotFoundError, PolicyLifecycleNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (PolicyMetadataConflictError, PolicyLifecycleConflictError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (PolicyMetadataValidationError, PolicyLifecycleValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

