import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import User, Role, OnboardingStatus, Application, Document, Session as DBSession
from app.core.security import create_user_session
import uuid
import io
from app.db.session import SessionLocal

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        from app.db.models import ApplicationAuditEvent, AdditionalInformationRequest
        test_users = db.query(User).filter(User.email.like("test_portal_%@example.com")).all()
        for user in test_users:
            apps = db.query(Application).filter(Application.user_id == user.id).all()
            for app_obj in apps:
                db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.application_id == app_obj.id).delete()
                db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.application_id == app_obj.id).delete()
            db.query(Document).filter(Document.user_id == user.id).delete()
            db.query(Application).filter(Application.user_id == user.id).delete()
            db.query(DBSession).filter(DBSession.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()

def create_test_customer(db, email_prefix, role=Role.CUSTOMER.value, requested_role=Role.CUSTOMER.value, status=OnboardingStatus.COMPLETED.value):
    uid = uuid.uuid4()
    email = f"test_portal_{email_prefix}_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name=f"Customer {email_prefix.capitalize()}",
        role=role,
        requested_role=requested_role,
        onboarding_status=status,
        authentication_provider="local",
        provider_subject_id=email
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_user_session(db, user.id)
    return user, token

def test_customer_application_lifecycle_and_isolation(db_session):
    client = TestClient(app)
    
    # 1. Create two distinct customers
    customer_a, token_a = create_test_customer(db_session, "alpha")
    customer_b, token_b = create_test_customer(db_session, "beta")
    
    client_a = TestClient(app, cookies={"session_id": token_a})
    client_b = TestClient(app, cookies={"session_id": token_b})
    
    # 2. Customer A creates a new draft loan application
    app_payload = {
        "loan_type": "Personal Loan",
        "requested_amount": 250000,
        "tenure": 24,
        "purpose": "Home renovation and repairs",
        "employment_info": "Software Engineer",
        "income_info": "85000",
        "existing_liabilities": "None"
    }
    create_res = client_a.post("/api/applications/", json=app_payload)
    assert create_res.status_code == 200, create_res.text
    created_app = create_res.json()
    app_id = created_app["id"]
    assert created_app["status"] == "DRAFT"
    assert created_app["requested_amount"] == 250000
    assert created_app["purpose"] == "Home renovation and repairs"
    
    # 3. Customer A updates draft application
    update_payload = {
        "requested_amount": 300000,
        "tenure": 36,
        "purpose": "Major home renovation and energy upgrades"
    }
    patch_res = client_a.patch(f"/api/applications/{app_id}", json=update_payload)
    assert patch_res.status_code == 200, patch_res.text
    updated_app = patch_res.json()
    assert updated_app["requested_amount"] == 300000
    assert updated_app["tenure"] == 36
    
    # 4. Customer A uploads an attached document
    from tests.pdf_fixtures import make_test_pdf_bytes
    file_content = make_test_pdf_bytes(1)
    upload_res = client_a.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF", "application_id": app_id},
        files={"file": ("aadhaar.pdf", io.BytesIO(file_content), "application/pdf")}
    )
    assert upload_res.status_code == 200, upload_res.text
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    assert doc_data["application_id"] == app_id
    assert doc_data["document_type"] == "IDENTITY_PROOF"
    
    # 5. Customer A reads application details: verify info + attached documents
    get_res = client_a.get(f"/api/applications/{app_id}")
    assert get_res.status_code == 200, get_res.text
    detail_data = get_res.json()
    assert detail_data["application"]["id"] == app_id
    assert detail_data["application"]["status"] == "DRAFT"
    assert detail_data["application"]["requested_amount"] == 300000
    assert len(detail_data["documents"]) == 1
    assert detail_data["documents"][0]["id"] == doc_id
    
    # 6. Customer B cannot access Customer A's application (Ownership verification)
    unauthorized_get = client_b.get(f"/api/applications/{app_id}")
    assert unauthorized_get.status_code == 404
    
    # Customer B cannot update Customer A's application
    unauthorized_patch = client_b.patch(f"/api/applications/{app_id}", json={"requested_amount": 999999})
    assert unauthorized_patch.status_code == 404
    
    # Customer B cannot submit Customer A's application
    unauthorized_submit = client_b.post(f"/api/applications/{app_id}/submit")
    assert unauthorized_submit.status_code == 404
    
    # Customer B cannot delete Customer A's document
    unauthorized_doc_del = client_b.delete(f"/api/documents/{doc_id}")
    assert unauthorized_doc_del.status_code == 404
    
    # 7. Customer A submits draft application
    submit_res = client_a.post(f"/api/applications/{app_id}/submit")
    assert submit_res.status_code == 200, submit_res.text
    submitted_app = submit_res.json()
    assert submitted_app["status"] == "SUBMITTED"
    
    # 8. Verify refresh / re-query persists SUBMITTED state in PostgreSQL
    verify_res = client_a.get(f"/api/applications/{app_id}")
    assert verify_res.status_code == 200
    persisted_app = verify_res.json()
    assert persisted_app["application"]["status"] == "SUBMITTED"
    
    # 9. Verify editing is forbidden once submitted
    blocked_patch = client_a.patch(f"/api/applications/{app_id}", json={"requested_amount": 500000})
    assert blocked_patch.status_code == 400
    assert "draft" in blocked_patch.json()["detail"].lower()
    
    # 10. Verify duplicate submission is rejected
    duplicate_submit = client_a.post(f"/api/applications/{app_id}/submit")
    assert duplicate_submit.status_code == 400
    assert "draft" in duplicate_submit.json()["detail"].lower()
    
    # 11. Customer A dashboard summary accurately reflects real state
    summary_res = client_a.get("/api/customer/dashboard/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["applications"]["total"] == 1
    assert summary["documents"]["total"] == 1
    assert len(summary["applications"]["recent"]) == 1
    assert summary["applications"]["recent"][0]["status"] == "SUBMITTED"
    
    # 12. Customer A profile update and retrieval
    prof_patch = client_a.patch("/api/customer/profile", json={
        "phone_number": "+919876543210",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001"
    })
    assert prof_patch.status_code == 200
    
    prof_get = client_a.get("/api/customer/profile")
    assert prof_get.status_code == 200
    prof = prof_get.json()
    assert prof["city"] == "Bengaluru"
    assert prof["pincode"] == "560001"

def test_customer_onboarding_assigns_customer_role(db_session):
    # User begins as newly authenticated user (e.g. from Google OAuth)
    new_user, token = create_test_customer(
        db_session, 
        "onboard_test", 
        role=Role.UNASSIGNED.value, 
        requested_role=Role.UNASSIGNED.value, 
        status=OnboardingStatus.NEW.value
    )
    client = TestClient(app, cookies={"session_id": token})
    
    # User completes customer onboarding
    onboard_payload = {
        "phone_number": "+919888877777",
        "full_name": "Verified Onboarded Customer",
        "language": "en",
        "consent_accepted": True
    }
    res = client.post("/onboarding/customer", json=onboard_payload)
    assert res.status_code == 200, res.text
    
    # Verify in DB: role=CUSTOMER, requested_role=CUSTOMER, onboarding_status=COMPLETED
    db_session.refresh(new_user)
    assert new_user.role == Role.CUSTOMER.value
    assert new_user.requested_role == Role.CUSTOMER.value
    assert new_user.onboarding_status == OnboardingStatus.COMPLETED.value
    
    # Now user can immediately access customer dashboard summary with HTTP 200
    dash_res = client.get("/api/customer/dashboard/summary")
    assert dash_res.status_code == 200, dash_res.text
    dash_data = dash_res.json()
    assert dash_data["customer"]["name"] == "Verified Onboarded Customer"

def test_non_customer_users_blocked_from_customer_endpoints(db_session):
    # 1. Employee user
    emp_user, emp_token = create_test_customer(
        db_session,
        "employee_block",
        role=Role.EMPLOYEE.value,
        requested_role=Role.EMPLOYEE.value,
        status=OnboardingStatus.COMPLETED.value
    )
    emp_client = TestClient(app, cookies={"session_id": emp_token})
    
    assert emp_client.get("/api/customer/dashboard/summary").status_code == 403
    assert emp_client.get("/api/customer/profile").status_code == 403
    assert emp_client.get("/api/applications/").status_code == 403
    assert emp_client.get("/api/documents/").status_code == 403
    assert emp_client.get("/api/notifications/").status_code == 403

    # 2. Unassigned / pending user who merely requests CUSTOMER without completion
    unassigned_user, unassigned_token = create_test_customer(
        db_session,
        "unassigned_block",
        role=Role.UNASSIGNED.value,
        requested_role=Role.CUSTOMER.value,
        status=OnboardingStatus.NEW.value
    )
    unassigned_client = TestClient(app, cookies={"session_id": unassigned_token})
    
    # Mere requested_role="CUSTOMER" does NOT grant access when role is UNASSIGNED
    assert unassigned_client.get("/api/customer/dashboard/summary").status_code == 403
    assert unassigned_client.get("/api/customer/profile").status_code == 403
    assert unassigned_client.get("/api/applications/").status_code == 403

def test_repaired_existing_customer_can_access_dashboard_and_auth_me(db_session):
    # Verify the exact state of repaired user
    customer, token = create_test_customer(
        db_session,
        "repaired_customer",
        role=Role.CUSTOMER.value,
        requested_role=Role.CUSTOMER.value,
        status=OnboardingStatus.COMPLETED.value
    )
    client = TestClient(app, cookies={"session_id": token})
    
    # 1. Verify GET /auth/me returns 200 with role CUSTOMER
    me_res = client.get("/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["role"] == Role.CUSTOMER.value
    assert me_data["requested_role"] == Role.CUSTOMER.value
    assert me_data["onboarding_status"] == OnboardingStatus.COMPLETED.value
    
    # 2. Verify GET /api/customer/dashboard/summary returns 200
    dash_res = client.get("/api/customer/dashboard/summary")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "customer" in dash_data
    assert "applications" in dash_data
    assert "documents" in dash_data
    assert "notifications" in dash_data


def test_customer_dashboard_operational_metrics_and_ai_boundary(db_session):
    customer, token = create_test_customer(
        db_session,
        "metrics_customer",
        role=Role.CUSTOMER.value,
        requested_role=Role.CUSTOMER.value,
        status=OnboardingStatus.COMPLETED.value
    )
    client = TestClient(app, cookies={"session_id": token})
    
    # 1. Create a draft application
    app_res = client.post("/api/applications/", json={
        "loan_type": "Home Loan",
        "requested_amount": 4500000,
        "tenure": 120,
        "purpose": "Apartment acquisition",
        "employment_info": "Senior Software Architect",
        "income_info": "180000",
        "existing_liabilities": "None"
    })
    assert app_res.status_code == 200
    app_id = app_res.json()["id"]

    # 2. Dashboard summary reflects draft count & required actions
    dash_res = client.get("/api/customer/dashboard/summary")
    assert dash_res.status_code == 200
    data = dash_res.json()
    assert data["applications"]["draft"] == 1
    assert data["applications"]["approved"] == 0
    assert len(data["required_actions"]) >= 1
    # Check that the draft action has been generated
    draft_actions = [a for a in data["required_actions"] if a["type"] == "COMPLETE_DRAFT"]
    assert len(draft_actions) == 1
    assert draft_actions[0]["link"] == f"/dashboard/applications/{app_id}"

    # 3. Test AI boundary query with application context
    ai_res = client.post("/api/customer/ai/query", json={
        "query": "What are the required documents for my Home Loan application?",
        "application_id": app_id
    })
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    assert ai_data["customer_safe"] is True
    assert ai_data["application_context"]["id"] == app_id
    assert ai_data["application_context"]["loan_type"] == "Home Loan"
    assert "AI compliance assistance is being prepared" in ai_data["explanation"]

    # 4. Unauthorized customer cannot query another customer's application
    other_customer, other_token = create_test_customer(
        db_session,
        "unauth_ai_cust",
        role=Role.CUSTOMER.value,
        requested_role=Role.CUSTOMER.value,
        status=OnboardingStatus.COMPLETED.value
    )
    other_client = TestClient(app, cookies={"session_id": other_token})
    unauth_ai = other_client.post("/api/customer/ai/query", json={
        "query": "Can I see this application?",
        "application_id": app_id
    })
    assert unauth_ai.status_code == 404

    # 5. Dedicated GET /api/customer/actions returns real required actions
    actions_res = client.get("/api/customer/actions")
    assert actions_res.status_code == 200
    actions_data = actions_res.json()
    assert "actions" in actions_data
    assert len(actions_data["actions"]) >= 1
    draft_act = next(a for a in actions_data["actions"] if a["type"] == "COMPLETE_DRAFT")
    assert draft_act["action_url"] == f"/dashboard/applications/{app_id}"
    assert draft_act["application_id"] == app_id


def test_customer_new_loan_application_creation_regression(db_session):
    """
    Regression test for customer loan application creation:
    1. Valid frontend payload creates application in DRAFT status via both /api/applications and /api/applications/
    2. Empty optional fields are saved cleanly as null
    3. Application appears in customer applications list and is isolated to this customer
    4. Proper validation errors are raised for invalid inputs (amount <= 0, tenure <= 0, empty purpose/loan_type)
    """
    customer, token = create_test_customer(
        db_session,
        "app_create_cust",
        role=Role.CUSTOMER.value,
        requested_role=Role.CUSTOMER.value,
        status=OnboardingStatus.COMPLETED.value
    )
    client = TestClient(app, cookies={"session_id": token})

    # Test 1: POST to /api/applications (without trailing slash) - exact payload matching frontend
    frontend_payload = {
        "loan_type": "Home Loan",
        "requested_amount": 50000,
        "tenure": 24,
        "purpose": "Home purchase and renovation",
        "employment_info": "Software Engineer at Tech Corp",
        "income_info": "58555",
        "existing_liabilities": "1200"
    }

    res_no_slash = client.post("/api/applications", json=frontend_payload)
    assert res_no_slash.status_code == 200
    app_data = res_no_slash.json()
    assert app_data["loan_type"] == "Home Loan"
    assert app_data["requested_amount"] == 50000
    assert app_data["tenure"] == 24
    assert app_data["purpose"] == "Home purchase and renovation"
    assert app_data["status"] == "DRAFT"  # Must remain DRAFT, not automatically submitted
    assert app_data["income_info"] == "58555"
    assert app_data["existing_liabilities"] == "1200"

    # Test 2: POST to /api/applications/ (with trailing slash) with empty optional fields (sent as null)
    payload_null_optionals = {
        "loan_type": "Personal Loan",
        "requested_amount": 25000,
        "tenure": 12,
        "purpose": "Personal medical expenses",
        "employment_info": None,
        "income_info": None,
        "existing_liabilities": None
    }

    res_slash = client.post("/api/applications/", json=payload_null_optionals)
    assert res_slash.status_code == 200
    app_slash_data = res_slash.json()
    assert app_slash_data["loan_type"] == "Personal Loan"
    assert app_slash_data["requested_amount"] == 25000
    assert app_slash_data["status"] == "DRAFT"
    assert app_slash_data["employment_info"] is None
    assert app_slash_data["income_info"] is None
    assert app_slash_data["existing_liabilities"] is None

    # Test 3: Verify created applications appear in My Applications
    list_res = client.get("/api/applications")
    assert list_res.status_code == 200
    apps_list = list_res.json()
    created_ids = [a["id"] for a in apps_list]
    assert app_data["id"] in created_ids
    assert app_slash_data["id"] in created_ids

    # Test 4: Validation error - requested_amount <= 0
    invalid_amt = client.post("/api/applications", json={
        "loan_type": "Home Loan",
        "requested_amount": 0,
        "tenure": 24,
        "purpose": "Home renovation"
    })
    assert invalid_amt.status_code == 422
    assert "Requested amount must be greater than 0" in invalid_amt.text

    # Test 5: Validation error - tenure <= 0
    invalid_tenure = client.post("/api/applications", json={
        "loan_type": "Home Loan",
        "requested_amount": 50000,
        "tenure": 0,
        "purpose": "Home renovation"
    })
    assert invalid_tenure.status_code == 422
    assert "Tenure must be greater than 0" in invalid_tenure.text

    # Test 6: Validation error - empty purpose
    invalid_purpose = client.post("/api/applications", json={
        "loan_type": "Home Loan",
        "requested_amount": 50000,
        "tenure": 12,
        "purpose": "   "
    })
    assert invalid_purpose.status_code == 422
    assert "Purpose is required" in invalid_purpose.text

