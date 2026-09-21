from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from app.db.session import get_db
from app.db.models import (
    User, Role, OnboardingStatus, Application, ApplicationStatus,
    Document, DocumentStatus, Notification, EmployeeRequest, EmployeeRequestStatus,
    InformationRequestStatus, AdditionalInformationRequest, ApplicationAuditEvent,
    ComplianceChecklistStatus, ComplianceChecklistItem, ComplianceReviewNote
)
from app.api.deps import require_verified_employee, check_employee_review_not_owner

router = APIRouter()

# Explicit Pydantic response schemas for Employee Application Queue and Dossier
class EmployeeApplicationQueueItem(BaseModel):
    id: str
    user_id: str
    customer_display_name: str
    applicant_name: str
    applicant_email: str
    loan_type: str
    requested_amount: int
    tenure: int
    purpose: str
    status: str
    submitted_date: Optional[str] = None
    created_at: Optional[str] = None
    last_updated_time: Optional[str] = None
    updated_at: Optional[str] = None
    assigned_employee: Optional[str] = None
    is_own_application: bool = False
    document_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class ApplicationDetailInfo(BaseModel):
    id: str
    user_id: str
    loan_type: str
    requested_amount: int
    tenure: int
    purpose: str
    employment_info: Optional[str] = None
    income_info: Optional[str] = None
    existing_liabilities: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ApplicantKYCInfo(BaseModel):
    id: Optional[str] = None
    full_name: str
    email: str
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentItem(BaseModel):
    id: str
    document_type: str
    file_url: str
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class InformationRequestItem(BaseModel):
    id: str
    application_id: str
    requested_by: str
    title: str
    description: str
    requested_document_type: Optional[str] = None
    status: str
    response_document_id: Optional[str] = None
    response_document_url: Optional[str] = None
    response_notes: Optional[str] = None
    created_at: Optional[str] = None
    responded_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentReviewRequest(BaseModel):
    status: str
    reason: Optional[str] = None

class InformationRequestCreate(BaseModel):
    title: str
    description: str
    requested_document_type: Optional[str] = None

class TimelineItem(BaseModel):
    event: str
    title: str
    description: str
    timestamp: Optional[str] = None

class ComplianceSummary(BaseModel):
    status: str
    module: str
    compliance_score: Optional[float] = None
    flags: List[str] = []
    notes: str

class DecisionSummary(BaseModel):
    status: str
    module: str
    can_decide: bool
    notes: str

class EmployeeApplicationDetailResponse(BaseModel):
    application: ApplicationDetailInfo
    applicant: ApplicantKYCInfo
    documents: List[DocumentItem]
    information_requests: List[InformationRequestItem] = []
    timeline: List[TimelineItem]
    compliance: ComplianceSummary
    decision: DecisionSummary

class ComplianceChecklistItemResponse(BaseModel):
    id: str
    application_id: str
    item_key: str
    category: str
    title: str
    description: Optional[str] = None
    status: str
    notes: Optional[str] = None
    display_order: int
    updated_by: Optional[str] = None
    updated_by_name: Optional[str] = None
    updated_at: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ComplianceChecklistUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

class ComplianceNoteCreate(BaseModel):
    note: str

class ComplianceNoteResponse(BaseModel):
    id: str
    application_id: str
    author_id: str
    author_name: str
    author_email: str
    note: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class ComplianceAuditEventItem(BaseModel):
    id: str
    event_type: str
    title: str
    description: str
    user_id: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ComplianceWorkspaceResponse(BaseModel):
    application: ApplicationDetailInfo
    applicant: ApplicantKYCInfo
    documents: List[DocumentItem]
    checklist_items: List[ComplianceChecklistItemResponse]
    review_notes: List[ComplianceNoteResponse]
    information_requests: List[InformationRequestItem]
    audit_events: List[ComplianceAuditEventItem]
    ai_rag_boundary: dict

STANDARD_COMPLIANCE_CHECKLIST = [
    {
        "item_key": "mandatory_kyc_presence",
        "category": "DOCUMENT_COMPLETENESS",
        "title": "Identity & KYC Document Completeness",
        "description": "Verify government-issued photo ID (Aadhaar/PAN/Passport) and proof of address are present and legible.",
        "display_order": 1,
    },
    {
        "item_key": "income_obligation_consistency",
        "category": "FINANCIAL_VERIFICATION",
        "title": "Income & Existing Liabilities Verification",
        "description": "Verify declared salary/business income against uploaded financial records and bank statements.",
        "display_order": 2,
    },
    {
        "item_key": "facility_purpose_validation",
        "category": "LOAN_PURPOSE_ALIGNMENT",
        "title": "Credit Facility Purpose Alignment",
        "description": "Assess declared loan purpose against institutional risk parameters and eligible product categories.",
        "display_order": 3,
    },
    {
        "item_key": "applicant_profile_consistency",
        "category": "DATA_CONSISTENCY",
        "title": "Applicant Demographic & Data Consistency",
        "description": "Confirm applicant personal details match records across all submitted documentation without discrepancy.",
        "display_order": 4,
    },
    {
        "item_key": "preliminary_policy_evidence",
        "category": "POLICY_EVIDENCE",
        "title": "Regulatory Policy Pre-check Evidence",
        "description": "Confirm pre-underwriting compliance checks adhere to mandatory retail lending standards.",
        "display_order": 5,
    },
]


@router.get("/dashboard/summary")
def get_employee_dashboard_summary(
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Returns operational summary metrics for the Employee Portal.
    Only applications that are NOT in DRAFT status are included in operational counts.
    """
    # Exclude drafts from operational queue metrics
    base_apps_query = db.query(Application).filter(Application.status != ApplicationStatus.DRAFT.value)
    
    total_submitted = base_apps_query.count()
    under_review_count = base_apps_query.filter(Application.status == ApplicationStatus.UNDER_REVIEW.value).count()
    submitted_count = base_apps_query.filter(Application.status == ApplicationStatus.SUBMITTED.value).count()
    additional_info_count = base_apps_query.filter(Application.status == ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value).count()
    approved_count = base_apps_query.filter(Application.status == ApplicationStatus.APPROVED.value).count()
    declined_count = base_apps_query.filter(Application.status == ApplicationStatus.DECLINED.value).count()
    
    # Documents in queue across submitted applications
    pending_docs_count = (
        db.query(Document)
        .join(Application, Document.application_id == Application.id)
        .filter(Application.status != ApplicationStatus.DRAFT.value)
        .filter(Document.status.in_(["UPLOADED", "PROCESSING"]))
        .count()
    )
    
    # Recent non-draft applications
    recent_apps = (
        base_apps_query
        .order_by(Application.created_at.desc())
        .limit(6)
        .all()
    )
    
    recent_list = []
    for app in recent_apps:
        applicant = db.query(User).filter(User.id == app.user_id).first()
        applicant_name = applicant.full_name if (applicant and applicant.full_name) else (applicant.email if applicant else "Unknown")
        recent_list.append({
            "id": str(app.id),
            "user_id": str(app.user_id),
            "loan_type": app.loan_type,
            "requested_amount": app.requested_amount,
            "tenure": app.tenure,
            "status": app.status,
            "applicant_name": applicant_name,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "is_own_application": str(app.user_id) == str(current_user.id)
        })
        
    # Fetch employee request details
    emp_req = (
        db.query(EmployeeRequest)
        .filter(EmployeeRequest.user_id == current_user.id)
        .order_by(EmployeeRequest.created_at.desc())
        .first()
    )

    return {
        "metrics": {
            "total_submitted_applications": total_submitted,
            "under_review": under_review_count,
            "submitted": submitted_count,
            "additional_info_required": additional_info_count,
            "approved": approved_count,
            "declined": declined_count,
            "my_assignments": 0,
            "pending_documents": pending_docs_count
        },
        "recent_applications": recent_list,
        "employee_info": {
            "id": str(current_user.id),
            "full_name": current_user.full_name or "Authorized Officer",
            "email": current_user.email,
            "organization": emp_req.organization if emp_req else "PolicyPilot Demo Bank",
            "department": emp_req.department if (emp_req and emp_req.department) else "Retail Credit Operations",
            "designation": emp_req.designation if (emp_req and emp_req.designation) else "Senior Credit Officer",
            "employee_id": emp_req.employee_id if (emp_req and emp_req.employee_id) else "PP-DEMO-EMP-001"
        }
    }


@router.get("/applications", response_model=List[EmployeeApplicationQueueItem])
def get_employee_applications(
    status: Optional[str] = Query(None, description="Filter by application status"),
    loan_type: Optional[str] = Query(None, description="Filter by loan type"),
    search: Optional[str] = Query(None, description="Search applicant name, email, or application ID"),
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Returns non-draft applications in the enterprise queue.
    Supports filtering and searching.
    Customers' drafts are strictly excluded from the queue.
    """
    query = db.query(Application).filter(Application.status != ApplicationStatus.DRAFT.value)
    
    if status and status.upper() != "ALL":
        query = query.filter(Application.status == status.upper())
        
    if loan_type and loan_type.upper() != "ALL":
        query = query.filter(Application.loan_type.ilike(f"%{loan_type}%"))
        
    apps = query.order_by(Application.created_at.desc()).all()
    
    result = []
    search_term = search.strip().lower() if search else None
    
    for app in apps:
        applicant = db.query(User).filter(User.id == app.user_id).first()
        applicant_name = applicant.full_name if (applicant and applicant.full_name) else (applicant.email if applicant else "Unknown")
        applicant_email = applicant.email if applicant else ""
        
        # Apply search filter if provided
        if search_term:
            matches_id = search_term in str(app.id).lower()
            matches_name = search_term in applicant_name.lower()
            matches_email = search_term in applicant_email.lower()
            matches_loan = search_term in app.loan_type.lower()
            if not (matches_id or matches_name or matches_email or matches_loan):
                continue
                
        doc_count = db.query(Document).filter(Document.application_id == app.id).count()
        created_str = app.created_at.isoformat() if app.created_at else None
        updated_str = app.updated_at.isoformat() if app.updated_at else None
        
        result.append({
            "id": str(app.id),
            "user_id": str(app.user_id),
            "customer_display_name": applicant_name,
            "applicant_name": applicant_name,
            "applicant_email": applicant_email,
            "loan_type": app.loan_type,
            "requested_amount": app.requested_amount,
            "tenure": app.tenure,
            "purpose": app.purpose,
            "status": app.status,
            "submitted_date": created_str,
            "created_at": created_str,
            "last_updated_time": updated_str or created_str,
            "updated_at": updated_str,
            "assigned_employee": None,
            "is_own_application": str(app.user_id) == str(current_user.id),
            "document_count": doc_count
        })
        
    return result


@router.get("/applications/{application_id}", response_model=EmployeeApplicationDetailResponse)
def get_employee_application_detail(
    application_id: UUID,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Returns full application detail for inspection.
    Pure read operation: Does NOT mutate application status.
    Enforces conflict of interest: Employees cannot review their own application.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    # Strictly exclude drafts from review workspace
    if app.status == ApplicationStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Draft applications are in progress by the applicant and cannot be accessed in the review queue."
        )
        
    # Check Conflict of Interest:
    # If the application belongs to the logged-in employee, self-review is forbidden.
    if str(app.user_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conflict of interest: Employees cannot review their own applications. Self-review is strictly forbidden under institutional governance rules."
        )
        
    applicant = db.query(User).filter(User.id == app.user_id).first()
    documents = db.query(Document).filter(Document.application_id == app.id).all()
    
    docs_data = []
    for doc in documents:
        docs_data.append({
            "id": str(doc.id),
            "document_type": doc.document_type,
            "file_url": f"/api/documents/{doc.id}/content",
            "status": doc.status,
            "reviewed_by": str(doc.reviewed_by) if doc.reviewed_by else None,
            "reviewed_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
            "review_notes": doc.review_notes,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
        })
        
    applicant_data = {
        "id": str(applicant.id) if applicant else None,
        "full_name": applicant.full_name if applicant else "Unknown",
        "email": applicant.email if applicant else "",
        "phone_number": applicant.phone_number if applicant else None,
        "date_of_birth": applicant.date_of_birth if applicant else None,
        "address": applicant.address if applicant else None,
        "city": applicant.city if applicant else None,
        "state": applicant.state if applicant else None,
        "pincode": applicant.pincode if applicant else None,
        "created_at": applicant.created_at.isoformat() if (applicant and applicant.created_at) else None
    }
    
    # Query additional information requests
    info_requests = db.query(AdditionalInformationRequest).filter(
        AdditionalInformationRequest.application_id == app.id
    ).order_by(AdditionalInformationRequest.created_at.desc()).all()
    
    info_requests_data = []
    for ir in info_requests:
        info_requests_data.append({
            "id": str(ir.id),
            "application_id": str(ir.application_id),
            "requested_by": str(ir.requested_by),
            "title": ir.title,
            "description": ir.description,
            "requested_document_type": ir.requested_document_type,
            "status": ir.status,
            "response_document_id": str(ir.response_document_id) if ir.response_document_id else None,
            "response_document_url": f"/api/documents/{ir.response_document_id}/content" if ir.response_document_id else None,
            "response_notes": ir.response_notes,
            "created_at": ir.created_at.isoformat() if ir.created_at else None,
            "responded_at": ir.responded_at.isoformat() if ir.responded_at else None,
        })

    # Construct audit timeline based on persisted events
    timeline = [
        {
            "event": "APPLICATION_SUBMITTED",
            "title": "Application Submitted",
            "description": "Applicant completed and formally submitted the loan application.",
            "timestamp": app.created_at.isoformat() if app.created_at else None
        }
    ]
    if app.status in [ApplicationStatus.UNDER_REVIEW.value, ApplicationStatus.APPROVED.value, ApplicationStatus.DECLINED.value, ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value]:
        timeline.append({
            "event": "QUEUE_INGESTION",
            "title": "Queued for Operational Review",
            "description": "Application routed to institutional operations queue.",
            "timestamp": app.created_at.isoformat() if app.created_at else None
        })
        timeline.append({
            "event": "UNDER_REVIEW",
            "title": "Underwriting Review Started",
            "description": "Authorized credit officer initiated formal underwriting evaluation.",
            "timestamp": app.updated_at.isoformat() if app.updated_at else app.created_at.isoformat()
        })

    # Append dynamic database audit events
    audit_records = db.query(ApplicationAuditEvent).filter(
        ApplicationAuditEvent.application_id == app.id
    ).order_by(ApplicationAuditEvent.created_at.asc()).all()
    for audit in audit_records:
        timeline.append({
            "event": audit.event_type,
            "title": audit.title,
            "description": audit.description,
            "timestamp": audit.created_at.isoformat() if audit.created_at else None
        })

    if app.status == ApplicationStatus.APPROVED.value:
        timeline.append({
            "event": "FINAL_APPROVAL",
            "title": "Application Approved",
            "description": "Formal credit sanction granted.",
            "timestamp": app.updated_at.isoformat() if app.updated_at else None
        })
    elif app.status == ApplicationStatus.DECLINED.value:
        timeline.append({
            "event": "FINAL_DECLINE",
            "title": "Application Declined",
            "description": "Application did not meet underwriting criteria.",
            "timestamp": app.updated_at.isoformat() if app.updated_at else None
        })
        
    return {
        "application": {
            "id": str(app.id),
            "user_id": str(app.user_id),
            "loan_type": app.loan_type,
            "requested_amount": app.requested_amount,
            "tenure": app.tenure,
            "purpose": app.purpose,
            "employment_info": app.employment_info,
            "income_info": app.income_info,
            "existing_liabilities": app.existing_liabilities,
            "status": app.status,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None
        },
        "applicant": applicant_data,
        "documents": docs_data,
        "information_requests": info_requests_data,
        "timeline": timeline,
        "compliance": {
            "status": "READY_FOR_EVALUATION",
            "module": "M10_ADAPTIVE_RAG",
            "compliance_score": None,
            "flags": [],
            "notes": "Policy & Compliance Evaluation integrates with Module M10/M11."
        },
        "decision": {
            "status": app.status,
            "module": "M12_DECISION_ENGINE",
            "can_decide": False,
            "notes": "Credit decision delegation & sanction letter generation handled in Module M12."
        }
    }


@router.post("/applications/{application_id}/transition-review", response_model=EmployeeApplicationDetailResponse)
def transition_application_to_review(
    application_id: UUID,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Explicitly transitions an application from SUBMITTED to UNDER_REVIEW (Start Review).
    Idempotent: If application is already UNDER_REVIEW, returns current state safely without duplicate events.
    Rejects invalid states (DRAFT, APPROVED, DECLINED, ADDITIONAL_INFO_REQUIRED).
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if str(app.user_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conflict of interest: Employees cannot review their own applications. Self-review is strictly forbidden under institutional governance rules."
        )
        
    if app.status == ApplicationStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Draft applications cannot be placed under review.")
        
    if app.status in [ApplicationStatus.APPROVED.value, ApplicationStatus.DECLINED.value, ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start review: Application is already in '{app.status}' state."
        )
        
    # If already UNDER_REVIEW, return current detail idempotently
    if app.status == ApplicationStatus.UNDER_REVIEW.value:
        return get_employee_application_detail(application_id=app.id, current_user=current_user, db=db)
        
    # Transition SUBMITTED -> UNDER_REVIEW
    app.status = ApplicationStatus.UNDER_REVIEW.value
    app.updated_at = datetime.now(timezone.utc)
    
    # Record review started audit event
    audit = ApplicationAuditEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="REVIEW_STARTED",
        title="Underwriting Review Started",
        description="Authorized credit officer formally initiated underwriting review."
    )
    db.add(audit)
    
    db.commit()
    db.refresh(app)
    
    return get_employee_application_detail(application_id=app.id, current_user=current_user, db=db)


@router.post("/documents/{document_id}/review")
def review_document(
    document_id: UUID,
    req: DocumentReviewRequest,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Review a customer-submitted document (Accept or Require Re-upload / Reject).
    Rejection and re-upload requests strictly mandate an explanatory reason.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
    if doc.application_id:
        app = db.query(Application).filter(Application.id == doc.application_id).first()
        if app and str(app.user_id) == str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conflict of interest: Employees cannot review their own application documents."
            )

    valid_statuses = [
        DocumentStatus.ACCEPTED.value,
        DocumentStatus.REQUIRES_REUPLOAD.value,
        DocumentStatus.REJECTED.value,
        DocumentStatus.VERIFIED.value
    ]
    if req.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid review status. Must be one of: {valid_statuses}"
        )

    if req.status in [DocumentStatus.REQUIRES_REUPLOAD.value, DocumentStatus.REJECTED.value]:
        if not req.reason or not req.reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="A clear reason is required when rejecting or requesting re-upload of a document."
            )

    doc.status = req.status
    doc.reviewed_by = current_user.id
    doc.reviewed_at = datetime.now(timezone.utc)
    doc.review_notes = req.reason.strip() if req.reason else None

    # Persist audit event
    if doc.application_id:
        audit_event = ApplicationAuditEvent(
            application_id=doc.application_id,
            user_id=current_user.id,
            event_type=f"DOCUMENT_{req.status}",
            title=f"Document {req.status.replace('_', ' ').title()}",
            description=f"Document '{doc.document_type.replace('_', ' ')}' was marked as {req.status}. {f'Reason: {doc.review_notes}' if doc.review_notes else ''}".strip()
        )
        db.add(audit_event)

    # Notify customer if re-upload is required
    if req.status in [DocumentStatus.REQUIRES_REUPLOAD.value, DocumentStatus.REJECTED.value] and doc.user_id:
        notif = Notification(
            user_id=doc.user_id,
            title="Document Review Action Required",
            message=f"Your submitted document '{doc.document_type.replace('_', ' ')}' requires re-upload. Reason: {doc.review_notes}",
            type="ACTION_REQUIRED",
            related_entity_id=doc.application_id
        )
        db.add(notif)

    db.commit()
    db.refresh(doc)
    return {
        "id": str(doc.id),
        "status": doc.status,
        "reviewed_by": str(doc.reviewed_by),
        "reviewed_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
        "review_notes": doc.review_notes
    }


@router.post("/applications/{application_id}/information-requests")
def create_information_request(
    application_id: UUID,
    req: InformationRequestCreate,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Creates an official request for additional information or supplementary documentation.
    Transitions the application status from UNDER_REVIEW to ADDITIONAL_INFO_REQUIRED.
    Generates an audit trail event and customer notification.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if str(app.user_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conflict of interest: Employees cannot review or request information on their own applications."
        )

    if app.status == ApplicationStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cannot request information on a draft application."
        )

    if not req.title or not req.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request title is required.")
    if not req.description or not req.description.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request description / explanation is required.")

    info_req = AdditionalInformationRequest(
        application_id=app.id,
        requested_by=current_user.id,
        title=req.title.strip(),
        description=req.description.strip(),
        requested_document_type=req.requested_document_type.strip() if req.requested_document_type else None,
        status=InformationRequestStatus.OPEN.value
    )
    db.add(info_req)

    # Transition application status to ADDITIONAL_INFO_REQUIRED
    app.status = ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value
    app.updated_at = datetime.now(timezone.utc)

    # Audit event
    audit = ApplicationAuditEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="ADDITIONAL_INFO_REQUESTED",
        title="Additional Information Requested",
        description=f"Underwriter requested supplementary documentation: {req.title.strip()} ({req.description.strip()})"
    )
    db.add(audit)

    # Customer notification
    notif = Notification(
        user_id=app.user_id,
        title="Additional Information Required",
        message=f"Underwriting desk requested additional information for application #{str(app.id)[:8].upper()}: {req.title.strip()}",
        type="ACTION_REQUIRED",
        related_entity_id=app.id
    )
    db.add(notif)

    db.commit()
    db.refresh(info_req)

    return {
        "id": str(info_req.id),
        "application_id": str(info_req.application_id),
        "requested_by": str(info_req.requested_by),
        "title": info_req.title,
        "description": info_req.description,
        "requested_document_type": info_req.requested_document_type,
        "status": info_req.status,
        "created_at": info_req.created_at.isoformat() if info_req.created_at else None,
        "application_status": app.status
    }


@router.get("/assignments")
def get_employee_assignments(
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Returns the truthful assignments for the employee.
    PolicyPilot currently routes applications through a shared operational queue.
    """
    return {
        "assigned_applications": [],
        "queue_type": "SHARED_INSTITUTIONAL_QUEUE",
        "message": "Direct individual assignment allocation is not configured. All applications are reviewed directly from the central operational queue."
    }


@router.get("/documents")
def get_employee_documents(
    status: Optional[str] = Query(None, description="Filter by document status"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Aggregated document repository for employee inspection across submitted customer applications.
    """
    query = (
        db.query(Document, Application, User)
        .join(Application, Document.application_id == Application.id)
        .join(User, Document.user_id == User.id)
        .filter(Application.status != ApplicationStatus.DRAFT.value)
    )
    
    if status and status.upper() != "ALL":
        query = query.filter(Document.status == status.upper())
        
    if document_type and document_type.upper() != "ALL":
        query = query.filter(Document.document_type.ilike(f"%{document_type}%"))
        
    records = query.order_by(Document.created_at.desc()).all()
    
    result = []
    for doc, app, user in records:
        result.append({
            "id": str(doc.id),
            "application_id": str(doc.application_id),
            "document_type": doc.document_type,
            "file_url": f"/api/documents/{doc.id}/content",
            "status": doc.status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "applicant_name": user.full_name or user.email,
            "applicant_email": user.email,
            "loan_type": app.loan_type,
            "application_status": app.status
        })
        
    return result


@router.get("/profile")
def get_employee_profile(
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Returns official employee profile information including institutional credentials.
    """
    emp_req = (
        db.query(EmployeeRequest)
        .filter(EmployeeRequest.user_id == current_user.id)
        .order_by(EmployeeRequest.created_at.desc())
        .first()
    )
    
    return {
        "user_id": str(current_user.id),
        "full_name": current_user.full_name or "Authorized Officer",
        "email": current_user.email,
        "role": current_user.role,
        "onboarding_status": current_user.onboarding_status,
        "language": current_user.language or "English",
        "organization": emp_req.organization if emp_req else "PolicyPilot Demo Bank",
        "department": emp_req.department if (emp_req and emp_req.department) else "Retail Credit Operations",
        "designation": emp_req.designation if (emp_req and emp_req.designation) else "Senior Credit Officer",
        "employee_id": emp_req.employee_id if (emp_req and emp_req.employee_id) else "PP-DEMO-EMP-001",
        "work_email": emp_req.work_email if (emp_req and emp_req.work_email) else "employee.demo@policypilot.local",
        "verified_at": emp_req.reviewed_at.isoformat() if (emp_req and emp_req.reviewed_at) else None
    }


@router.get("/organization")
def get_employee_organization(
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Returns organizational identity and institutional details.
    """
    emp_req = (
        db.query(EmployeeRequest)
        .filter(EmployeeRequest.user_id == current_user.id)
        .order_by(EmployeeRequest.created_at.desc())
        .first()
    )
    
    org_name = emp_req.organization if emp_req else "PolicyPilot Demo Bank"
    dept_name = emp_req.department if (emp_req and emp_req.department) else "Retail Credit Operations"
    
    return {
        "organization_name": org_name,
        "department": dept_name,
        "division": "Demo Lending Operations",
        "jurisdiction": "Sandbox Testing Jurisdiction",
        "branch_code": "PP-DEMO-BR-01",
        "regulatory_body": "PolicyPilot Regulatory Sandbox",
        "compliance_framework": "PolicyPilot Demo Credit Guidelines (M08 Integration Pending)",
        "portal_version": "PolicyPilot Demo Core v1.0",
        "active_workforce_unit": "Underwriting Desk A (Demo)"
    }


@router.get("/notifications")
def get_employee_notifications(
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Returns notifications addressed to the employee.
    """
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    
    unread_count = sum(1 for n in notifications if not n.is_read)
    
    result = []
    for n in notifications:
        result.append({
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": n.is_read,
            "related_entity_id": str(n.related_entity_id) if n.related_entity_id else None,
            "created_at": n.created_at.isoformat() if n.created_at else None
        })
        
    return {
        "unread_count": unread_count,
        "notifications": result
    }


# ============================================================================
# M05.3 — Compliance Workspace Endpoints
# ============================================================================

@router.get("/applications/{application_id}/compliance", response_model=ComplianceWorkspaceResponse)
def get_compliance_workspace(
    application_id: UUID,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Returns the Compliance Workspace dossier for an authorized employee.
    Enforces employee verification, COI (cannot review own application), and non-draft status.
    Lazily initializes standard compliance checklist items if not already present.
    NEVER mutates application status (no auto-transition).
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status == ApplicationStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Draft applications are in progress by the applicant and cannot be accessed in the compliance workspace."
        )

    check_employee_review_not_owner(current_user, str(app.user_id))

    # Lazy-seed checklist items if none exist
    checklist_items = (
        db.query(ComplianceChecklistItem)
        .filter(ComplianceChecklistItem.application_id == app.id)
        .order_by(ComplianceChecklistItem.display_order.asc())
        .all()
    )

    if not checklist_items:
        for seed_data in STANDARD_COMPLIANCE_CHECKLIST:
            new_item = ComplianceChecklistItem(
                application_id=app.id,
                item_key=seed_data["item_key"],
                category=seed_data["category"],
                title=seed_data["title"],
                description=seed_data["description"],
                status=ComplianceChecklistStatus.PENDING.value,
                notes=None,
                display_order=seed_data["display_order"],
                updated_by=None
            )
            db.add(new_item)
        db.commit()
        checklist_items = (
            db.query(ComplianceChecklistItem)
            .filter(ComplianceChecklistItem.application_id == app.id)
            .order_by(ComplianceChecklistItem.display_order.asc())
            .all()
        )

    # Build response
    applicant = db.query(User).filter(User.id == app.user_id).first()
    applicant_data = {
        "id": str(applicant.id) if applicant else None,
        "full_name": applicant.full_name if applicant else "Unknown",
        "email": applicant.email if applicant else "",
        "phone_number": applicant.phone_number if applicant else None,
        "date_of_birth": applicant.date_of_birth if applicant else None,
        "address": applicant.address if applicant else None,
        "city": applicant.city if applicant else None,
        "state": applicant.state if applicant else None,
        "pincode": applicant.pincode if applicant else None,
        "created_at": applicant.created_at.isoformat() if (applicant and applicant.created_at) else None
    }

    application_data = {
        "id": str(app.id),
        "user_id": str(app.user_id),
        "loan_type": app.loan_type,
        "requested_amount": app.requested_amount,
        "tenure": app.tenure,
        "purpose": app.purpose,
        "employment_info": app.employment_info,
        "income_info": app.income_info,
        "existing_liabilities": app.existing_liabilities,
        "status": app.status,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }

    documents = db.query(Document).filter(Document.application_id == app.id).all()
    docs_data = [
        {
            "id": str(doc.id),
            "document_type": doc.document_type,
            "file_url": f"/api/documents/{doc.id}/content",
            "status": doc.status,
            "reviewed_by": str(doc.reviewed_by) if doc.reviewed_by else None,
            "reviewed_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
            "review_notes": doc.review_notes,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
        }
        for doc in documents
    ]

    items_data = []
    for item in checklist_items:
        updater_name = None
        if item.updated_by:
            updater = db.query(User).filter(User.id == item.updated_by).first()
            if updater:
                updater_name = updater.full_name or updater.email
        items_data.append({
            "id": str(item.id),
            "application_id": str(item.application_id),
            "item_key": item.item_key,
            "category": item.category,
            "title": item.title,
            "description": item.description,
            "status": item.status,
            "notes": item.notes,
            "display_order": item.display_order,
            "updated_by": str(item.updated_by) if item.updated_by else None,
            "updated_by_name": updater_name,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    notes = (
        db.query(ComplianceReviewNote)
        .filter(ComplianceReviewNote.application_id == app.id)
        .order_by(ComplianceReviewNote.created_at.desc())
        .all()
    )
    notes_data = []
    for n in notes:
        author = db.query(User).filter(User.id == n.author_id).first()
        author_name = author.full_name or author.email if author else "Compliance Officer"
        author_email = author.email if author else ""
        notes_data.append({
            "id": str(n.id),
            "application_id": str(n.application_id),
            "author_id": str(n.author_id),
            "author_name": author_name,
            "author_email": author_email,
            "note": n.note,
            "created_at": n.created_at.isoformat() if n.created_at else None
        })

    info_requests = (
        db.query(AdditionalInformationRequest)
        .filter(AdditionalInformationRequest.application_id == app.id)
        .order_by(AdditionalInformationRequest.created_at.desc())
        .all()
    )
    info_requests_data = [
        {
            "id": str(ir.id),
            "application_id": str(ir.application_id),
            "requested_by": str(ir.requested_by),
            "title": ir.title,
            "description": ir.description,
            "requested_document_type": ir.requested_document_type,
            "status": ir.status,
            "response_document_id": str(ir.response_document_id) if ir.response_document_id else None,
            "response_document_url": f"/api/documents/{ir.response_document_id}/content" if ir.response_document_id else None,
            "response_notes": ir.response_notes,
            "created_at": ir.created_at.isoformat() if ir.created_at else None,
            "responded_at": ir.responded_at.isoformat() if ir.responded_at else None,
        }
        for ir in info_requests
    ]

    audit_events = (
        db.query(ApplicationAuditEvent)
        .filter(ApplicationAuditEvent.application_id == app.id)
        .order_by(ApplicationAuditEvent.created_at.desc())
        .all()
    )
    audit_data = [
        {
            "id": str(ae.id),
            "event_type": ae.event_type,
            "title": ae.title,
            "description": ae.description,
            "user_id": str(ae.user_id) if ae.user_id else None,
            "created_at": ae.created_at.isoformat() if ae.created_at else None,
        }
        for ae in audit_events
    ]

    return {
        "application": application_data,
        "applicant": applicant_data,
        "documents": docs_data,
        "checklist_items": items_data,
        "review_notes": notes_data,
        "information_requests": info_requests_data,
        "audit_events": audit_data,
        "ai_rag_boundary": {
            "status": "M10_RESERVED",
            "feature": "Adaptive RAG & Hybrid Retrieval",
            "message": "Regulatory policy vector search, BM25 indexing, evidence reranking, and automated policy cross-referencing are scheduled for Module M10. Manual compliance review workspace is currently active."
        }
    }


@router.patch("/applications/{application_id}/compliance/checklist/{item_id}", response_model=ComplianceChecklistItemResponse)
def update_compliance_checklist_item(
    application_id: UUID,
    item_id: UUID,
    body: ComplianceChecklistUpdate,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Updates the verification status and internal notes of a compliance checklist item.
    Enforces employee verification, COI, non-draft status.
    Generates a persistent ApplicationAuditEvent.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status == ApplicationStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Draft applications cannot be modified for compliance."
        )

    check_employee_review_not_owner(current_user, str(app.user_id))

    item = (
        db.query(ComplianceChecklistItem)
        .filter(
            ComplianceChecklistItem.id == item_id,
            ComplianceChecklistItem.application_id == app.id
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Compliance checklist item not found")

    valid_statuses = [s.value for s in ComplianceChecklistStatus]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid checklist status '{body.status}'. Valid statuses: {valid_statuses}"
        )

    old_status = item.status
    item.status = body.status
    if body.notes is not None:
        item.notes = body.notes.strip() if body.notes else None
    item.updated_by = current_user.id
    item.updated_at = datetime.now(timezone.utc)

    # Log audit event
    audit = ApplicationAuditEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="COMPLIANCE_CHECKLIST_UPDATED",
        title="Compliance Checklist Item Updated",
        description=f"Checklist item '{item.title}' marked as {item.status} (was {old_status}) by {current_user.full_name or current_user.email}."
    )
    db.add(audit)
    db.commit()
    db.refresh(item)

    updater_name = current_user.full_name or current_user.email
    return {
        "id": str(item.id),
        "application_id": str(item.application_id),
        "item_key": item.item_key,
        "category": item.category,
        "title": item.title,
        "description": item.description,
        "status": item.status,
        "notes": item.notes,
        "display_order": item.display_order,
        "updated_by": str(item.updated_by) if item.updated_by else None,
        "updated_by_name": updater_name,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.post("/applications/{application_id}/compliance/notes", response_model=ComplianceNoteResponse)
def add_compliance_review_note(
    application_id: UUID,
    body: ComplianceNoteCreate,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Records an internal compliance review note for an application.
    Enforces employee verification, COI, non-draft status.
    Generates a persistent ApplicationAuditEvent.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status == ApplicationStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Draft applications cannot accept compliance notes."
        )

    check_employee_review_not_owner(current_user, str(app.user_id))

    trimmed_note = body.note.strip() if body.note else ""
    if not trimmed_note:
        raise HTTPException(status_code=400, detail="Note text cannot be empty.")

    new_note = ComplianceReviewNote(
        application_id=app.id,
        author_id=current_user.id,
        note=trimmed_note
    )
    db.add(new_note)

    # Log audit event
    audit = ApplicationAuditEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="COMPLIANCE_NOTE_RECORDED",
        title="Compliance Officer Note Added",
        description=f"Compliance review note recorded by {current_user.full_name or current_user.email}."
    )
    db.add(audit)
    db.commit()
    db.refresh(new_note)

    author_name = current_user.full_name or current_user.email
    return {
        "id": str(new_note.id),
        "application_id": str(new_note.application_id),
        "author_id": str(new_note.author_id),
        "author_name": author_name,
        "author_email": current_user.email,
        "note": new_note.note,
        "created_at": new_note.created_at.isoformat() if new_note.created_at else datetime.now(timezone.utc).isoformat(),
    }
