import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import (
    User, Role, OnboardingStatus, Application, ApplicationStatus,
    Document, DocumentStatus, EmployeeRequest, EmployeeRequestStatus,
    Notification, Session as DBSession, AdditionalInformationRequest,
    ApplicationAuditEvent, ComplianceChecklistStatus, ComplianceChecklistItem,
    ComplianceReviewNote, ReviewReadinessState, InformationRequestStatus
)
from app.core.security import create_user_session
import uuid
import io
from app.db.session import SessionLocal

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        test_users = db.query(User).filter(User.email.like("test_rr_%@example.com")).all()
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
    email = f"test_rr_{prefix}_{uid.hex[:6]}@example.com"
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


def test_review_readiness_authorization_and_coi(db_session):
    customer = create_user_helper(db_session, "cust", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "emp", role=Role.EMPLOYEE.value)
    employee_applicant = create_user_helper(db_session, "emp_app", role=Role.EMPLOYEE.value)

    # 1. Customer application
    app = Application(
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=4000000,
        tenure=180,
        purpose="Property purchase",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(app)

    # 2. Draft application
    draft_app = Application(
        user_id=customer.id,
        loan_type="Personal Loan",
        requested_amount=200000,
        tenure=24,
        purpose="Renovation",
        status=ApplicationStatus.DRAFT.value
    )
    db_session.add(draft_app)

    # 3. Employee self-application (COI)
    emp_app = Application(
        user_id=employee_applicant.id,
        loan_type="Home Loan",
        requested_amount=5000000,
        tenure=240,
        purpose="Flat acquisition",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(emp_app)

    db_session.commit()

    cust_token = create_user_session(db_session, customer.id)
    emp_token = create_user_session(db_session, employee.id)
    emp_app_token = create_user_session(db_session, employee_applicant.id)

    # Customer forbidden from readiness endpoints (403)
    resp = client.get(
        f"/api/employee/applications/{app.id}/review-readiness",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert resp.status_code == 403

    resp = client.post(
        f"/api/employee/applications/{app.id}/review-readiness/mark-ready",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert resp.status_code == 403

    # Draft application returns 400 Bad Request
    resp = client.get(
        f"/api/employee/applications/{draft_app.id}/review-readiness",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp.status_code == 400
    assert "Draft applications" in resp.json()["detail"]

    # Conflict of Interest: employee cannot inspect or mark own application (403)
    resp = client.get(
        f"/api/employee/applications/{emp_app.id}/review-readiness",
        headers={"Authorization": f"Bearer {emp_app_token}"}
    )
    assert resp.status_code == 403
    assert "Conflict of interest" in resp.json()["detail"]

    resp = client.post(
        f"/api/employee/applications/{emp_app.id}/review-readiness/mark-ready",
        headers={"Authorization": f"Bearer {emp_app_token}"}
    )
    assert resp.status_code == 403


def test_readiness_blockers_calculation_and_mark_ready_rejection(db_session):
    customer = create_user_helper(db_session, "cust2", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "emp2", role=Role.EMPLOYEE.value)

    app = Application(
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=3000000,
        tenure=120,
        purpose="House renovation",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(app)
    db_session.commit()

    emp_token = create_user_session(db_session, employee.id)

    # 1. Initialize compliance workspace so checklist items are seeded
    resp = client.get(
        f"/api/employee/applications/{app.id}/compliance",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp.status_code == 200
    workspace = resp.json()
    assert workspace["readiness"] is not None
    assert workspace["readiness"]["is_ready"] is False
    assert workspace["readiness"]["can_mark_ready"] is False
    assert len(workspace["readiness"]["blocking_reasons"]) > 0

    # 2. Check explicit GET /review-readiness endpoint
    resp = client.get(
        f"/api/employee/applications/{app.id}/review-readiness",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp.status_code == 200
    readiness = resp.json()
    assert readiness["is_ready"] is False
    assert readiness["status"] == ReviewReadinessState.PENDING_REVIEW_PREPARATION.value
    # Should flag missing documents and pending checklist items
    blocker_str = " ".join(readiness["blocking_reasons"])
    assert "No verification documents" in blocker_str
    assert "checklist item" in blocker_str

    # 3. Trying to mark ready while blockers exist must fail with 400
    resp = client.post(
        f"/api/employee/applications/{app.id}/review-readiness/mark-ready",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp.status_code == 400
    err_detail = resp.json()["detail"]
    assert "All blockers must be resolved" in err_detail["message"]
    assert len(err_detail["blocking_reasons"]) > 0


def test_mark_review_ready_succeeds_when_all_prerequisites_met(db_session):
    customer = create_user_helper(db_session, "cust3", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "emp3", role=Role.EMPLOYEE.value)

    app = Application(
        user_id=customer.id,
        loan_type="Business Loan",
        requested_amount=1500000,
        tenure=60,
        purpose="Machinery purchase",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app)
    db_session.commit()

    emp_token = create_user_session(db_session, employee.id)

    # 1. Seed checklist by opening workspace
    client.get(
        f"/api/employee/applications/{app.id}/compliance",
        headers={"Authorization": f"Bearer {emp_token}"}
    )

    # 2. Add an accepted document
    doc = Document(
        user_id=customer.id,
        application_id=app.id,
        document_type="PAN_CARD",
        file_url="documents/test/pan.pdf",
        status=DocumentStatus.ACCEPTED.value,
        reviewed_by=employee.id
    )
    db_session.add(doc)
    db_session.commit()

    # 3. Mark all checklist items as REVIEWED
    checklist_items = db_session.query(ComplianceChecklistItem).filter(ComplianceChecklistItem.application_id == app.id).all()
    assert len(checklist_items) == 5
    for it in checklist_items:
        it.status = ComplianceChecklistStatus.REVIEWED.value
        it.notes = "Verified against standard regulatory guideline"
        it.updated_by = employee.id
    db_session.commit()

    # 4. Fetch readiness now -> must have 0 blockers!
    resp = client.get(
        f"/api/employee/applications/{app.id}/review-readiness",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp.status_code == 200
    readiness = resp.json()
    assert readiness["is_ready"] is True
    assert readiness["can_mark_ready"] is True
    assert len(readiness["blocking_reasons"]) == 0

    # 5. Mark Review Ready succeeds (200)
    resp = client.post(
        f"/api/employee/applications/{app.id}/review-readiness/mark-ready",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp.status_code == 200
    ready_data = resp.json()
    assert ready_data["status"] == ReviewReadinessState.READY_FOR_COMPLIANCE_ASSESSMENT.value
    assert ready_data["is_ready"] is True
    assert ready_data["can_mark_ready"] is False
    assert ready_data["updated_by"] == str(employee.id)

    # 6. Verify COMPLIANCE_REVIEW_READY audit event
    audit = db_session.query(ApplicationAuditEvent).filter(
        ApplicationAuditEvent.application_id == app.id,
        ApplicationAuditEvent.event_type == "COMPLIANCE_REVIEW_READY"
    ).first()
    assert audit is not None
    assert "ready for compliance assessment" in audit.description.lower()


def test_review_readiness_invalidation_lifecycle(db_session):
    customer = create_user_helper(db_session, "cust4", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "emp4", role=Role.EMPLOYEE.value)

    app = Application(
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=2500000,
        tenure=120,
        purpose="Apartment purchase",
        status=ApplicationStatus.UNDER_REVIEW.value,
        review_readiness_status=ReviewReadinessState.READY_FOR_COMPLIANCE_ASSESSMENT.value
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    doc = Document(
        user_id=customer.id,
        application_id=app.id,
        document_type="AADHAAR_CARD",
        file_url="documents/test/aadhaar.pdf",
        status=DocumentStatus.ACCEPTED.value,
        reviewed_by=employee.id
    )
    db_session.add(doc)
    db_session.commit()

    emp_token = create_user_session(db_session, employee.id)
    cust_token = create_user_session(db_session, customer.id)

    # Seed checklist items and mark reviewed
    client.get(
        f"/api/employee/applications/{app.id}/compliance",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    checklist_items = db_session.query(ComplianceChecklistItem).filter(ComplianceChecklistItem.application_id == app.id).all()
    for it in checklist_items:
        it.status = ComplianceChecklistStatus.REVIEWED.value
    db_session.commit()

    # --- Scenario A: Checklist item set back to PENDING invalidates readiness ---
    target_item = checklist_items[0]
    resp = client.patch(
        f"/api/employee/applications/{app.id}/compliance/checklist/{target_item.id}",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"status": "PENDING", "notes": "Re-evaluation requested"}
    )
    assert resp.status_code == 200

    # Application readiness must now be PENDING_REVIEW_PREPARATION
    db_session.refresh(app)
    assert app.review_readiness_status == ReviewReadinessState.PENDING_REVIEW_PREPARATION.value

    # Check audit event logged
    audit = db_session.query(ApplicationAuditEvent).filter(
        ApplicationAuditEvent.application_id == app.id,
        ApplicationAuditEvent.event_type == "COMPLIANCE_REVIEW_READINESS_RESET"
    ).order_by(ApplicationAuditEvent.created_at.desc()).first()
    assert audit is not None
    assert "reset from READY_FOR_COMPLIANCE_ASSESSMENT to PENDING_REVIEW_PREPARATION" in audit.description

    # --- Re-mark ready ---
    target_item.status = ComplianceChecklistStatus.REVIEWED.value
    app.review_readiness_status = ReviewReadinessState.READY_FOR_COMPLIANCE_ASSESSMENT.value
    db_session.commit()

    # --- Scenario B: Document marked REQUIRES_REUPLOAD invalidates readiness ---
    resp = client.post(
        f"/api/employee/documents/{doc.id}/review",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"status": "REQUIRES_REUPLOAD", "reason": "Watermark obscured signature"}
    )
    assert resp.status_code == 200
    db_session.refresh(app)
    assert app.review_readiness_status == ReviewReadinessState.PENDING_REVIEW_PREPARATION.value

    # --- Re-mark ready ---
    doc.status = DocumentStatus.ACCEPTED.value
    app.review_readiness_status = ReviewReadinessState.READY_FOR_COMPLIANCE_ASSESSMENT.value
    db_session.commit()

    # --- Scenario C: Customer uploading new document invalidates readiness ---
    file_bytes = b"%PDF-1.4 test uploaded content"
    resp = client.post(
        "/api/documents/",
        headers={"Authorization": f"Bearer {cust_token}"},
        data={"document_type": "SALARY_SLIP", "application_id": str(app.id)},
        files={"file": ("salary.pdf", file_bytes, "application/pdf")}
    )
    assert resp.status_code == 200
    db_session.refresh(app)
    assert app.review_readiness_status == ReviewReadinessState.PENDING_REVIEW_PREPARATION.value

    # --- Re-mark ready ---
    app.review_readiness_status = ReviewReadinessState.READY_FOR_COMPLIANCE_ASSESSMENT.value
    db_session.commit()

    # --- Scenario D: Manual reset via POST /review-readiness/reset ---
    resp = client.post(
        f"/api/employee/applications/{app.id}/review-readiness/reset",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"reason": "Audit committee periodic re-check"}
    )
    assert resp.status_code == 200
    reset_data = resp.json()
    assert reset_data["status"] == ReviewReadinessState.PENDING_REVIEW_PREPARATION.value
    db_session.refresh(app)
    assert app.review_readiness_status == ReviewReadinessState.PENDING_REVIEW_PREPARATION.value


def test_customer_api_data_isolation(db_session):
    customer = create_user_helper(db_session, "cust5", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "emp5", role=Role.EMPLOYEE.value)

    app = Application(
        user_id=customer.id,
        loan_type="Education Loan",
        requested_amount=800000,
        tenure=36,
        purpose="Higher education tuition",
        status=ApplicationStatus.UNDER_REVIEW.value,
        review_readiness_status=ReviewReadinessState.READY_FOR_COMPLIANCE_ASSESSMENT.value
    )
    db_session.add(app)
    db_session.commit()

    cust_token = create_user_session(db_session, customer.id)

    # Customer fetches their application
    resp = client.get(
        f"/api/applications/{app.id}",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert resp.status_code == 200
    cust_view = resp.json()

    # review_readiness_status must NOT be exposed in Customer API
    assert "review_readiness_status" not in cust_view
    assert "readiness" not in cust_view
    assert "checklist_items" not in cust_view
    assert "review_notes" not in cust_view


def test_audit_reason_sanitization_and_truthful_fallbacks(db_session):
    customer = create_user_helper(db_session, "cust6", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "emp6", role=Role.EMPLOYEE.value)

    app = Application(
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=3500000,
        tenure=120,
        purpose="Purchase apartment",
        status=ApplicationStatus.UNDER_REVIEW.value,
        review_readiness_status=ReviewReadinessState.PENDING_REVIEW_PREPARATION.value
    )
    db_session.add(app)
    db_session.commit()

    doc = Document(
        user_id=customer.id,
        application_id=app.id,
        document_type="PAN_CARD",
        file_url="/uploads/test_pan.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    emp_token = create_user_session(db_session, employee.id)

    # 1. Attempt review with "nil" reason -> HTTP 400
    resp_nil = client.post(
        f"/api/employee/documents/{doc.id}/review",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"status": "REQUIRES_REUPLOAD", "reason": "nil"}
    )
    assert resp_nil.status_code == 400
    assert "reason is required" in resp_nil.json()["detail"].lower()

    # 2. Attempt review with valid reason -> HTTP 200
    valid_reason = "Official stamp is truncated on page 1"
    resp_valid = client.post(
        f"/api/employee/documents/{doc.id}/review",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"status": "REQUIRES_REUPLOAD", "reason": valid_reason}
    )
    assert resp_valid.status_code == 200
    db_session.refresh(doc)
    assert doc.review_notes == valid_reason

    # Verify audit event has real reason
    audit_ev = db_session.query(ApplicationAuditEvent).filter(
        ApplicationAuditEvent.application_id == app.id,
        ApplicationAuditEvent.description.like("%PAN CARD%")
    ).first()
    assert audit_ev is not None
    assert f"Reason: {valid_reason}" in audit_ev.description

    # 3. Simulate historical record with Reason: nil in audit description and review_notes = "nil"
    historical_doc = Document(
        user_id=customer.id,
        application_id=app.id,
        document_type="SALARY_SLIP",
        file_url="/uploads/hist_salary.pdf",
        status=DocumentStatus.REQUIRES_REUPLOAD.value,
        review_notes="nil"
    )
    db_session.add(historical_doc)

    hist_audit = ApplicationAuditEvent(
        application_id=app.id,
        user_id=employee.id,
        event_type="DOCUMENT_REQUIRES_REUPLOAD",
        title="Document Review: SALARY_SLIP marked REQUIRES_REUPLOAD",
        description="Employee reviewed SALARY_SLIP. Marked as REQUIRES_REUPLOAD. Reason: nil"
    )
    db_session.add(hist_audit)
    db_session.commit()

    # Fetch Compliance Workspace
    ws_resp = client.get(
        f"/api/employee/applications/{app.id}/compliance",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert ws_resp.status_code == 200
    ws_data = ws_resp.json()

    # Check that historical audit event description displays "Reason not recorded"
    hist_ev_in_ws = next((e for e in ws_data["audit_events"] if "SALARY_SLIP" in e["title"]), None)
    assert hist_ev_in_ws is not None
    assert "Reason: nil" not in hist_ev_in_ws["description"]
    assert "Reason: Reason not recorded" in hist_ev_in_ws["description"]

    # Check that historical document review notes displays "Reason not recorded"
    hist_doc_in_ws = next((d for d in ws_data["documents"] if d["document_type"] == "SALARY_SLIP"), None)
    assert hist_doc_in_ws is not None
    assert hist_doc_in_ws["review_notes"] == "Reason not recorded"

    # Fetch Employee Application Detail (timeline and docs)
    detail_resp = client.get(
        f"/api/employee/applications/{app.id}",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()

    hist_tl_in_detail = next((t for t in detail_data["timeline"] if "SALARY_SLIP" in t["title"]), None)
    assert hist_tl_in_detail is not None
    assert "Reason: nil" not in hist_tl_in_detail["description"]
    assert "Reason: Reason not recorded" in hist_tl_in_detail["description"]

    hist_doc_in_detail = next((d for d in detail_data["documents"] if d["document_type"] == "SALARY_SLIP"), None)
    assert hist_doc_in_detail is not None
    assert hist_doc_in_detail["review_notes"] == "Reason not recorded"


def test_workflow_distinction_and_info_request_resolution(db_session):
    """
    Tests M05.4 Correction Pass:
    1. Existing document -> Require Re-upload (Mandatory deficiency reason, blocks readiness, shows DOCUMENT_REPLACEMENT_REQUIRED to customer).
    2. Missing/new information -> Additional Information Request (shows ADDITIONAL_INFORMATION_REQUIRED to customer, blocks readiness).
    3. Customer sees them as distinct workflows on dashboard actions.
    4. Customer replaces deficient document -> clears REQUIRES_REUPLOAD.
    5. Customer responds to info request -> transitions to RESPONDED.
    6. Employee resolves RESPONDED request -> transitions to RESOLVED, audit event created, readiness unblocks.
    7. Customer isolation: customer cannot access compliance readiness or notes endpoints.
    """
    customer = create_user_helper(db_session, "dist_cust", role=Role.CUSTOMER.value)
    employee = create_user_helper(db_session, "dist_emp", role=Role.EMPLOYEE.value)

    cust_token = create_user_session(db_session, customer.id)
    emp_token = create_user_session(db_session, employee.id)

    # 1. Create submitted application
    app = Application(
        user_id=customer.id,
        loan_type="Business Loan",
        requested_amount=2500000,
        tenure=36,
        purpose="Inventory expansion",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    # Initialize checklist so checklist checks pass
    checklist_resp = client.get(
        f"/api/employee/applications/{app.id}/compliance",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert checklist_resp.status_code == 200
    # Mark all checklist items as REVIEWED
    items = db_session.query(ComplianceChecklistItem).filter(ComplianceChecklistItem.application_id == app.id).all()
    for it in items:
        it.status = ComplianceChecklistStatus.REVIEWED.value
    db_session.commit()

    # Upload existing document: GST_CERTIFICATE
    doc = Document(
        user_id=customer.id,
        application_id=app.id,
        document_type="GST_CERTIFICATE",
        file_url="documents/sample_gst.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # RULE 1: Employee reviews existing document -> requires re-upload
    reup_resp = client.post(
        f"/api/employee/documents/{doc.id}/review",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"status": "REQUIRES_REUPLOAD", "reason": "Page 2 missing official tax seal and signature"}
    )
    assert reup_resp.status_code == 200
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.REQUIRES_REUPLOAD.value
    assert doc.review_notes == "Page 2 missing official tax seal and signature"

    # RULE 2: Employee needs NEW information not previously submitted -> Additional Information Request
    info_resp = client.post(
        f"/api/employee/applications/{app.id}/information-requests",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={
            "title": "Audited Balance Sheet FY2025",
            "description": "Please provide complete audited balance sheet with schedule notes",
            "requested_document_type": "AUDITED_BALANCE_SHEET"
        }
    )
    assert info_resp.status_code == 200
    info_req_id = info_resp.json()["id"]

    # Readiness check: blocked by both REQUIRES_REUPLOAD and OPEN information request
    readiness_resp = client.get(
        f"/api/employee/applications/{app.id}/review-readiness",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert readiness_resp.status_code == 200
    readiness_data = readiness_resp.json()
    assert readiness_data["is_ready"] is False
    assert any("requires re-upload" in r for r in readiness_data["blocking_reasons"])
    assert any("pending applicant response" in r for r in readiness_data["blocking_reasons"])

    # 3. Customer actions check: Verify customer sees TWO visually distinct workflows
    cust_actions_resp = client.get(
        "/api/customer/actions",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert cust_actions_resp.status_code == 200
    cust_actions = cust_actions_resp.json()["actions"]
    action_types = [a["type"] for a in cust_actions]

    assert "DOCUMENT_REPLACEMENT_REQUIRED" in action_types
    assert "INFORMATION_REQUEST" in action_types

    reup_action = next(a for a in cust_actions if a["type"] == "DOCUMENT_REPLACEMENT_REQUIRED")
    assert "Page 2 missing official tax seal" in reup_action["description"]
    assert reup_action["action_label"] == "Replace Document"

    inforeq_action = next(a for a in cust_actions if a["type"] == "INFORMATION_REQUEST")
    assert "Additional Information Required: Audited Balance Sheet" in inforeq_action["title"]
    assert inforeq_action["action_label"] == "Respond / Upload"

    # 4. Customer replaces deficient document
    replace_file_bytes = io.BytesIO(b"%PDF-1.4 fresh new clear GST document")
    replace_resp = client.post(
        "/api/documents/",
        headers={"Authorization": f"Bearer {cust_token}"},
        data={
            "document_type": "GST_CERTIFICATE",
            "application_id": str(app.id),
            "replaces_document_id": str(doc.id)
        },
        files={"file": ("new_gst.pdf", replace_file_bytes, "application/pdf")}
    )
    assert replace_resp.status_code == 200
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.UPLOADED.value
    assert doc.review_notes is None

    # Verify DOCUMENT_REPLACED audit event exists
    rep_audit = db_session.query(ApplicationAuditEvent).filter(
        ApplicationAuditEvent.application_id == app.id,
        ApplicationAuditEvent.event_type == "DOCUMENT_REPLACED"
    ).first()
    assert rep_audit is not None

    # Accept the replaced document so document checks pass
    client.post(
        f"/api/employee/documents/{doc.id}/review",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"status": "ACCEPTED"}
    )

    # 5. Customer responds to Additional Information Request
    info_file_bytes = io.BytesIO(b"%PDF-1.4 audited balance sheet fy2025")
    cust_respond_resp = client.post(
        f"/api/customer/applications/{app.id}/information-requests/{info_req_id}/respond",
        headers={"Authorization": f"Bearer {cust_token}"},
        data={"notes": "Attached statutory audit report and signed schedules."},
        files={"file": ("balance_sheet.pdf", info_file_bytes, "application/pdf")}
    )
    assert cust_respond_resp.status_code == 200
    info_req_db = db_session.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.id == info_req_id).first()
    assert info_req_db.status == InformationRequestStatus.RESPONDED.value
    assert info_req_db.responded_at is not None

    # Readiness check: still blocked because RESPONDED query is awaiting underwriter review
    readiness_resp2 = client.get(
        f"/api/employee/applications/{app.id}/review-readiness",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert readiness_resp2.status_code == 200
    assert readiness_resp2.json()["is_ready"] is False
    assert any("Applicant responded" in r for r in readiness_resp2.json()["blocking_reasons"])

    # 6. Employee reviews response and RESOLVES the information request
    resolve_resp = client.post(
        f"/api/employee/applications/{app.id}/information-requests/{info_req_id}/resolve",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"notes": "Audited financials verified against MCA portal filings."}
    )
    assert resolve_resp.status_code == 200
    db_session.refresh(info_req_db)
    assert info_req_db.status == InformationRequestStatus.RESOLVED.value
    assert info_req_db.resolved_at is not None

    # Verify ADDITIONAL_INFO_RESOLVED audit event exists
    res_audit = db_session.query(ApplicationAuditEvent).filter(
        ApplicationAuditEvent.application_id == app.id,
        ApplicationAuditEvent.event_type == "ADDITIONAL_INFO_RESOLVED"
    ).first()
    assert res_audit is not None
    assert "Audited financials verified" in res_audit.description

    # Also accept the response document uploaded for the info request so all docs are verified
    resp_doc = db_session.query(Document).filter(Document.id == info_req_db.response_document_id).first()
    if resp_doc:
        client.post(
            f"/api/employee/documents/{resp_doc.id}/review",
            headers={"Authorization": f"Bearer {emp_token}"},
            json={"status": "ACCEPTED"}
        )

    # 7. Readiness check: NOW UNBLOCKED!
    readiness_final = client.get(
        f"/api/employee/applications/{app.id}/review-readiness",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert readiness_final.status_code == 200
    final_data = readiness_final.json()
    assert final_data["is_ready"] is True
    assert len(final_data["blocking_reasons"]) == 0
    assert "All 1 information request(s) resolved" in final_data["completed_checks"]

    # 8. Customer isolation check
    cust_forbidden_readiness = client.get(
        f"/api/employee/applications/{app.id}/review-readiness",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert cust_forbidden_readiness.status_code == 403

    cust_forbidden_compliance = client.get(
        f"/api/employee/applications/{app.id}/compliance",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert cust_forbidden_compliance.status_code == 403

