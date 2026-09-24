import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import (
    User, Role, OnboardingStatus, Application, ApplicationStatus,
    Document, DocumentStatus, EmployeeRequest, EmployeeRequestStatus,
    Notification, Session as DBSession, AdditionalInformationRequest,
    ApplicationAuditEvent, ComplianceChecklistStatus, ComplianceChecklistItem,
    ComplianceReviewNote
)
from app.core.security import create_user_session
import uuid
from app.db.session import SessionLocal

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        test_users = db.query(User).filter(User.email.like("test_comp_%@example.com")).all()
        for user in test_users:
            apps = db.query(Application).filter(Application.user_id == user.id).all()
            for app_obj in apps:
                db.query(ComplianceChecklistItem).filter(ComplianceChecklistItem.application_id == app_obj.id).delete()
                db.query(ComplianceReviewNote).filter(ComplianceReviewNote.application_id == app_obj.id).delete()
                db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.application_id == app_obj.id).delete()
                db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.application_id == app_obj.id).delete()
            db.query(ComplianceChecklistItem).filter(ComplianceChecklistItem.updated_by == user.id).delete()
            db.query(ComplianceReviewNote).filter(ComplianceReviewNote.author_id == user.id).delete()
            db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.requested_by == user.id).delete()
            db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.user_id == user.id).delete()
            db.query(Notification).filter(Notification.user_id == user.id).delete()
            db.query(Document).filter((Document.user_id == user.id) | (Document.reviewed_by == user.id)).delete()
            db.query(Application).filter(Application.user_id == user.id).delete()
            db.query(EmployeeRequest).filter((EmployeeRequest.user_id == user.id) | (EmployeeRequest.reviewed_by == user.id)).delete()
            db.query(DBSession).filter(DBSession.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()


def create_user_helper(db, prefix, role=Role.CUSTOMER.value, onboarding_status=OnboardingStatus.COMPLETED.value):
    uid = uuid.uuid4()
    email = f"test_comp_{prefix}_{uid.hex[:6]}@example.com"
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
            organization="PolicyPilot Test Bank",
            department="Credit & Compliance Operations",
            employee_id=f"EMP-{uid.hex[:4]}",
            designation="Senior Compliance Officer",
            work_email=email,
            status=EmployeeRequestStatus.APPROVED.value
        )
        db.add(emp_req)
        db.commit()

    return user


def test_compliance_workspace_authorization_and_draft_rejection(db_session):
    customer = create_user_helper(db_session, "cust", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "emp", role=Role.EMPLOYEE.value)

    # Create draft application for customer
    draft_app = Application(
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=3500000,
        tenure=240,
        purpose="Residential purchase",
        status=ApplicationStatus.DRAFT.value
    )
    db_session.add(draft_app)
    db_session.commit()
    db_session.refresh(draft_app)

    customer_token = create_user_session(db_session, customer.id)
    employee_token = create_user_session(db_session, employee.id)

    # 1. Customer token should be rejected (403 Forbidden)
    resp = client.get(
        f"/api/employee/applications/{draft_app.id}/compliance",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert resp.status_code == 403

    # 2. Employee on draft application should get 400 Bad Request
    resp = client.get(
        f"/api/employee/applications/{draft_app.id}/compliance",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert resp.status_code == 400
    assert "Draft applications" in resp.json()["detail"]


def test_compliance_workspace_conflict_of_interest(db_session):
    employee = create_user_helper(db_session, "emp_owner", role=Role.EMPLOYEE.value)

    # Employee owns this submitted application
    own_app = Application(
        user_id=employee.id,
        loan_type="Personal Loan",
        requested_amount=500000,
        tenure=36,
        purpose="Home Renovation",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(own_app)
    db_session.commit()
    db_session.refresh(own_app)

    emp_token = create_user_session(db_session, employee.id)

    # Self-review must be strictly rejected with 403 Forbidden
    resp = client.get(
        f"/api/employee/applications/{own_app.id}/compliance",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp.status_code == 403
    assert "Conflict of interest" in resp.json()["detail"]


def test_compliance_workspace_initialization_and_zero_mutation(db_session):
    customer = create_user_helper(db_session, "applicant", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "reviewer", role=Role.EMPLOYEE.value)

    app_obj = Application(
        user_id=customer.id,
        loan_type="Vehicle Loan",
        requested_amount=1200000,
        tenure=60,
        purpose="Vehicle Purchase",
        employment_info="Salaried - Senior Software Engineer",
        income_info="1800000 INR p.a.",
        existing_liabilities="None",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(app_obj)

    doc = Document(
        user_id=customer.id,
        document_type="ID_PROOF",
        file_url="/uploads/mock_aadhaar.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(app_obj)
    doc.application_id = app_obj.id
    db_session.commit()

    emp_token = create_user_session(db_session, employee.id)

    # GET compliance workspace
    resp = client.get(
        f"/api/employee/applications/{app_obj.id}/compliance",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify no auto-mutation: application status MUST still be SUBMITTED
    db_session.refresh(app_obj)
    assert app_obj.status == ApplicationStatus.SUBMITTED.value
    assert data["application"]["status"] == ApplicationStatus.SUBMITTED.value

    # Verify standard 5 checklist items seeded in PENDING status
    checklist = data["checklist_items"]
    assert len(checklist) == 5
    for item in checklist:
        assert item["status"] == "PENDING"
        assert item["application_id"] == str(app_obj.id)
    
    keys = [item["item_key"] for item in checklist]
    assert "mandatory_kyc_presence" in keys
    assert "income_obligation_consistency" in keys
    assert "facility_purpose_validation" in keys
    assert "applicant_profile_consistency" in keys
    assert "preliminary_policy_evidence" in keys

    # Verify documents and applicant info returned
    assert len(data["documents"]) == 1
    assert data["applicant"]["full_name"] == customer.full_name
    assert data["applicant"]["email"] == customer.email

    # Verify M10 architectural boundary banner metadata
    assert data["ai_rag_boundary"]["status"] == "M10_RESERVED"


def test_compliance_checklist_update_and_audit_logging(db_session):
    customer = create_user_helper(db_session, "app2", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "officer2", role=Role.EMPLOYEE.value)

    app_obj = Application(
        user_id=customer.id,
        loan_type="Business Loan",
        requested_amount=2500000,
        tenure=48,
        purpose="Working Capital",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app_obj)
    db_session.commit()
    db_session.refresh(app_obj)

    emp_token = create_user_session(db_session, employee.id)

    # Initialize workspace
    resp = client.get(
        f"/api/employee/applications/{app_obj.id}/compliance",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp.status_code == 200
    first_item = resp.json()["checklist_items"][0]
    item_id = first_item["id"]

    # 1. Update checklist item to REVIEWED with notes
    patch_resp = client.patch(
        f"/api/employee/applications/{app_obj.id}/compliance/checklist/{item_id}",
        json={"status": "REVIEWED", "notes": "Aadhaar and PAN verified against government registry."},
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["status"] == "REVIEWED"
    assert updated["notes"] == "Aadhaar and PAN verified against government registry."
    assert updated["updated_by"] == str(employee.id)

    # Verify audit event logged
    audit = (
        db_session.query(ApplicationAuditEvent)
        .filter(
            ApplicationAuditEvent.application_id == app_obj.id,
            ApplicationAuditEvent.event_type == "COMPLIANCE_CHECKLIST_UPDATED"
        )
        .first()
    )
    assert audit is not None
    assert "marked as REVIEWED" in audit.description

    # 2. Update to invalid status -> 400 Bad Request
    invalid_resp = client.patch(
        f"/api/employee/applications/{app_obj.id}/compliance/checklist/{item_id}",
        json={"status": "INVALID_STATE"},
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert invalid_resp.status_code == 400


def test_compliance_officer_review_notes(db_session):
    customer = create_user_helper(db_session, "app3", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "officer3", role=Role.EMPLOYEE.value)

    app_obj = Application(
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=4000000,
        tenure=180,
        purpose="Property Purchase",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app_obj)
    db_session.commit()
    db_session.refresh(app_obj)

    emp_token = create_user_session(db_session, employee.id)

    # 1. Add compliance note
    note_resp = client.post(
        f"/api/employee/applications/{app_obj.id}/compliance/notes",
        json={"note": "Applicant credit history verified across bureau records. No defaults recorded."},
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert note_resp.status_code == 200
    note_data = note_resp.json()
    assert note_data["note"] == "Applicant credit history verified across bureau records. No defaults recorded."
    assert note_data["author_id"] == str(employee.id)
    assert note_data["author_name"] == employee.full_name

    # Verify audit event logged
    audit = (
        db_session.query(ApplicationAuditEvent)
        .filter(
            ApplicationAuditEvent.application_id == app_obj.id,
            ApplicationAuditEvent.event_type == "COMPLIANCE_NOTE_RECORDED"
        )
        .first()
    )
    assert audit is not None
    assert "Compliance review note recorded" in audit.description

    # 2. Add empty note -> 400 Bad Request
    empty_resp = client.post(
        f"/api/employee/applications/{app_obj.id}/compliance/notes",
        json={"note": "   "},
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert empty_resp.status_code == 400

    # 3. Subsequent GET returns the note and audit events
    get_resp = client.get(
        f"/api/employee/applications/{app_obj.id}/compliance",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert get_resp.status_code == 200
    res_data = get_resp.json()
    assert len(res_data["review_notes"]) == 1
    assert res_data["review_notes"][0]["note"] == "Applicant credit history verified across bureau records. No defaults recorded."
    assert any(ae["event_type"] == "COMPLIANCE_NOTE_RECORDED" for ae in res_data["audit_events"])


def test_unverified_employee_forbidden(db_session):
    customer = create_user_helper(db_session, "app_unv", role=Role.CUSTOMER.value)
    unverified_emp = create_user_helper(
        db_session,
        "unv_emp",
        role=Role.EMPLOYEE.value,
        onboarding_status=OnboardingStatus.PENDING_VERIFICATION.value
    )

    app_obj = Application(
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=3000000,
        tenure=120,
        purpose="Flat Purchase",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(app_obj)
    db_session.commit()
    db_session.refresh(app_obj)

    token = create_user_session(db_session, unverified_emp.id)

    resp = client.get(
        f"/api/employee/applications/{app_obj.id}/compliance",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    assert "pending approval" in resp.json()["detail"].lower() or "restricted" in resp.json()["detail"].lower()


def test_application_submission_creates_audit_event_and_timestamp(db_session):
    customer = create_user_helper(db_session, "app_sub", role=Role.CUSTOMER.value)

    # 1. Customer creates draft application
    draft_app = Application(
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=1500000,
        tenure=120,
        purpose="Construction",
        status=ApplicationStatus.DRAFT.value
    )
    db_session.add(draft_app)
    db_session.commit()
    db_session.refresh(draft_app)

    cust_token = create_user_session(db_session, customer.id)

    # 2. Customer submits the application
    resp = client.post(
        f"/api/applications/{draft_app.id}/submit",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == ApplicationStatus.SUBMITTED.value

    # 3. Verify APPLICATION_SUBMITTED audit event was created
    audit = (
        db_session.query(ApplicationAuditEvent)
        .filter(
            ApplicationAuditEvent.application_id == draft_app.id,
            ApplicationAuditEvent.event_type == "APPLICATION_SUBMITTED"
        )
        .first()
    )
    assert audit is not None
    assert audit.user_id == customer.id
    assert audit.created_at is not None
    assert "formally submitted" in audit.description


def test_compliance_workspace_timestamps_and_customer_notes_isolation(db_session):
    customer = create_user_helper(db_session, "iso_cust", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "iso_emp", role=Role.EMPLOYEE.value)

    app_obj = Application(
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=2000000,
        tenure=180,
        purpose="Flat Purchase",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app_obj)
    db_session.commit()
    db_session.refresh(app_obj)

    emp_token = create_user_session(db_session, employee.id)
    cust_token = create_user_session(db_session, customer.id)

    # Add internal note
    note_resp = client.post(
        f"/api/employee/applications/{app_obj.id}/compliance/notes",
        json={"note": "CONFIDENTIAL INTERNAL NOTE: Credit risk score acceptable."},
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert note_resp.status_code == 200

    # Customer fetches their application
    cust_get_resp = client.get(
        f"/api/applications/{app_obj.id}",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert cust_get_resp.status_code == 200
    cust_data = cust_get_resp.json()

    # Verify customer payload does NOT contain compliance notes, audit trail, or checklist
    assert "review_notes" not in cust_data
    assert "compliance_notes" not in cust_data
    assert "audit_events" not in cust_data
    assert "checklist_items" not in cust_data
    assert "readiness" not in cust_data
    # Content of the internal note must not leak into customer response
    assert "CONFIDENTIAL INTERNAL NOTE" not in str(cust_data)
