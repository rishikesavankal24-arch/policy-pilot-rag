from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from datetime import datetime, timezone
import re

from pydantic import BaseModel, ConfigDict, field_validator
from app.db.session import get_db
from app.db.models import (
    User, Role, OnboardingStatus, Application, ApplicationStatus,
    Document, DocumentStatus, Notification, EmployeeRequest, EmployeeRequestStatus,
    InformationRequestStatus, AdditionalInformationRequest, ApplicationAuditEvent,
    ComplianceChecklistStatus, ComplianceChecklistItem, ComplianceReviewNote,
    ReviewReadinessState
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
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    file_hash: Optional[str] = None
    page_count: Optional[int] = None

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
    resolved_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ResolveInformationRequestRequest(BaseModel):
    notes: Optional[str] = None

class ApplicationDecisionRequest(BaseModel):
    status: str
    notes: Optional[str] = None

    @field_validator("notes")
    @classmethod
    def trim_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed if trimmed else None

class ApplicationDecisionResponse(BaseModel):
    id: str
    status: str
    decision: str
    notes: Optional[str] = None
    updated_at: Optional[str] = None
    message: str

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

class ChecklistSummarySchema(BaseModel):
    total: int
    reviewed: int
    pending: int
    requires_information: int
    not_applicable: int

class DocumentSummarySchema(BaseModel):
    total: int
    verified_or_accepted: int
    pending_review: int
    rejected_or_reupload: int

class InfoRequestsSummarySchema(BaseModel):
    total: int
    open: int
    responded: int
    resolved: int

class ReviewReadinessResponse(BaseModel):
    application_id: str
    status: str
    is_ready: bool
    can_mark_ready: bool
    blocking_reasons: List[str]
    completed_checks: List[str]
    pending_checks: List[str]
    checklist_summary: ChecklistSummarySchema
    document_summary: DocumentSummarySchema
    info_requests_summary: InfoRequestsSummarySchema
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    updated_by_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ReviewReadinessResetRequest(BaseModel):
    reason: Optional[str] = None

class ComplianceWorkspaceResponse(BaseModel):
    application: ApplicationDetailInfo
    applicant: ApplicantKYCInfo
    documents: List[DocumentItem]
    checklist_items: List[ComplianceChecklistItemResponse]
    review_notes: List[ComplianceNoteResponse]
    information_requests: List[InformationRequestItem]
    audit_events: List[ComplianceAuditEventItem]
    ai_rag_boundary: dict
    readiness: Optional[ReviewReadinessResponse] = None

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


def invalidate_review_readiness(app: Application, db: Session, actor_id: Optional[UUID], reason: str):
    """
    If an application was marked READY_FOR_COMPLIANCE_ASSESSMENT,
    and a conflicting action or new information arrives,
    immediately reset review_readiness_status to PENDING_REVIEW_PREPARATION
    and log an immutable ApplicationAuditEvent.
    """
    if getattr(app, "review_readiness_status", None) == ReviewReadinessState.READY_FOR_COMPLIANCE_ASSESSMENT.value:
        prev_state = app.review_readiness_status
        app.review_readiness_status = ReviewReadinessState.PENDING_REVIEW_PREPARATION.value
        app.review_readiness_updated_at = datetime.now(timezone.utc)
        app.review_readiness_updated_by = actor_id
        
        actor = db.query(User).filter(User.id == actor_id).first() if actor_id else None
        actor_label = actor.full_name or actor.email if actor else "Authorized User"

        audit = ApplicationAuditEvent(
            application_id=app.id,
            user_id=actor_id,
            event_type="COMPLIANCE_REVIEW_READINESS_RESET",
            title="Review Readiness Invalidated",
            description=f"Review readiness state reset from {prev_state} to PENDING_REVIEW_PREPARATION by {actor_label}. Reason: {reason}"
        )
        db.add(audit)


def calculate_review_readiness(app: Application, db: Session) -> dict:
    """
    Calculates review readiness dynamically from real database state.
    Evaluates:
    - Application submission status
    - Document availability & review statuses
    - Additional information requests status
    - Compliance checklist evaluation status
    """
    blocking_reasons: List[str] = []
    completed_checks: List[str] = []
    pending_checks: List[str] = []

    # 1. Application submission check
    if app.status == ApplicationStatus.DRAFT.value:
        blocking_reasons.append("Application is in draft status and has not been formally submitted.")
        pending_checks.append("Formal application submission by applicant")
    else:
        completed_checks.append(f"Application formally submitted (Status: {app.status})")

    # 2. Document completeness & review check
    documents = db.query(Document).filter(Document.application_id == app.id).all()
    total_docs = len(documents)
    verified_docs = sum(1 for d in documents if d.status in [DocumentStatus.ACCEPTED.value, DocumentStatus.VERIFIED.value])
    pending_docs = sum(1 for d in documents if d.status in [DocumentStatus.UPLOADED.value, DocumentStatus.PROCESSING.value, DocumentStatus.UNDER_REVIEW.value])
    rejected_or_reupload_docs = sum(1 for d in documents if d.status in [DocumentStatus.REQUIRES_REUPLOAD.value, DocumentStatus.REJECTED.value])

    if total_docs == 0:
        blocking_reasons.append("No verification documents have been uploaded for this application.")
        pending_checks.append("Mandatory verification documentation upload")
    else:
        if rejected_or_reupload_docs > 0:
            for d in documents:
                if d.status in [DocumentStatus.REQUIRES_REUPLOAD.value, DocumentStatus.REJECTED.value]:
                    notes_text = d.review_notes if (d.review_notes and d.review_notes.strip().lower() not in ["nil", "none"]) else "Reason not recorded"
                    blocking_reasons.append(f"Document '{d.document_type.replace('_', ' ')}' requires re-upload or was rejected ({notes_text}).")
            pending_checks.append(f"{rejected_or_reupload_docs} document(s) require re-upload or rectification")
        
        if pending_docs > 0:
            for d in documents:
                if d.status in [DocumentStatus.UPLOADED.value, DocumentStatus.PROCESSING.value, DocumentStatus.UNDER_REVIEW.value]:
                    blocking_reasons.append(f"Document '{d.document_type.replace('_', ' ')}' is awaiting operational review.")
            pending_checks.append(f"{pending_docs} document(s) awaiting credit officer review")

        if verified_docs == total_docs and total_docs > 0:
            completed_checks.append(f"All {total_docs} submitted document(s) verified by credit operations")

    # 3. Additional information requests check
    info_requests = db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.application_id == app.id).all()
    open_reqs = [ir for ir in info_requests if ir.status == InformationRequestStatus.OPEN.value]
    responded_reqs = [ir for ir in info_requests if ir.status == InformationRequestStatus.RESPONDED.value]
    resolved_reqs = [ir for ir in info_requests if ir.status in [InformationRequestStatus.RESOLVED.value, InformationRequestStatus.CANCELLED.value]]

    if open_reqs:
        for ir in open_reqs:
            blocking_reasons.append(f"Additional information request '{ir.title}' is pending applicant response.")
        pending_checks.append(f"{len(open_reqs)} open query/information request(s) awaiting applicant action")

    if responded_reqs:
        for ir in responded_reqs:
            blocking_reasons.append(f"Applicant responded to '{ir.title}'; review of response is required.")
        pending_checks.append(f"{len(responded_reqs)} customer response(s) pending officer verification")

    if not open_reqs and not responded_reqs:
        if info_requests:
            completed_checks.append(f"All {len(info_requests)} information request(s) resolved")
        else:
            completed_checks.append("No open information requests or queries")

    # 4. Compliance checklist check
    checklist_items = db.query(ComplianceChecklistItem).filter(ComplianceChecklistItem.application_id == app.id).all()
    total_items = len(checklist_items)
    pending_items = [it for it in checklist_items if it.status == ComplianceChecklistStatus.PENDING.value]
    req_info_items = [it for it in checklist_items if it.status == ComplianceChecklistStatus.REQUIRES_INFORMATION.value]
    not_applicable_items = [it for it in checklist_items if it.status == ComplianceChecklistStatus.NOT_APPLICABLE.value]
    reviewed_only_items = [it for it in checklist_items if it.status == ComplianceChecklistStatus.REVIEWED.value]

    if total_items == 0:
        blocking_reasons.append("Compliance checklist has not been initialized.")
        pending_checks.append("Compliance checklist evaluation")
    else:
        if pending_items:
            for it in pending_items:
                blocking_reasons.append(f"Compliance checklist item '{it.title}' has not been evaluated (status is PENDING).")
            pending_checks.append(f"{len(pending_items)} checklist item(s) pending evaluation")

        if req_info_items:
            for it in req_info_items:
                blocking_reasons.append(f"Compliance checklist item '{it.title}' requires additional information before compliance assessment can proceed.")
            pending_checks.append(f"{len(req_info_items)} checklist item(s) flagged as requiring information")

        if not pending_items and not req_info_items:
            completed_checks.append(f"All {total_items} compliance checklist item(s) reviewed and verified")

    is_ready = (len(blocking_reasons) == 0)
    current_readiness = getattr(app, "review_readiness_status", ReviewReadinessState.PENDING_REVIEW_PREPARATION.value)
    can_mark_ready = is_ready and (current_readiness != ReviewReadinessState.READY_FOR_COMPLIANCE_ASSESSMENT.value)

    updater_name = None
    if getattr(app, "review_readiness_updated_by", None):
        updater = db.query(User).filter(User.id == app.review_readiness_updated_by).first()
        if updater:
            updater_name = updater.full_name or updater.email

    return {
        "application_id": str(app.id),
        "status": current_readiness,
        "is_ready": is_ready,
        "can_mark_ready": can_mark_ready,
        "blocking_reasons": blocking_reasons,
        "completed_checks": completed_checks,
        "pending_checks": pending_checks,
        "checklist_summary": {
            "total": total_items,
            "reviewed": len(reviewed_only_items),
            "pending": len(pending_items),
            "requires_information": len(req_info_items),
            "not_applicable": len(not_applicable_items)
        },
        "document_summary": {
            "total": total_docs,
            "verified_or_accepted": verified_docs,
            "pending_review": pending_docs,
            "rejected_or_reupload": rejected_or_reupload_docs
        },
        "info_requests_summary": {
            "total": len(info_requests),
            "open": len(open_reqs),
            "responded": len(responded_reqs),
            "resolved": len(resolved_reqs)
        },
        "updated_at": app.review_readiness_updated_at.isoformat() if getattr(app, "review_readiness_updated_at", None) else None,
        "updated_by": str(app.review_readiness_updated_by) if getattr(app, "review_readiness_updated_by", None) else None,
        "updated_by_name": updater_name
    }


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
            detail="Conflict of interest: Employees cannot review their own applications. Self-review is strictly forbidden under governance rules."
        )
        
    applicant = db.query(User).filter(User.id == app.user_id).first()
    documents = db.query(Document).filter(Document.application_id == app.id).order_by(Document.created_at.desc()).all()
    
    docs_data = []
    for doc in documents:
        display_notes = doc.review_notes
        if display_notes and display_notes.strip().lower() in ["nil", "none"]:
            display_notes = "Reason not recorded"
        docs_data.append({
            "id": str(doc.id),
            "document_type": doc.document_type,
            "file_url": f"/api/documents/{doc.id}/content",
            "status": doc.status,
            "reviewed_by": str(doc.reviewed_by) if doc.reviewed_by else None,
            "reviewed_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
            "review_notes": display_notes,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            "original_filename": doc.original_filename,
            "file_size_bytes": doc.file_size_bytes,
            "mime_type": doc.mime_type,
            "file_hash": doc.file_hash,
            "page_count": doc.page_count
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
            "resolved_at": ir.resolved_at.isoformat() if ir.resolved_at else None,
        })

    # Append dynamic database audit events
    audit_records = db.query(ApplicationAuditEvent).filter(
        ApplicationAuditEvent.application_id == app.id
    ).order_by(ApplicationAuditEvent.created_at.asc()).all()

    # Construct audit timeline based on persisted events
    timeline = []
    has_submitted_audit = any(a.event_type == "APPLICATION_SUBMITTED" for a in audit_records)
    if not has_submitted_audit and app.status != ApplicationStatus.DRAFT.value:
        timeline.append({
            "event": "APPLICATION_SUBMITTED",
            "title": "Application Submitted",
            "description": "Applicant completed and formally submitted the loan application.",
            "timestamp": app.created_at.isoformat() if app.created_at else None
        })

    if app.status in [ApplicationStatus.UNDER_REVIEW.value, ApplicationStatus.APPROVED.value, ApplicationStatus.DECLINED.value, ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value]:
        timeline.append({
            "event": "QUEUE_INGESTION",
            "title": "Queued for Operational Review",
            "description": "Application routed to operational review queue.",
            "timestamp": app.created_at.isoformat() if app.created_at else None
        })
        has_review_started = any(a.event_type == "REVIEW_STARTED" for a in audit_records)
        if not has_review_started:
            timeline.append({
                "event": "UNDER_REVIEW",
                "title": "Underwriting Review Started",
                "description": "Authorized credit officer initiated formal underwriting evaluation.",
                "timestamp": app.updated_at.isoformat() if app.updated_at else app.created_at.isoformat()
            })

    for audit in audit_records:
        clean_desc = audit.description or ""
        clean_desc = re.sub(r'Reason:\s*(nil|none)\b', 'Reason: Reason not recorded', clean_desc, flags=re.IGNORECASE)
        timeline.append({
            "event": audit.event_type,
            "title": audit.title,
            "description": clean_desc,
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
            "notes": "Policy & Compliance Evaluation reserved for Module M10/M11. Manual compliance review currently active."
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
            detail="Conflict of interest: Employees cannot review their own applications. Self-review is strictly forbidden under governance rules."
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


@router.post("/applications/{application_id}/decision", response_model=ApplicationDecisionResponse)
def decide_application(
    application_id: UUID,
    req: ApplicationDecisionRequest,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Final credit decisioning endpoint for an application under review:
    - Status must be 'APPROVED' or 'DECLINED'
    - Application must be in 'UNDER_REVIEW' status (rejects DRAFT, SUBMITTED, ADDITIONAL_INFO_REQUIRED, APPROVED, DECLINED)
    - Enforces Conflict of Interest: Employees cannot decide on their own applications
    - If APPROVED: Verifies that calculate_review_readiness has is_ready == True and 0 blockers
    - If DECLINED: A meaningful reason is mandatory (non-empty, non-whitespace, not 'nil')
    - Transactionally creates immutable audit event and customer notification
    - Transitions to terminal state APPROVED or DECLINED
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # Conflict of interest check (employees cannot review or decide their own applications)
    check_employee_review_not_owner(current_user, str(app.user_id))

    # Validate decision status
    valid_decisions = [ApplicationStatus.APPROVED.value, ApplicationStatus.DECLINED.value]
    clean_status = (req.status or "").strip().upper()
    if clean_status not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision status '{req.status}'. Final decision must be one of: {valid_decisions}."
        )

    # Validate current application state: final decision only allowed when UNDER_REVIEW
    if app.status != ApplicationStatus.UNDER_REVIEW.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application cannot be decided in '{app.status}' status. Final decisions can only be made on applications that are UNDER_REVIEW."
        )

    clean_notes = req.notes.strip() if req.notes else None

    if clean_status == ApplicationStatus.APPROVED.value:
        # Re-use existing review-readiness engine
        readiness = calculate_review_readiness(app, db)
        if not readiness["is_ready"] or len(readiness["blocking_reasons"]) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Application is not ready for final approval. All review readiness blockers must be resolved first.",
                    "blocking_reasons": readiness["blocking_reasons"]
                }
            )

        app.status = ApplicationStatus.APPROVED.value
        app.updated_at = datetime.now(timezone.utc)

        approval_desc = f"Loan application approved for {app.loan_type} (₹{app.requested_amount:,}) by credit officer {current_user.full_name or current_user.email}."
        if clean_notes and clean_notes.lower() != "nil":
            approval_desc += f" Note: {clean_notes}"

        audit = ApplicationAuditEvent(
            application_id=app.id,
            user_id=current_user.id,
            event_type="APPLICATION_APPROVED",
            title="Application Approved",
            description=approval_desc
        )
        db.add(audit)

        notif = Notification(
            user_id=app.user_id,
            title="Loan Application Approved",
            message=f"Congratulations! Your loan application for {app.loan_type} has been approved.",
            type="STATUS_UPDATE",
            related_entity_id=app.id
        )
        db.add(notif)

    elif clean_status == ApplicationStatus.DECLINED.value:
        # Mandatory meaningful reason
        if not clean_notes or clean_notes.lower() == "nil":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A clear, meaningful rejection/deficiency reason is mandatory when declining an application."
            )

        app.status = ApplicationStatus.DECLINED.value
        app.updated_at = datetime.now(timezone.utc)

        audit = ApplicationAuditEvent(
            application_id=app.id,
            user_id=current_user.id,
            event_type="APPLICATION_DECLINED",
            title="Application Declined",
            description=f"Loan application declined by {current_user.full_name or current_user.email}. Reason: {clean_notes}"
        )
        db.add(audit)

        notif = Notification(
            user_id=app.user_id,
            title="Loan Application Declined",
            message="Your loan application has been declined. Please review the application for available decision information.",
            type="STATUS_UPDATE",
            related_entity_id=app.id
        )
        db.add(notif)

    db.commit()
    db.refresh(app)

    return ApplicationDecisionResponse(
        id=str(app.id),
        status=app.status,
        decision=app.status,
        notes=clean_notes,
        updated_at=app.updated_at.isoformat() if app.updated_at else None,
        message=f"Application successfully marked as {app.status}."
    )


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
        clean_req_reason = req.reason.strip() if req.reason else ""
        if not clean_req_reason or clean_req_reason.lower() == "nil":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="A clear reason is required when rejecting or requesting re-upload of a document."
            )

    doc.status = req.status
    doc.reviewed_by = current_user.id
    doc.reviewed_at = datetime.now(timezone.utc)
    clean_notes = req.reason.strip() if (req.reason and req.reason.strip().lower() != "nil") else None
    doc.review_notes = clean_notes

    # Persist audit event
    if doc.application_id:
        if req.status in [DocumentStatus.REQUIRES_REUPLOAD.value, DocumentStatus.REJECTED.value]:
            reason_text = clean_notes if clean_notes else "Reason not recorded"
            desc = f"Document '{doc.document_type.replace('_', ' ')}' was marked as {req.status}. Reason: {reason_text}"
        else:
            reason_text = f" Reason: {clean_notes}" if clean_notes else ""
            desc = f"Document '{doc.document_type.replace('_', ' ')}' was marked as {req.status}.{reason_text}".strip()

        audit_event = ApplicationAuditEvent(
            application_id=doc.application_id,
            user_id=current_user.id,
            event_type=f"DOCUMENT_{req.status}",
            title=f"Document {req.status.replace('_', ' ').title()}",
            description=desc
        )
        db.add(audit_event)

        # Invalidate review readiness if document is deficient or rejected
        if req.status in [DocumentStatus.REQUIRES_REUPLOAD.value, DocumentStatus.REJECTED.value]:
            app_to_check = db.query(Application).filter(Application.id == doc.application_id).first()
            if app_to_check:
                invalidate_review_readiness(
                    app_to_check, db, current_user.id,
                    f"Document '{doc.document_type.replace('_', ' ')}' marked as {req.status}."
                )

    # Notify customer if re-upload is required
    if req.status in [DocumentStatus.REQUIRES_REUPLOAD.value, DocumentStatus.REJECTED.value] and doc.user_id:
        notif_reason = doc.review_notes if doc.review_notes else "Reason not recorded"
        notif = Notification(
            user_id=doc.user_id,
            title="Document Review Action Required",
            message=f"Your submitted document '{doc.document_type.replace('_', ' ')}' requires re-upload. Reason: {notif_reason}",
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

    # Invalidate review readiness
    invalidate_review_readiness(
        app, db, current_user.id,
        f"Underwriting desk requested additional information: {req.title.strip()}."
    )

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


@router.post("/applications/{application_id}/information-requests/{request_id}/resolve")
def resolve_information_request(
    application_id: UUID,
    request_id: UUID,
    body: ResolveInformationRequestRequest = ResolveInformationRequestRequest(),
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Resolves an information request after evaluating customer response.
    Transitions request from RESPONDED (or OPEN) to RESOLVED.
    If no other open or responded queries exist, transitions application back to UNDER_REVIEW.
    Re-evaluates review readiness and logs an audit event.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if str(app.user_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conflict of interest: Employees cannot review or resolve queries on their own applications."
        )

    info_req = db.query(AdditionalInformationRequest).filter(
        AdditionalInformationRequest.id == request_id,
        AdditionalInformationRequest.application_id == app.id
    ).first()
    if not info_req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information request not found")

    if info_req.status == InformationRequestStatus.RESOLVED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Information request is already resolved")

    # Update status to RESOLVED
    info_req.status = InformationRequestStatus.RESOLVED.value
    info_req.resolved_at = datetime.now(timezone.utc)

    # Check remaining open / responded queries
    remaining_pending_requests = db.query(AdditionalInformationRequest).filter(
        AdditionalInformationRequest.application_id == app.id,
        AdditionalInformationRequest.id != info_req.id,
        AdditionalInformationRequest.status.in_([
            InformationRequestStatus.OPEN.value,
            InformationRequestStatus.RESPONDED.value
        ])
    ).count()

    if remaining_pending_requests == 0 and app.status == ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value:
        app.status = ApplicationStatus.UNDER_REVIEW.value
        app.updated_at = datetime.now(timezone.utc)

    # Audit event
    notes_detail = f" Notes: {body.notes.strip()}" if body.notes and body.notes.strip() else ""
    audit = ApplicationAuditEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="ADDITIONAL_INFO_RESOLVED",
        title="Additional Information Request Resolved",
        description=f"Underwriter resolved query '{info_req.title}'.{notes_detail}"
    )
    db.add(audit)

    db.commit()
    db.refresh(info_req)
    db.refresh(app)

    # Dynamically calculate review readiness
    readiness = calculate_review_readiness(app, db)

    return {
        "id": str(info_req.id),
        "application_id": str(info_req.application_id),
        "status": info_req.status,
        "resolved_at": info_req.resolved_at.isoformat() if info_req.resolved_at else None,
        "application_status": app.status,
        "readiness": readiness
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
            "application_status": app.status,
            "original_filename": doc.original_filename,
            "file_size_bytes": doc.file_size_bytes,
            "mime_type": doc.mime_type,
            "file_hash": doc.file_hash,
            "page_count": doc.page_count
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

    documents = db.query(Document).filter(Document.application_id == app.id).order_by(Document.created_at.desc()).all()
    docs_data = [
        {
            "id": str(doc.id),
            "document_type": doc.document_type,
            "file_url": f"/api/documents/{doc.id}/content",
            "status": doc.status,
            "reviewed_by": str(doc.reviewed_by) if doc.reviewed_by else None,
            "reviewed_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
            "review_notes": ("Reason not recorded" if (doc.review_notes and doc.review_notes.strip().lower() in ["nil", "none"]) else doc.review_notes),
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
            "resolved_at": ir.resolved_at.isoformat() if ir.resolved_at else None,
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
            "description": re.sub(r'Reason:\s*(nil|none)\b', 'Reason: Reason not recorded', ae.description or "", flags=re.IGNORECASE),
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
        },
        "readiness": calculate_review_readiness(app, db)
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

    # Invalidate review readiness if item is set to PENDING or REQUIRES_INFORMATION
    if item.status in [ComplianceChecklistStatus.PENDING.value, ComplianceChecklistStatus.REQUIRES_INFORMATION.value]:
        invalidate_review_readiness(
            app, db, current_user.id,
            f"Checklist item '{item.title}' marked as {item.status}."
        )

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


@router.get("/applications/{application_id}/review-readiness", response_model=ReviewReadinessResponse)
def get_application_review_readiness(
    application_id: UUID,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Returns current readiness evaluation, blocker list, and completed checks.
    Enforces verified employee access, draft exclusion, and COI checks.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status == ApplicationStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Draft applications cannot be evaluated for review readiness."
        )

    check_employee_review_not_owner(current_user, str(app.user_id))

    return calculate_review_readiness(app, db)


@router.post("/applications/{application_id}/review-readiness/mark-ready", response_model=ReviewReadinessResponse)
def mark_application_review_ready(
    application_id: UUID,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Transitions review readiness status to READY_FOR_COMPLIANCE_ASSESSMENT.
    Rejects with 400 if any unresolved blockers exist.
    Generates immutable COMPLIANCE_REVIEW_READY audit event.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status == ApplicationStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Draft applications cannot be marked ready for compliance assessment."
        )

    check_employee_review_not_owner(current_user, str(app.user_id))

    readiness = calculate_review_readiness(app, db)
    if not readiness["is_ready"] or len(readiness["blocking_reasons"]) > 0:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Application is not ready for compliance assessment. All blockers must be resolved first.",
                "blocking_reasons": readiness["blocking_reasons"]
            }
        )

    app.review_readiness_status = ReviewReadinessState.READY_FOR_COMPLIANCE_ASSESSMENT.value
    app.review_readiness_updated_at = datetime.now(timezone.utc)
    app.review_readiness_updated_by = current_user.id

    audit = ApplicationAuditEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="COMPLIANCE_REVIEW_READY",
        title="Application Marked Ready for Compliance Assessment",
        description=f"Application marked ready for compliance assessment by {current_user.full_name or current_user.email} after satisfying all prerequisite verifications."
    )
    db.add(audit)
    db.commit()
    db.refresh(app)

    return calculate_review_readiness(app, db)


@router.post("/applications/{application_id}/review-readiness/reset", response_model=ReviewReadinessResponse)
def reset_application_review_readiness(
    application_id: UUID,
    body: ReviewReadinessResetRequest = ReviewReadinessResetRequest(),
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Explicitly resets review readiness status back to PENDING_REVIEW_PREPARATION.
    Logs COMPLIANCE_REVIEW_READINESS_RESET audit event.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status == ApplicationStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Draft applications cannot be modified for review readiness."
        )

    check_employee_review_not_owner(current_user, str(app.user_id))

    reason = body.reason.strip() if (body and body.reason and body.reason.strip()) else "Manual reset by compliance reviewer."

    if getattr(app, "review_readiness_status", None) == ReviewReadinessState.READY_FOR_COMPLIANCE_ASSESSMENT.value:
        invalidate_review_readiness(app, db, current_user.id, reason)
        db.commit()
        db.refresh(app)

    return calculate_review_readiness(app, db)


# ==============================================================================
# M08.7 — Employee Policy Catalog Schemas & Endpoints
# ==============================================================================

from app.services.employee_policy_service import (
    EmployeePolicyService,
    EmployeePolicyNotFoundError,
    EmployeePolicyAccessDeniedError
)


class EmployeeRegulatoryAuthoritySummary(BaseModel):
    id: str
    name: str
    short_name: str
    authority_type: str
    jurisdiction: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeePolicyListItem(BaseModel):
    id: str
    policy_code: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    policy_type: Optional[str] = None
    institution: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: str
    current_version_id: Optional[str] = None
    current_version_number: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    regulatory_authority: Optional[EmployeeRegulatoryAuthoritySummary] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeePolicyListResponse(BaseModel):
    items: List[EmployeePolicyListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class EmployeeApplicabilitySummary(BaseModel):
    id: str
    institution: Optional[str] = None
    jurisdiction: Optional[str] = None
    loan_type: Optional[str] = None
    department: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeePolicyVersionSummary(BaseModel):
    id: str
    version_number: str
    changelog: Optional[str] = None
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None
    file_size: Optional[int] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    has_file: bool = False
    status: Optional[str] = None
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeePolicyDetail(BaseModel):
    id: str
    policy_code: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    policy_type: Optional[str] = None
    institution: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: str
    current_version: Optional[EmployeePolicyVersionSummary] = None
    current_version_id: Optional[str] = None
    current_version_number: Optional[str] = None
    current_version_changelog: Optional[str] = None
    current_version_page_count: Optional[int] = None
    current_version_file_size_bytes: Optional[int] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    regulatory_authority: Optional[EmployeeRegulatoryAuthoritySummary] = None
    applicabilities: List[EmployeeApplicabilitySummary]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeePolicyHistoryItem(BaseModel):
    id: str
    version_number: str
    status_context: str
    status: Optional[str] = None
    changelog: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    has_file: bool = False
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    created_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    download_url: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/policies", response_model=EmployeePolicyListResponse)
def list_employee_policies(
    search: Optional[str] = None,
    category: Optional[str] = None,
    policy_type: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    institution: Optional[str] = None,
    regulatory_authority_id: Optional[str] = None,
    loan_type: Optional[str] = None,
    department: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Verified employee catalog listing of ACTIVE policies.
    Guarantees that only policies in ACTIVE state are discoverable.
    """
    try:
        items, total, total_pages = EmployeePolicyService.list_active_policies(
            db=db,
            search=search,
            category=category,
            policy_type=policy_type,
            jurisdiction=jurisdiction,
            institution=institution,
            regulatory_authority_id=regulatory_authority_id,
            loan_type=loan_type,
            department=department,
            page=page,
            page_size=page_size
        )
        return EmployeePolicyListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to query employee policy catalog: {str(e)}"
        )


@router.get("/policies/{policy_id}", response_model=EmployeePolicyDetail)
def get_employee_policy_detail(
    policy_id: UUID,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Retrieve employee-safe detail for an ACTIVE policy.
    Returns 404 if policy does not exist or is not in ACTIVE state.
    """
    try:
        return EmployeePolicyService.get_active_policy_detail(db=db, policy_id=policy_id)
    except EmployeePolicyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found or not in active regulatory force."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve policy details: {str(e)}"
        )


@router.get("/policies/{policy_id}/history", response_model=List[EmployeePolicyHistoryItem])
def get_employee_policy_history(
    policy_id: UUID,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Retrieve version lineage for an ACTIVE policy.
    Returns 404 if policy does not exist or is not in ACTIVE state.
    """
    try:
        return EmployeePolicyService.get_active_policy_history(db=db, policy_id=policy_id)
    except EmployeePolicyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found or not in active regulatory force."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve version history: {str(e)}"
        )


@router.get("/policies/{policy_id}/versions/{version_id}/file")
def get_employee_policy_document_file(
    policy_id: UUID,
    version_id: UUID,
    current_user: User = Depends(require_verified_employee),
    db: Session = Depends(get_db)
):
    """
    Authorized document streaming endpoint for verified employees.
    Verifies that policy is ACTIVE and version exists.
    """
    try:
        file_path, version = EmployeePolicyService.get_active_policy_version_file(
            db=db,
            policy_id=policy_id,
            version_id=version_id
        )

        media_type = "application/pdf"
        suffix = file_path.suffix.lower()
        if suffix == ".png":
            media_type = "image/png"
        elif suffix in (".jpg", ".jpeg"):
            media_type = "image/jpeg"

        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type=media_type
        )
    except EmployeePolicyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy document version not found or not in active force."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to access policy document: {str(e)}"
        )


