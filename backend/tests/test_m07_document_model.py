import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import (
    User, Role, OnboardingStatus, Application, ApplicationStatus,
    Document, DocumentStatus, EmployeeRequest, EmployeeRequestStatus,
    Notification, Session as DBSession, AdditionalInformationRequest,
    ApplicationAuditEvent
)
from app.core.security import create_user_session
from app.api.documents import STORAGE_DIR
import uuid
import io
import shutil
from app.db.session import SessionLocal

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        test_users = db.query(User).filter(User.email.like("test_m07_%@example.com")).all()
        for user in test_users:
            docs = db.query(Document).filter(Document.user_id == user.id).all()
            for d in docs:
                doc_dir = STORAGE_DIR / str(d.id)
                if doc_dir.exists():
                    shutil.rmtree(doc_dir, ignore_errors=True)
            apps = db.query(Application).filter(Application.user_id == user.id).all()
            for app_obj in apps:
                db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.application_id == app_obj.id).delete()
                db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.application_id == app_obj.id).delete()
            db.query(Notification).filter(Notification.user_id == user.id).delete()
            db.query(Document).filter(Document.reviewed_by == user.id).update({Document.reviewed_by: None})
            db.query(Document).filter(Document.user_id == user.id).delete()
            db.query(Application).filter(Application.user_id == user.id).delete()
            db.query(EmployeeRequest).filter((EmployeeRequest.user_id == user.id) | (EmployeeRequest.reviewed_by == user.id)).delete()
            db.query(DBSession).filter(DBSession.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()


def create_user_helper(db, prefix, role=Role.CUSTOMER.value, onboarding_status=OnboardingStatus.COMPLETED.value):
    uid = uuid.uuid4()
    email = f"test_m07_{prefix}_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name=f"User {prefix.capitalize()}",
        role=role,
        requested_role=role,
        onboarding_status=onboarding_status,
        authentication_provider="local",
        provider_subject_id=email,
        phone_number="+919876543210",
        date_of_birth="1992-05-15",
        address="123 Financial District",
        city="Mumbai",
        state="Maharashtra",
        pincode="400051"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if role == Role.EMPLOYEE.value:
        emp_req = EmployeeRequest(
            user_id=user.id,
            organization="PolicyPilot Verification Desk",
            department="Credit & Compliance Operations",
            employee_id=f"EMP-{uid.hex[:4].upper()}",
            designation="Senior Credit Officer",
            work_email=email,
            status=EmployeeRequestStatus.APPROVED.value if onboarding_status == OnboardingStatus.COMPLETED.value else EmployeeRequestStatus.PENDING.value
        )
        db.add(emp_req)
        db.commit()

    token = create_user_session(db, user.id)
    return user, {"session_id": token}


def test_m07_document_schema_columns_exist_and_support_null(db_session):
    """
    Verify that the M07 document metadata columns exist on the Document model
    and that legacy records with NULL values are completely valid.
    """
    customer, cookies_cust = create_user_helper(db_session, "legacy_cust")

    # Create a legacy-style document where all new M07 columns are NULL
    legacy_doc = Document(
        id=uuid.uuid4(),
        user_id=customer.id,
        document_type="IDENTITY_PROOF",
        file_url=f"documents/{uuid.uuid4()}/aadhaar.pdf",
        status=DocumentStatus.UPLOADED.value,
        original_filename=None,
        file_size_bytes=None,
        mime_type=None,
        file_hash=None,
        page_count=None
    )
    db_session.add(legacy_doc)
    db_session.commit()
    db_session.refresh(legacy_doc)

    # Verify attributes exist on ORM instance and default to None
    assert hasattr(legacy_doc, "original_filename")
    assert hasattr(legacy_doc, "file_size_bytes")
    assert hasattr(legacy_doc, "mime_type")
    assert hasattr(legacy_doc, "file_hash")
    assert hasattr(legacy_doc, "page_count")

    assert legacy_doc.original_filename is None
    assert legacy_doc.file_size_bytes is None
    assert legacy_doc.mime_type is None
    assert legacy_doc.file_hash is None
    assert legacy_doc.page_count is None

    # Verify query via Customer GET /api/documents/ returns successfully
    res = client.get("/api/documents/", cookies=cookies_cust)
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) >= 1
    matched = [d for d in docs if d["id"] == str(legacy_doc.id)][0]
    assert matched["original_filename"] is None
    assert matched["file_size_bytes"] is None
    assert matched["mime_type"] is None
    assert matched["file_hash"] is None
    assert matched["page_count"] is None


def test_m07_document_metadata_population(db_session):
    """
    Verify that M07 metadata can be explicitly populated and retrieved through APIs.
    """
    customer, cookies_cust = create_user_helper(db_session, "meta_cust")
    employee, cookies_emp = create_user_helper(db_session, "meta_emp", Role.EMPLOYEE.value)

    app_obj = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=2000000,
        tenure=120,
        purpose="Flat Purchase",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app_obj)

    doc = Document(
        id=uuid.uuid4(),
        user_id=customer.id,
        application_id=app_obj.id,
        document_type="INCOME_PROOF",
        file_url=f"documents/{uuid.uuid4()}/salary_slip.pdf",
        status=DocumentStatus.UPLOADED.value,
        original_filename="salary_slip_aug_2026.pdf",
        file_size_bytes=1048576,
        mime_type="application/pdf",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        page_count=3
    )
    db_session.add(doc)
    db_session.commit()

    # 1. Customer application detail
    res_app = client.get(f"/api/applications/{app_obj.id}", cookies=cookies_cust)
    assert res_app.status_code == 200
    app_data = res_app.json()
    doc_in_app = [d for d in app_data["documents"] if d["id"] == str(doc.id)][0]
    assert doc_in_app["original_filename"] == "salary_slip_aug_2026.pdf"
    assert doc_in_app["file_size_bytes"] == 1048576
    assert doc_in_app["mime_type"] == "application/pdf"
    assert doc_in_app["file_hash"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert doc_in_app["page_count"] == 3

    # 2. Employee application detail
    res_emp = client.get(f"/api/employee/applications/{app_obj.id}", cookies=cookies_emp)
    assert res_emp.status_code == 200
    emp_data = res_emp.json()
    emp_doc = [d for d in emp_data["documents"] if d["id"] == str(doc.id)][0]
    assert emp_doc["original_filename"] == "salary_slip_aug_2026.pdf"
    assert emp_doc["file_size_bytes"] == 1048576
    assert emp_doc["page_count"] == 3

    # 3. Employee documents repository
    res_repo = client.get("/api/employee/documents", cookies=cookies_emp)
    assert res_repo.status_code == 200
    repo_data = res_repo.json()
    repo_doc = [d for d in repo_data if d["id"] == str(doc.id)][0]
    assert repo_doc["original_filename"] == "salary_slip_aug_2026.pdf"
    assert repo_doc["file_size_bytes"] == 1048576
