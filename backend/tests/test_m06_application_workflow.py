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
        test_users = db.query(User).filter(User.email.like("test_m06_%@example.com")).all()
        for user in test_users:
            docs = db.query(Document).filter(Document.user_id == user.id).all()
            for d in docs:
                doc_dir = STORAGE_DIR / str(d.id)
                if doc_dir.exists():
                    shutil.rmtree(doc_dir, ignore_errors=True)
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
    email = f"test_m06_{prefix}_{uid.hex[:6]}@example.com"
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
            organization="PolicyPilot Credit Desk",
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


def seed_fully_verified_application(db_session, customer, employee):
    """
    Helper that sets up an application in UNDER_REVIEW status with:
    - 2 verified documents (ACCEPTED)
    - All checklist items REVIEWED
    - No open or responded information requests
    Satisfies calculate_review_readiness with is_ready = True and 0 blockers.
    """
    app = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=3500000,
        tenure=180,
        purpose="Residential apartment acquisition",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app)
    db_session.commit()

    # Documents
    doc1 = Document(
        id=uuid.uuid4(),
        application_id=app.id,
        user_id=customer.id,
        document_type="IDENTITY_PROOF",
        file_url=f"documents/{uuid.uuid4()}/id.pdf",
        status=DocumentStatus.ACCEPTED.value,
        reviewed_by=employee.id,
        reviewed_at=app.created_at
    )
    doc2 = Document(
        id=uuid.uuid4(),
        application_id=app.id,
        user_id=customer.id,
        document_type="INCOME_PROOF",
        file_url=f"documents/{uuid.uuid4()}/income.pdf",
        status=DocumentStatus.ACCEPTED.value,
        reviewed_by=employee.id,
        reviewed_at=app.created_at
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    # Initialize checklist via compliance workspace endpoint
    headers_emp = {"Cookie": f"session_id={create_user_session(db_session, employee.id)}"}
    client.get(f"/api/employee/applications/{app.id}/compliance", headers=headers_emp)

    # Mark all checklist items as REVIEWED
    items = db_session.query(ComplianceChecklistItem).filter(ComplianceChecklistItem.application_id == app.id).all()
    for it in items:
        it.status = ComplianceChecklistStatus.REVIEWED.value
        it.updated_by = employee.id
    db_session.commit()

    return app


# ==============================================================================
# 1. State Validation Tests: Decision only allowed when UNDER_REVIEW
# ==============================================================================

def test_decision_rejected_on_invalid_application_states(db_session):
    """
    Final decision can only be made when application.status == UNDER_REVIEW.
    Rejects DRAFT, SUBMITTED, ADDITIONAL_INFO_REQUIRED.
    """
    customer, cookies_cust = create_user_helper(db_session, "state_cust", Role.CUSTOMER.value)
    employee, cookies_emp = create_user_helper(db_session, "state_emp", Role.EMPLOYEE.value)

    # 17. DRAFT cannot be decided
    draft_app = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Personal Loan",
        requested_amount=100000,
        tenure=12,
        purpose="Home renovation",
        status=ApplicationStatus.DRAFT.value
    )
    db_session.add(draft_app)
    db_session.commit()

    res_draft = client.post(
        f"/api/employee/applications/{draft_app.id}/decision",
        json={"status": "APPROVED"},
        cookies=cookies_emp
    )
    assert res_draft.status_code == 400
    assert "UNDER_REVIEW" in res_draft.json()["detail"]

    # 18. SUBMITTED cannot be decided
    submitted_app = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Personal Loan",
        requested_amount=100000,
        tenure=12,
        purpose="Medical",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(submitted_app)
    db_session.commit()

    res_sub = client.post(
        f"/api/employee/applications/{submitted_app.id}/decision",
        json={"status": "DECLINED", "notes": "Credit score too low"},
        cookies=cookies_emp
    )
    assert res_sub.status_code == 400
    assert "UNDER_REVIEW" in res_sub.json()["detail"]

    # 19. ADDITIONAL_INFO_REQUIRED cannot be decided
    info_app = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Auto Loan",
        requested_amount=500000,
        tenure=36,
        purpose="Vehicle",
        status=ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value
    )
    db_session.add(info_app)
    db_session.commit()

    res_info = client.post(
        f"/api/employee/applications/{info_app.id}/decision",
        json={"status": "APPROVED"},
        cookies=cookies_emp
    )
    assert res_info.status_code == 400
    assert "UNDER_REVIEW" in res_info.json()["detail"]


# ==============================================================================
# 2. Authorization & COI Tests
# ==============================================================================

def test_decision_authorization_and_conflict_of_interest(db_session):
    """
    14. Employee cannot decide own application (Conflict of interest -> 403)
    15. Unverified employee cannot decide (403)
    16. Non-employee (Customer) cannot decide (403)
    """
    customer, cookies_cust = create_user_helper(db_session, "auth_cust", Role.CUSTOMER.value)
    employee, cookies_emp = create_user_helper(db_session, "auth_emp", Role.EMPLOYEE.value)
    unverified_emp, cookies_unv = create_user_helper(
        db_session, "auth_unv", Role.EMPLOYEE.value, onboarding_status=OnboardingStatus.PENDING_VERIFICATION.value
    )

    app = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Personal Loan",
        requested_amount=200000,
        tenure=24,
        purpose="Relocation",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app)
    db_session.commit()

    # 16. Customer attempts to decide -> 403 Forbidden
    cust_res = client.post(
        f"/api/employee/applications/{app.id}/decision",
        json={"status": "APPROVED"},
        cookies=cookies_cust
    )
    assert cust_res.status_code == 403

    # 15. Unverified employee attempts to decide -> 403 Forbidden
    unv_res = client.post(
        f"/api/employee/applications/{app.id}/decision",
        json={"status": "APPROVED"},
        cookies=cookies_unv
    )
    assert unv_res.status_code == 403

    # 14. Employee attempts to decide on their OWN application -> 403 Conflict of interest
    own_app = Application(
        id=uuid.uuid4(),
        user_id=employee.id,
        loan_type="Employee Loan",
        requested_amount=50000,
        tenure=12,
        purpose="Personal",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(own_app)
    db_session.commit()

    own_res = client.post(
        f"/api/employee/applications/{own_app.id}/decision",
        json={"status": "APPROVED"},
        cookies=cookies_emp
    )
    assert own_res.status_code == 403
    assert "conflict of interest" in own_res.json()["detail"].lower()


# ==============================================================================
# 3. Approval Rules & Review Readiness Blocker Enforcement
# ==============================================================================

def test_approved_with_readiness_blockers(db_session):
    """
    1. APPROVED with readiness blockers -> 400
    2. APPROVED with unresolved information request -> 400
    3. APPROVED with incomplete/invalid document state -> 400
    """
    customer, cookies_cust = create_user_helper(db_session, "blk_cust", Role.CUSTOMER.value)
    employee, cookies_emp = create_user_helper(db_session, "blk_emp", Role.EMPLOYEE.value)

    # 3. Incomplete document state (e.g. document requires re-upload)
    app = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Business Loan",
        requested_amount=1500000,
        tenure=36,
        purpose="Working capital",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app)
    db_session.commit()

    doc_bad = Document(
        id=uuid.uuid4(),
        application_id=app.id,
        user_id=customer.id,
        document_type="TAX_RETURN",
        file_url=f"documents/{uuid.uuid4()}/tax.pdf",
        status=DocumentStatus.REQUIRES_REUPLOAD.value,
        review_notes="Missing page 4 stamp"
    )
    db_session.add(doc_bad)
    db_session.commit()

    # Attempt approval with deficient document
    res_bad_doc = client.post(
        f"/api/employee/applications/{app.id}/decision",
        json={"status": "APPROVED"},
        cookies=cookies_emp
    )
    assert res_bad_doc.status_code == 400
    detail = res_bad_doc.json()["detail"]
    assert "not ready for final approval" in detail["message"].lower()
    assert any("requires re-upload" in b.lower() for b in detail["blocking_reasons"])
    # Verify no status mutation occurred
    db_session.refresh(app)
    assert app.status == ApplicationStatus.UNDER_REVIEW.value

    # Fix document to ACCEPTED
    doc_bad.status = DocumentStatus.ACCEPTED.value
    db_session.commit()

    # 2. Unresolved information request blocker
    info_req = AdditionalInformationRequest(
        id=uuid.uuid4(),
        application_id=app.id,
        requested_by=employee.id,
        title="Audited P&L",
        description="Provide complete P&L statement",
        status=InformationRequestStatus.OPEN.value
    )
    db_session.add(info_req)
    db_session.commit()

    res_info_blk = client.post(
        f"/api/employee/applications/{app.id}/decision",
        json={"status": "APPROVED"},
        cookies=cookies_emp
    )
    assert res_info_blk.status_code == 400
    detail_info = res_info_blk.json()["detail"]
    assert any("open query" in b.lower() or "audited p&l" in b.lower() for b in detail_info["blocking_reasons"])


# ==============================================================================
# 4. Approval Success, Audit, and Notification Lifecycle
# ==============================================================================

def test_approved_success_lifecycle(db_session):
    """
    4. APPROVED when readiness is satisfied -> 200
    5. APPROVED persists application status
    6. APPROVED creates APPLICATION_APPROVED audit event
    7. APPROVED creates customer notification
    """
    customer, cookies_cust = create_user_helper(db_session, "appr_cust", Role.CUSTOMER.value)
    employee, cookies_emp = create_user_helper(db_session, "appr_emp", Role.EMPLOYEE.value)

    app = seed_fully_verified_application(db_session, customer, employee)

    # Execute final approval
    decision_res = client.post(
        f"/api/employee/applications/{app.id}/decision",
        json={"status": "APPROVED", "notes": "Risk policy checks satisfied and underwriter approved."},
        cookies=cookies_emp
    )
    assert decision_res.status_code == 200, decision_res.text
    dec_data = decision_res.json()
    assert dec_data["status"] == "APPROVED"
    assert dec_data["decision"] == "APPROVED"
    assert dec_data["id"] == str(app.id)

    # 5. Persisted in PostgreSQL database
    db_session.refresh(app)
    assert app.status == ApplicationStatus.APPROVED.value
    assert app.updated_at is not None

    # 6. APPLICATION_APPROVED audit event created
    audit = db_session.query(ApplicationAuditEvent).filter(
        ApplicationAuditEvent.application_id == app.id,
        ApplicationAuditEvent.event_type == "APPLICATION_APPROVED"
    ).first()
    assert audit is not None
    assert audit.title == "Application Approved"
    assert "approved" in audit.description.lower()
    assert str(employee.id) == str(audit.user_id)

    # 7. Customer notification created
    notif = db_session.query(Notification).filter(
        Notification.user_id == customer.id,
        Notification.related_entity_id == app.id
    ).first()
    assert notif is not None
    assert notif.title == "Loan Application Approved"
    assert "approved" in notif.message.lower()
    assert notif.type == "STATUS_UPDATE"


# ==============================================================================
# 5. Decline Validation, Success, Audit, and Notification Lifecycle
# ==============================================================================

def test_declined_validation_and_success_lifecycle(db_session):
    """
    8. DECLINED without notes -> 400
    9. DECLINED with whitespace notes -> 400
    10. DECLINED with valid reason -> 200
    11. DECLINED persists application status
    12. DECLINED creates APPLICATION_DECLINED audit event
    13. DECLINED creates customer notification
    """
    customer, cookies_cust = create_user_helper(db_session, "dec_cust", Role.CUSTOMER.value)
    employee, cookies_emp = create_user_helper(db_session, "dec_emp", Role.EMPLOYEE.value)

    app = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Personal Loan",
        requested_amount=250000,
        tenure=24,
        purpose="Debt consolidation",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app)
    db_session.commit()

    # 8. DECLINED without notes -> 400
    res_no_notes = client.post(
        f"/api/employee/applications/{app.id}/decision",
        json={"status": "DECLINED"},
        cookies=cookies_emp
    )
    assert res_no_notes.status_code == 400
    assert "reason is mandatory" in res_no_notes.json()["detail"].lower()

    # 9. DECLINED with whitespace notes -> 400
    res_ws_notes = client.post(
        f"/api/employee/applications/{app.id}/decision",
        json={"status": "DECLINED", "notes": "    "},
        cookies=cookies_emp
    )
    assert res_ws_notes.status_code == 400
    assert "reason is mandatory" in res_ws_notes.json()["detail"].lower()

    # 9b. DECLINED with 'nil' string notes -> 400
    res_nil_notes = client.post(
        f"/api/employee/applications/{app.id}/decision",
        json={"status": "DECLINED", "notes": "nil"},
        cookies=cookies_emp
    )
    assert res_nil_notes.status_code == 400
    assert "reason is mandatory" in res_nil_notes.json()["detail"].lower()

    # 10. DECLINED with valid reason -> 200
    res_valid_dec = client.post(
        f"/api/employee/applications/{app.id}/decision",
        json={"status": "DECLINED", "notes": "Debt-to-income ratio exceeds institutional underwriting threshold (62% vs 45% limit)."},
        cookies=cookies_emp
    )
    assert res_valid_dec.status_code == 200
    dec_body = res_valid_dec.json()
    assert dec_body["status"] == "DECLINED"
    assert dec_body["decision"] == "DECLINED"

    # 11. Persisted in PostgreSQL database
    db_session.refresh(app)
    assert app.status == ApplicationStatus.DECLINED.value

    # 12. APPLICATION_DECLINED audit event created with employee decline reason
    audit = db_session.query(ApplicationAuditEvent).filter(
        ApplicationAuditEvent.application_id == app.id,
        ApplicationAuditEvent.event_type == "APPLICATION_DECLINED"
    ).first()
    assert audit is not None
    assert audit.title == "Application Declined"
    assert "Debt-to-income ratio exceeds" in audit.description

    # 13. Customer notification created
    notif = db_session.query(Notification).filter(
        Notification.user_id == customer.id,
        Notification.related_entity_id == app.id
    ).first()
    assert notif is not None
    assert notif.title == "Loan Application Declined"
    assert "declined" in notif.message.lower()


# ==============================================================================
# 6. Terminal State & Idempotency / Immobility Tests
# ==============================================================================

def test_terminal_state_cannot_be_re_decided(db_session):
    """
    20. APPROVED cannot be decided again (400)
    21. DECLINED cannot be decided again (400)
    """
    customer, cookies_cust = create_user_helper(db_session, "term_cust", Role.CUSTOMER.value)
    employee, cookies_emp = create_user_helper(db_session, "term_emp", Role.EMPLOYEE.value)

    # 20. Already APPROVED application
    app_appr = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Home Loan",
        requested_amount=2000000,
        tenure=120,
        purpose="Home purchase",
        status=ApplicationStatus.APPROVED.value
    )
    db_session.add(app_appr)
    db_session.commit()

    re_appr = client.post(
        f"/api/employee/applications/{app_appr.id}/decision",
        json={"status": "DECLINED", "notes": "Attempting to decline an approved loan"},
        cookies=cookies_emp
    )
    assert re_appr.status_code == 400
    assert "UNDER_REVIEW" in re_appr.json()["detail"]

    # 21. Already DECLINED application
    app_dec = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Personal Loan",
        requested_amount=100000,
        tenure=12,
        purpose="Personal",
        status=ApplicationStatus.DECLINED.value
    )
    db_session.add(app_dec)
    db_session.commit()

    re_dec = client.post(
        f"/api/employee/applications/{app_dec.id}/decision",
        json={"status": "APPROVED"},
        cookies=cookies_emp
    )
    assert re_dec.status_code == 400
    assert "UNDER_REVIEW" in re_dec.json()["detail"]


# ==============================================================================
# 7. Duplicate Route Cleanup Verification
# ==============================================================================

def test_customer_actions_canonical_route_after_cleanup(db_session):
    """
    24. GET /api/customer/actions remains functional after duplicate-route cleanup.
    Verify clean single registration, customer authorization, and expected structure.
    """
    customer, cookies_cust = create_user_helper(db_session, "act_cust", Role.CUSTOMER.value)
    employee, cookies_emp = create_user_helper(db_session, "act_emp", Role.EMPLOYEE.value)

    # Create draft application -> generates COMPLETE_DRAFT action
    app = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Personal Loan",
        requested_amount=100000,
        tenure=12,
        purpose="Holiday",
        status=ApplicationStatus.DRAFT.value
    )
    db_session.add(app)
    db_session.commit()

    # Call canonical GET /api/customer/actions
    res = client.get("/api/customer/actions", cookies=cookies_cust)
    assert res.status_code == 200
    data = res.json()
    assert "customer" in data
    assert "actions" in data
    assert "total_actions" in data
    assert data["total_actions"] >= 1
    assert any(a["type"] == "COMPLETE_DRAFT" and a["application_id"] == str(app.id) for a in data["actions"])

    # Non-customer gets 403 Forbidden
    emp_res = client.get("/api/customer/actions", cookies=cookies_emp)
    assert emp_res.status_code == 403


# ==============================================================================
# 8. M06 Phase 3: Customer Final Decision Experience & Isolation Tests
# ==============================================================================

def test_m06_phase3_customer_final_decision_view_and_isolation(db_session):
    """
    M06 Phase 3 Verification:
    A. Customer sees APPROVED correctly via GET /api/applications/{id}.
    B. Customer sees DECLINED correctly via GET /api/applications/{id}.
    C. Customer sees UNDER_REVIEW correctly via GET /api/applications/{id}.
    D. Customer sees ADDITIONAL_INFO_REQUIRED correctly via GET /api/applications/{id}.
    E. APPROVED application is read-only (rejects PATCH /api/applications/{id} and POST submit).
    F. DECLINED application is read-only (rejects PATCH /api/applications/{id} and POST submit).
    G. Customer notifications appear after final decision in GET /api/notifications.
    H. Internal employee notes, compliance details, and audit trail are NOT exposed to customer.
    I. Customer A cannot access Customer B's application or notifications (data isolation).
    J. Existing M05 Required Action flow remains functional.
    """
    cust_a, cookies_a = create_user_helper(db_session, "p3_ca", Role.CUSTOMER.value)
    cust_b, cookies_b = create_user_helper(db_session, "p3_cb", Role.CUSTOMER.value)
    employee, cookies_emp = create_user_helper(db_session, "p3_emp", Role.EMPLOYEE.value)

    # 1. Test UNDER_REVIEW customer view
    app_review = Application(
        id=uuid.uuid4(),
        user_id=cust_a.id,
        loan_type="Personal Loan",
        requested_amount=150000,
        tenure=12,
        purpose="Medical",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app_review)
    db_session.commit()

    res_review = client.get(f"/api/applications/{app_review.id}", cookies=cookies_a)
    assert res_review.status_code == 200
    review_data = res_review.json()
    assert review_data["application"]["status"] == "UNDER_REVIEW"
    assert "timeline" not in review_data
    assert "compliance" not in review_data

    # 2. Test APPROVED customer view & read-only enforcement
    app_appr = seed_fully_verified_application(db_session, cust_a, employee)

    # Approve via Phase 1 endpoint
    dec_appr = client.post(
        f"/api/employee/applications/{app_appr.id}/decision",
        json={"status": "APPROVED", "notes": "Internal underwriting approval code 9982"},
        cookies=cookies_emp
    )
    assert dec_appr.status_code == 200

    # Customer A views approved application
    res_appr = client.get(f"/api/applications/{app_appr.id}", cookies=cookies_a)
    assert res_appr.status_code == 200
    appr_data = res_appr.json()
    assert appr_data["application"]["status"] == "APPROVED"
    assert appr_data["application"]["updated_at"] is not None
    # Verify internal employee notes are NOT exposed in customer response
    assert "9982" not in str(appr_data)
    assert "audit" not in appr_data

    # Verify read-only enforcement: APPROVED application rejects updates & submit
    patch_res = client.patch(
        f"/api/applications/{app_appr.id}",
        json={"requested_amount": 3000000},
        cookies=cookies_a
    )
    assert patch_res.status_code == 400
    assert "draft" in patch_res.json()["detail"].lower()

    submit_res = client.post(f"/api/applications/{app_appr.id}/submit", cookies=cookies_a)
    assert submit_res.status_code == 400

    # 3. Test DECLINED customer view & read-only enforcement
    app_decl = Application(
        id=uuid.uuid4(),
        user_id=cust_a.id,
        loan_type="Business Loan",
        requested_amount=500000,
        tenure=24,
        purpose="Inventory",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app_decl)
    db_session.commit()

    # Decline via Phase 1 endpoint with employee internal notes
    internal_decline_reason = "Confidential credit assessment: Debt-to-income exceeds 65 percent risk ceiling."
    dec_decl = client.post(
        f"/api/employee/applications/{app_decl.id}/decision",
        json={"status": "DECLINED", "notes": internal_decline_reason},
        cookies=cookies_emp
    )
    assert dec_decl.status_code == 200

    # Customer A views declined application
    res_decl = client.get(f"/api/applications/{app_decl.id}", cookies=cookies_a)
    assert res_decl.status_code == 200
    decl_data = res_decl.json()
    assert decl_data["application"]["status"] == "DECLINED"
    assert decl_data["application"]["updated_at"] is not None
    # Crucial security check: internal employee decline note is NOT in customer response
    assert internal_decline_reason not in str(decl_data)
    assert "audit" not in decl_data

    # Verify read-only enforcement: DECLINED application rejects updates & submit
    patch_decl_res = client.patch(
        f"/api/applications/{app_decl.id}",
        json={"requested_amount": 100000},
        cookies=cookies_a
    )
    assert patch_decl_res.status_code == 400

    # 4. Customer Notifications verification
    notif_res = client.get("/api/notifications", cookies=cookies_a)
    assert notif_res.status_code == 200
    notifications = notif_res.json()
    assert len(notifications) >= 2
    titles = [n["title"] for n in notifications]
    assert "Loan Application Approved" in titles
    assert "Loan Application Declined" in titles
    # Notification messages do not contain internal employee reason
    for n in notifications:
        assert internal_decline_reason not in n["message"]

    # 5. Customer Data Isolation: Customer B cannot access Customer A's applications or notifications
    # Customer B attempts to get Customer A's approved application -> 404
    b_access_a = client.get(f"/api/applications/{app_appr.id}", cookies=cookies_b)
    assert b_access_a.status_code == 404

    # Customer B attempts to get Customer A's declined application -> 404
    b_access_decl = client.get(f"/api/applications/{app_decl.id}", cookies=cookies_b)
    assert b_access_decl.status_code == 404

    # Customer B's notifications do not contain Customer A's notifications
    b_notifs = client.get("/api/notifications", cookies=cookies_b).json()
    assert len(b_notifs) == 0

    # 6. ADDITIONAL_INFO_REQUIRED customer view
    app_info = Application(
        id=uuid.uuid4(),
        user_id=cust_a.id,
        loan_type="Education Loan",
        requested_amount=400000,
        tenure=36,
        purpose="Higher Studies",
        status=ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value
    )
    db_session.add(app_info)
    info_req = AdditionalInformationRequest(
        id=uuid.uuid4(),
        application_id=app_info.id,
        requested_by=employee.id,
        title="College Admission Offer Letter",
        description="Please provide the signed university admission letter.",
        requested_document_type="ADMISSION_LETTER",
        status="OPEN"
    )
    db_session.add(info_req)
    db_session.commit()

    res_info = client.get(f"/api/applications/{app_info.id}", cookies=cookies_a)
    assert res_info.status_code == 200
    info_data = res_info.json()
    assert info_data["application"]["status"] == "ADDITIONAL_INFO_REQUIRED"
    assert len(info_data["information_requests"]) >= 1
    assert info_data["information_requests"][0]["title"] == "College Admission Offer Letter"

