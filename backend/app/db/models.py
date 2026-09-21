from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from .session import Base

class OnboardingStatus(str, enum.Enum):
    NEW = "NEW"
    ONBOARDING_REQUIRED = "ONBOARDING_REQUIRED"
    ONBOARDING_IN_PROGRESS = "ONBOARDING_IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"

class Role(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    EMPLOYEE = "EMPLOYEE"
    ADMIN = "ADMIN"
    UNASSIGNED = "UNASSIGNED"

class EmployeeRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)
    
    authentication_provider = Column(String, nullable=False, default="google")
    provider_subject_id = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    
    reset_token = Column(String, nullable=True, index=True)
    reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    onboarding_status = Column(String, default=OnboardingStatus.NEW.value, nullable=False)
    role = Column(String, default=Role.UNASSIGNED.value, nullable=False)
    requested_role = Column(String, default=Role.UNASSIGNED.value, nullable=False)
    
    # Customer specific onboarding details
    phone_number = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    language = Column(String, default="English", nullable=False)
    consent_accepted = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    employee_requests = relationship("EmployeeRequest", foreign_keys="EmployeeRequest.user_id", back_populates="user", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String, unique=True, index=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="sessions")

class EmployeeRequest(Base):
    __tablename__ = "employee_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    organization = Column(String, nullable=False)
    department = Column(String, nullable=True)
    employee_id = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    work_email = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    
    status = Column(String, default=EmployeeRequestStatus.PENDING.value, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Admin review tracking
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(String, nullable=True)
    admin_note = Column(String, nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="employee_requests")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

class OTPRecord(Base):
    __tablename__ = "otp_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String, index=True, nullable=False)
    otp_hash = Column(String, nullable=False)
    
    attempts = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ApplicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ADDITIONAL_INFO_REQUIRED = "ADDITIONAL_INFO_REQUIRED"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"

class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    VERIFIED = "VERIFIED"
    PROCESSING = "PROCESSING"
    REJECTED = "REJECTED"
    REQUIRES_REUPLOAD = "REQUIRES_REUPLOAD"

class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    loan_type = Column(String, nullable=False)
    requested_amount = Column(Integer, nullable=False)
    tenure = Column(Integer, nullable=False)
    purpose = Column(String, nullable=False)
    
    employment_info = Column(String, nullable=True)
    income_info = Column(String, nullable=True)
    existing_liabilities = Column(String, nullable=True)
    
    status = Column(String, default=ApplicationStatus.DRAFT.value, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", backref="applications")
    documents = relationship("Document", back_populates="application")
    compliance_checklist_items = relationship("ComplianceChecklistItem", back_populates="application", cascade="all, delete-orphan", order_by="ComplianceChecklistItem.display_order")
    compliance_notes = relationship("ComplianceReviewNote", back_populates="application", cascade="all, delete-orphan", order_by="ComplianceReviewNote.created_at.desc()")

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=True, index=True)
    
    document_type = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    
    status = Column(String, default=DocumentStatus.UPLOADED.value, nullable=False)
    
    # Review tracking
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", foreign_keys=[user_id], backref="documents")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    application = relationship("Application", back_populates="documents")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, nullable=False) # e.g. 'ACTION_REQUIRED', 'STATUS_UPDATE', 'INFO'
    
    is_read = Column(Boolean, default=False, nullable=False)
    related_entity_id = Column(UUID(as_uuid=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", backref="notifications")

class InformationRequestStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESPONDED = "RESPONDED"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"

class AdditionalInformationRequest(Base):
    __tablename__ = "additional_information_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    requested_document_type = Column(String, nullable=True)
    status = Column(String, default=InformationRequestStatus.OPEN.value, nullable=False)
    
    response_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    response_notes = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    application = relationship("Application", backref="information_requests")
    requester = relationship("User", foreign_keys=[requested_by])
    response_document = relationship("Document", foreign_keys=[response_document_id])

class ApplicationAuditEvent(Base):
    __tablename__ = "application_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    event_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", backref="audit_events")
    user = relationship("User")

class ComplianceChecklistStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    REQUIRES_INFORMATION = "REQUIRES_INFORMATION"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class ComplianceChecklistItem(Base):
    __tablename__ = "compliance_checklist_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    item_key = Column(String, nullable=False)
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default=ComplianceChecklistStatus.PENDING.value, nullable=False)
    notes = Column(String, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", back_populates="compliance_checklist_items")
    updated_by_user = relationship("User", foreign_keys=[updated_by])

class ComplianceReviewNote(Base):
    __tablename__ = "compliance_review_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    note = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", back_populates="compliance_notes")
    author = relationship("User", foreign_keys=[author_id])

