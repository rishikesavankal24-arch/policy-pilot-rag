import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import (
    User, Role, OnboardingStatus, Application, ApplicationStatus,
    Document, DocumentStatus, EmployeeRequest, EmployeeRequestStatus,
    Notification, Session as DBSession
)
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
        test_users = db.query(User).filter(User.email.like("test_flow_%@example.com")).all()
        from app.db.models import AdditionalInformationRequest, ApplicationAuditEvent
        for user in test_users:
            apps = db.query(Application).filter(Application.user_id == user.id).all()
            for app in apps:
                db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.application_id == app.id).delete()
                db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.application_id == app.id).delete()
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
    email = f"test_flow_{prefix}_{uid.hex[:6]}@example.com"
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
        req = EmployeeRequest(
            user_id=user.id,
            organization="PolicyPilot Operations Desk",
            department="Retail Credit Operations",
            employee_id=f"EMP-{uid.hex[:4].upper()}",
            designation="Senior Credit Officer",
            work_email=f"work_{email}",
            status=EmployeeRequestStatus.APPROVED.value if onboarding_status == OnboardingStatus.COMPLETED.value else EmployeeRequestStatus.PENDING.value
        )
        db.add(req)
        db.commit()

    token = create_user_session(db, user.id)
    return user, token

def test_real_customer_to_employee_workflow(db_session):
    """
    End-to-end integration test verifying the connected real database workflow:
    1. Customer creates Education Loan for INR 8,00,000.
    2. Customer uploads a document attached to the application.
    3. Customer submits application -> status becomes SUBMITTED.
    4. Employee queries Application Queue -> exactly the same application is returned.
    5. Employee opens application detail -> backend transitions status SUBMITTED -> UNDER_REVIEW.
    6. Customer queries application details -> receives updated UNDER_REVIEW status.
    7. Database record is confirmed to be the exact same row with updated status.
    """
    client = TestClient(app)
    
    # 1. Create Customer and Employee
    customer, cust_token = create_user_helper(db_session, "customer", role=Role.CUSTOMER.value)
    employee, emp_token = create_user_helper(db_session, "officer", role=Role.EMPLOYEE.value)
    
    cust_client = TestClient(app, cookies={"session_id": cust_token})
    emp_client = TestClient(app, cookies={"session_id": emp_token})
    
    # Step 1: Customer creates Education Loan (₹8,00,000, 60 months)
    create_payload = {
        "loan_type": "Education Loan",
        "requested_amount": 800000,
        "tenure": 60,
        "purpose": "Postgraduate higher education tuition fees",
        "employment_info": "Salaried Professional",
        "income_info": "1200000",
        "existing_liabilities": "None"
    }
    create_res = cust_client.post("/api/applications/", json=create_payload)
    assert create_res.status_code == 200, create_res.text
    created_app = create_res.json()
    app_id = created_app["id"]
    assert created_app["status"] == "DRAFT"
    assert created_app["requested_amount"] == 800000
    assert created_app["loan_type"] == "Education Loan"
    
    # Verify DRAFT is NOT visible in Employee Queue
    emp_queue_before = emp_client.get("/api/employee/applications")
    assert emp_queue_before.status_code == 200
    assert not any(a["id"] == app_id for a in emp_queue_before.json())
    
    # Step 2: Customer uploads document
    from tests.pdf_fixtures import make_test_pdf_bytes
    file_bytes = make_test_pdf_bytes(1)
    upload_res = cust_client.post(
        "/api/documents/",
        data={"document_type": "ADMISSION_LETTER", "application_id": app_id},
        files={"file": ("admission_offer.pdf", io.BytesIO(file_bytes), "application/pdf")}
    )
    assert upload_res.status_code == 200, upload_res.text
    doc_id = upload_res.json()["id"]
    
    # Step 3: Customer clicks SUBMIT APPLICATION
    submit_res = cust_client.post(f"/api/applications/{app_id}/submit")
    assert submit_res.status_code == 200, submit_res.text
    assert submit_res.json()["status"] == "SUBMITTED"
    
    # Verify database status is SUBMITTED
    db_app = db_session.query(Application).filter(Application.id == app_id).first()
    assert db_app is not None
    assert db_app.status == ApplicationStatus.SUBMITTED.value
    
    # Step 4: Employee opens Application Queue
    emp_queue_res = emp_client.get("/api/employee/applications")
    assert emp_queue_res.status_code == 200
    queue_items = emp_queue_res.json()
    matching = [a for a in queue_items if a["id"] == app_id]
    assert len(matching) == 1, "Submitted application must appear in Employee Queue"
    queue_item = matching[0]
    assert queue_item["loan_type"] == "Education Loan"
    assert queue_item["requested_amount"] == 800000
    assert queue_item["status"] == "SUBMITTED"
    assert queue_item["applicant_name"] == customer.full_name
    assert queue_item["applicant_email"] == customer.email
    assert queue_item["document_count"] == 1
    assert queue_item["customer_display_name"] == customer.full_name
    
    # Step 5: Employee INSPECTS application detail (GET) -> status must REMAIN SUBMITTED (no auto-mutation)
    detail_res = emp_client.get(f"/api/employee/applications/{app_id}")
    assert detail_res.status_code == 200, detail_res.text
    detail_data = detail_res.json()
    assert detail_data["application"]["id"] == app_id
    assert detail_data["application"]["status"] == "SUBMITTED", "Opening application detail must NOT mutate status"
    assert detail_data["applicant"]["full_name"] == customer.full_name
    assert detail_data["applicant"]["email"] == customer.email
    assert len(detail_data["documents"]) == 1
    assert detail_data["documents"][0]["id"] == doc_id
    
    # Verify database status is STILL SUBMITTED after inspection
    db_session.expire_all()
    db_app_after_inspect = db_session.query(Application).filter(Application.id == app_id).first()
    assert db_app_after_inspect.status == ApplicationStatus.SUBMITTED.value, "Database status must remain SUBMITTED on inspect"
    
    # Step 6: Employee clicks START REVIEW (POST /api/employee/applications/{id}/transition-review)
    start_review_res = emp_client.post(f"/api/employee/applications/{app_id}/transition-review")
    assert start_review_res.status_code == 200, start_review_res.text
    review_data = start_review_res.json()
    assert review_data["application"]["status"] == "UNDER_REVIEW"
    
    # Verify database status is now UNDER_REVIEW in PostgreSQL
    db_session.expire_all()
    db_app_updated = db_session.query(Application).filter(Application.id == app_id).first()
    assert db_app_updated.status == ApplicationStatus.UNDER_REVIEW.value
    
    # Step 7: Customer opens Application Details -> verifies status is UNDER_REVIEW
    cust_detail_res = cust_client.get(f"/api/applications/{app_id}")
    assert cust_detail_res.status_code == 200
    cust_view = cust_detail_res.json()
    assert cust_view["application"]["id"] == app_id
    assert cust_view["application"]["status"] == "UNDER_REVIEW"
    
    # Customer list also reflects UNDER_REVIEW
    cust_list_res = cust_client.get("/api/applications/")
    assert cust_list_res.status_code == 200
    assert any(a["id"] == app_id and a["status"] == "UNDER_REVIEW" for a in cust_list_res.json())

def test_authorization_and_isolation_rules(db_session):
    """
    Verifies strict authorization constraints:
    - Customer cannot access another customer's application.
    - Employee cannot review their own application (conflict of interest -> 403).
    - Unverified employee cannot access employee queue or detail (403).
    - Customer cannot access employee queue (403).
    """
    cust_a, token_a = create_user_helper(db_session, "alice", role=Role.CUSTOMER.value)
    cust_b, token_b = create_user_helper(db_session, "bob", role=Role.CUSTOMER.value)
    emp_officer, emp_token = create_user_helper(db_session, "officer_safe", role=Role.EMPLOYEE.value)
    emp_pending, pending_token = create_user_helper(
        db_session, "officer_pending", role=Role.EMPLOYEE.value, onboarding_status=OnboardingStatus.PENDING_VERIFICATION.value
    )
    
    client_a = TestClient(app, cookies={"session_id": token_a})
    client_b = TestClient(app, cookies={"session_id": token_b})
    client_emp = TestClient(app, cookies={"session_id": emp_token})
    client_pending = TestClient(app, cookies={"session_id": pending_token})
    
    # 1. Customer A creates and submits an application
    create_res = client_a.post("/api/applications/", json={
        "loan_type": "Home Loan",
        "requested_amount": 4500000,
        "tenure": 240,
        "purpose": "Apartment purchase in Bengaluru"
    })
    app_id = create_res.json()["id"]
    client_a.post(f"/api/applications/{app_id}/submit")
    
    # 2. Customer B attempts to access Customer A's application -> 404 (isolated)
    cross_get = client_b.get(f"/api/applications/{app_id}")
    assert cross_get.status_code == 404
    
    # 3. Customer B cannot submit or patch Customer A's application
    cross_patch = client_b.patch(f"/api/applications/{app_id}", json={"requested_amount": 100})
    assert cross_patch.status_code == 404
    
    # 4. Customer A cannot access Employee Queue
    emp_access = client_a.get("/api/employee/applications")
    assert emp_access.status_code == 403
    
    # 5. Pending (unverified) employee cannot access Employee Queue
    pending_queue = client_pending.get("/api/employee/applications")
    assert pending_queue.status_code == 403
    
    # 6. Verified employee CAN access the queue and detail
    emp_queue = client_emp.get("/api/employee/applications")
    assert emp_queue.status_code == 200
    assert any(a["id"] == app_id for a in emp_queue.json())
    
    # 7. Employee self-review conflict of interest test
    # If employee creates an application (via DB or if employee submits)
    emp_as_borrower = Application(
        user_id=emp_officer.id,
        loan_type="Employee Personal Facility",
        requested_amount=200000,
        tenure=12,
        purpose="Relocation expenses",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(emp_as_borrower)
    db_session.commit()
    
    # Officer cannot review their own application
    self_review_res = client_emp.get(f"/api/employee/applications/{emp_as_borrower.id}")
    assert self_review_res.status_code == 403
    assert "Conflict of interest" in self_review_res.json()["detail"]
    
    # Nor can they call transition-review on their own application
    self_transition_res = client_emp.post(f"/api/employee/applications/{emp_as_borrower.id}/transition-review")
    assert self_transition_res.status_code == 403
    assert "Conflict of interest" in self_transition_res.json()["detail"]

def test_explicit_transition_endpoint(db_session):
    """
    Verifies POST /api/employee/applications/{id}/transition-review works as expected.
    """
    customer, cust_token = create_user_helper(db_session, "cust_trans", role=Role.CUSTOMER.value)
    employee, emp_token = create_user_helper(db_session, "emp_trans", role=Role.EMPLOYEE.value)
    
    cust_client = TestClient(app, cookies={"session_id": cust_token})
    emp_client = TestClient(app, cookies={"session_id": emp_token})
    
    # Create and submit
    app_res = cust_client.post("/api/applications/", json={
        "loan_type": "Personal Loan",
        "requested_amount": 150000,
        "tenure": 12,
        "purpose": "Medical expenses"
    })
    app_id = app_res.json()["id"]
    cust_client.post(f"/api/applications/{app_id}/submit")
    
    # Explicit transition endpoint
    trans_res = emp_client.post(f"/api/employee/applications/{app_id}/transition-review")
    assert trans_res.status_code == 200
    assert trans_res.json()["application"]["status"] == "UNDER_REVIEW"
    
    # Idempotent call remains UNDER_REVIEW
    trans_res_2 = emp_client.post(f"/api/employee/applications/{app_id}/transition-review")
    assert trans_res_2.status_code == 200
    assert trans_res_2.json()["application"]["status"] == "UNDER_REVIEW"
    
    # Verify rejection on DRAFT application
    draft_app = Application(
        user_id=customer.id,
        loan_type="Draft Loan",
        requested_amount=50000,
        tenure=6,
        purpose="Draft testing",
        status=ApplicationStatus.DRAFT.value
    )
    db_session.add(draft_app)
    db_session.commit()
    draft_trans = emp_client.post(f"/api/employee/applications/{draft_app.id}/transition-review")
    assert draft_trans.status_code == 400
    assert "draft" in draft_trans.json()["detail"].lower()
    
    # Verify rejection on final state (e.g. APPROVED or DECLINED)
    approved_app = Application(
        user_id=customer.id,
        loan_type="Approved Loan",
        requested_amount=50000,
        tenure=6,
        purpose="Approved testing",
        status=ApplicationStatus.APPROVED.value
    )
    db_session.add(approved_app)
    db_session.commit()
    approved_trans = emp_client.post(f"/api/employee/applications/{approved_app.id}/transition-review")
    assert approved_trans.status_code == 400
    assert "already in 'APPROVED' state" in approved_trans.json()["detail"]
