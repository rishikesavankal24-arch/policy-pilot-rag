from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from uuid import UUID

from app.db.session import get_db
from app.core.security import get_current_user
from app.db.models import User, Role, Application, ApplicationStatus, Document, AdditionalInformationRequest, ApplicationAuditEvent

router = APIRouter()


class ApplicationCreate(BaseModel):
    loan_type: str
    requested_amount: int
    tenure: int
    purpose: str
    employment_info: Optional[str] = None
    income_info: Optional[str] = None
    existing_liabilities: Optional[str] = None

    @field_validator("requested_amount")
    @classmethod
    def validate_requested_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Requested amount must be greater than 0.")
        return v

    @field_validator("tenure")
    @classmethod
    def validate_tenure(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Tenure must be greater than 0.")
        return v

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Purpose is required.")
        return v.strip()

    @field_validator("loan_type")
    @classmethod
    def validate_loan_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Loan type is required.")
        return v.strip()

    @field_validator("employment_info", "income_info", "existing_liabilities")
    @classmethod
    def normalize_optional_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed if trimmed else None

class ApplicationUpdate(BaseModel):
    loan_type: Optional[str] = None
    requested_amount: Optional[int] = None
    tenure: Optional[int] = None
    purpose: Optional[str] = None
    employment_info: Optional[str] = None
    income_info: Optional[str] = None
    existing_liabilities: Optional[str] = None

class DocumentItemResponse(BaseModel):
    id: UUID
    application_id: Optional[UUID] = None
    document_type: str
    file_url: str
    status: str
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class InformationRequestItemResponse(BaseModel):
    id: UUID
    application_id: UUID
    title: str
    description: str
    requested_document_type: Optional[str] = None
    status: str
    response_document_id: Optional[UUID] = None
    response_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ApplicationResponse(BaseModel):
    id: UUID
    user_id: UUID
    loan_type: str
    requested_amount: int
    tenure: int
    purpose: str
    employment_info: Optional[str] = None
    income_info: Optional[str] = None
    existing_liabilities: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ApplicationDetailResponse(BaseModel):
    application: ApplicationResponse
    documents: List[DocumentItemResponse]
    information_requests: List[InformationRequestItemResponse] = []

@router.get("", response_model=List[ApplicationResponse])
@router.get("/", response_model=List[ApplicationResponse])
def get_applications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="Unauthorized")
    apps = db.query(Application).filter(Application.user_id == current_user.id).order_by(Application.created_at.desc()).all()
    return apps

@router.get("/{app_id}", response_model=ApplicationDetailResponse)
def get_application(app_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="Unauthorized")
    app = db.query(Application).filter(Application.id == app_id, Application.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    docs = db.query(Document).filter(Document.application_id == app.id).order_by(Document.created_at.desc()).all()
    
    docs_formatted = [
        DocumentItemResponse(
            id=d.id,
            application_id=d.application_id,
            document_type=d.document_type,
            file_url=f"/api/documents/{d.id}/content",
            status=d.status,
            reviewed_at=d.reviewed_at,
            review_notes=("Reason not recorded" if (d.review_notes and d.review_notes.strip().lower() in ["nil", "none"]) else d.review_notes),
            created_at=d.created_at
        )
        for d in docs
    ]

    info_requests = db.query(AdditionalInformationRequest).filter(
        AdditionalInformationRequest.application_id == app.id
    ).order_by(AdditionalInformationRequest.created_at.desc()).all()

    requests_formatted = [
        InformationRequestItemResponse(
            id=ir.id,
            application_id=ir.application_id,
            title=ir.title,
            description=ir.description,
            requested_document_type=ir.requested_document_type,
            status=ir.status,
            response_document_id=ir.response_document_id,
            response_notes=ir.response_notes,
            created_at=ir.created_at,
            responded_at=ir.responded_at
        )
        for ir in info_requests
    ]
    
    return {
        "application": app,
        "documents": docs_formatted,
        "information_requests": requests_formatted
    }

@router.post("", response_model=ApplicationResponse)
@router.post("/", response_model=ApplicationResponse)
def create_application(app_data: ApplicationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    new_app = Application(
        user_id=current_user.id,
        loan_type=app_data.loan_type,
        requested_amount=app_data.requested_amount,
        tenure=app_data.tenure,
        purpose=app_data.purpose,
        employment_info=app_data.employment_info,
        income_info=app_data.income_info,
        existing_liabilities=app_data.existing_liabilities,
        status=ApplicationStatus.DRAFT.value
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    return new_app

@router.patch("/{app_id}", response_model=ApplicationResponse)
def update_application(app_id: UUID, app_data: ApplicationUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    app = db.query(Application).filter(Application.id == app_id, Application.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if app.status != ApplicationStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Only draft applications can be updated")
        
    update_dict = app_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(app, key, value)
        
    db.commit()
    db.refresh(app)
    return app

@router.post("/{app_id}/submit", response_model=ApplicationResponse)
def submit_application(app_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    app = db.query(Application).filter(Application.id == app_id, Application.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if app.status != ApplicationStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Application is not in DRAFT status")
        
    app.status = ApplicationStatus.SUBMITTED.value
    audit = ApplicationAuditEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="APPLICATION_SUBMITTED",
        title="Application Submitted",
        description=f"Applicant completed and formally submitted the loan application for {app.loan_type} (₹{app.requested_amount:,})."
    )
    db.add(audit)
    db.commit()
    db.refresh(app)
    return app
