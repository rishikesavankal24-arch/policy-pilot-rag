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
from app.db.session import SessionLocal

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        from app.db.models import ApplicationAuditEvent, AdditionalInformationRequest
        test_users = db.query(User).filter(User.email.like("test_emp_%@example.com")).all()
        for user in test_users:
            apps = db.query(Application).filter(Application.user_id == user.id).all()
            for app_obj in apps:
                db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.application_id == app_obj.id).delete()
                db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.application_id == app_obj.id).delete()
            db.query(Notification).filter(Notification.user_id == user.id).delete()
            db.query(Document).filter(Document.user_id == user.id).delete()
            db.query(Application).filter(Application.user_id == user.id).delete()
            db.query(EmployeeRequest).filter(EmployeeRequest.user_id == user.id).delete()
            db.query(DBSession).filter(DBSession.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()

def create_test_user(db, prefix, role=Role.EMPLOYEE.value, status=OnboardingStatus.COMPLETED.value):
    uid = uuid.uuid4()
    email = f"test_emp_{prefix}_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name=f"Officer {prefix.capitalize()}",
        role=role,
        requested_role=role,
        onboarding_status=status,
        authentication_provider="local",
        provider_subject_id=email
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if role == Role.EMPLOYEE.value:
        req = EmployeeRequest(
            user_id=user.id,
            organization="State Bank Operations Desk",
            department="Credit & Underwriting",
            employee_id=f"EMP-{uid.hex[:4].upper()}",
            designation="Senior Credit Officer",
            work_email=f"work_{email}",
            status=EmployeeRequestStatus.APPROVED.value if status == OnboardingStatus.COMPLETED.value else EmployeeRequestStatus.PENDING.value
        )
        db.add(req)
        db.commit()

    token = create_user_session(db, user.id)
    return user, token

def test_employee_portal_authorization_guards(db_session):
    client = TestClient(app)
    
    # 1. Customer user attempts to access employee routes -> 403
    customer, cust_token = create_test_user(db_session, "cust", role=Role.CUSTOMER.value)
    cust_client = TestClient(app, cookies={"session_id": cust_token})
    
    res = cust_client.get("/api/employee/dashboard/summary")
    assert res.status_code == 403
    assert "Employee access required" in res.json()["detail"]
    
    res = cust_client.get("/api/employee/applications")
    assert res.status_code == 403

    # 2. Unverified employee (PENDING_VERIFICATION) attempts to access -> 403
    unverified, unverified_token = create_test_user(
        db_session, "unverified", role=Role.EMPLOYEE.value, status=OnboardingStatus.PENDING_VERIFICATION.value
    )
    unv_client = TestClient(app, cookies={"session_id": unverified_token})
    
    res = unv_client.get("/api/employee/dashboard/summary")
    assert res.status_code == 403
    assert "pending approval" in res.json()["detail"]

    # 3. Verified employee access -> 200
    emp, emp_token = create_test_user(db_session, "verified", role=Role.EMPLOYEE.value, status=OnboardingStatus.COMPLETED.value)
    emp_client = TestClient(app, cookies={"session_id": emp_token})
    
    res = emp_client.get("/api/employee/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    assert "recent_applications" in data
    assert data["employee_info"]["email"] == emp.email


def test_draft_exclusion_and_search_filter(db_session):
    emp, emp_token = create_test_user(db_session, "officer", role=Role.EMPLOYEE.value)
    cust, cust_token = create_test_user(db_session, "applicant", role=Role.CUSTOMER.value)
    emp_client = TestClient(app, cookies={"session_id": emp_token})
    
    # Create one draft and one submitted application for the customer
    draft_app = Application(
        user_id=cust.id,
        loan_type="Draft Education Loan",
        requested_amount=100000,
        tenure=12,
        purpose="Tuition fees",
        status=ApplicationStatus.DRAFT.value
    )
    submitted_app = Application(
        user_id=cust.id,
        loan_type="Submitted MSME Loan",
        requested_amount=850000,
        tenure=36,
        purpose="Machinery expansion",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(draft_app)
    db_session.add(submitted_app)
    db_session.commit()
    
    # Query all applications
    res = emp_client.get("/api/employee/applications")
    assert res.status_code == 200
    app_ids = [a["id"] for a in res.json()]
    assert str(submitted_app.id) in app_ids
    assert str(draft_app.id) not in app_ids  # DRAFT must be excluded!

    # Test filtering by status
    res_sub = emp_client.get("/api/employee/applications?status=SUBMITTED")
    assert res_sub.status_code == 200
    assert any(a["id"] == str(submitted_app.id) for a in res_sub.json())

    # Test search query
    res_search = emp_client.get("/api/employee/applications?search=Machinery")
    assert res_search.status_code == 200
    # Or search applicant
    res_search_name = emp_client.get(f"/api/employee/applications?search={cust.email}")
    assert res_search_name.status_code == 200
    assert any(a["id"] == str(submitted_app.id) for a in res_search_name.json())


def test_conflict_of_interest_enforcement(db_session):
    # If an employee applies for a loan, they CANNOT review their own application
    emp, emp_token = create_test_user(db_session, "self_reviewer", role=Role.EMPLOYEE.value)
    emp_other, emp_other_token = create_test_user(db_session, "independent_reviewer", role=Role.EMPLOYEE.value)
    
    emp_app = Application(
        user_id=emp.id,
        loan_type="Employee Personal Loan",
        requested_amount=300000,
        tenure=24,
        purpose="Home purchase",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(emp_app)
    db_session.commit()
    
    emp_client = TestClient(app, cookies={"session_id": emp_token})
    other_client = TestClient(app, cookies={"session_id": emp_other_token})
    
    # 1. Self review attempt -> 403 Forbidden
    res_self = emp_client.get(f"/api/employee/applications/{emp_app.id}")
    assert res_self.status_code == 403
    assert "Conflict of interest" in res_self.json()["detail"]
    
    # 2. Independent officer review -> 200 OK
    res_other = other_client.get(f"/api/employee/applications/{emp_app.id}")
    assert res_other.status_code == 200
    detail = res_other.json()
    assert detail["application"]["id"] == str(emp_app.id)
    assert detail["compliance"]["module"] == "M10_ADAPTIVE_RAG"
    assert detail["decision"]["can_decide"] is False


def test_truthful_assignments_and_documents(db_session):
    emp, emp_token = create_test_user(db_session, "desk_officer", role=Role.EMPLOYEE.value)
    cust, _ = create_test_user(db_session, "borrower", role=Role.CUSTOMER.value)
    
    app_record = Application(
        user_id=cust.id,
        loan_type="Vehicle Loan",
        requested_amount=500000,
        tenure=48,
        purpose="Commercial car",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app_record)
    db_session.commit()
    
    doc = Document(
        user_id=cust.id,
        application_id=app_record.id,
        document_type="PAN_CARD",
        file_url="https://storage.policypilot.gov.in/docs/pan_sample.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()
    
    emp_client = TestClient(app, cookies={"session_id": emp_token})
    
    # Assignments endpoint
    res_assign = emp_client.get("/api/employee/assignments")
    assert res_assign.status_code == 200
    assert res_assign.json()["assigned_applications"] == []
    assert "shared" in res_assign.json()["message"].lower() or "central" in res_assign.json()["message"].lower()

    # Documents repository
    res_docs = emp_client.get("/api/employee/documents")
    assert res_docs.status_code == 200
    doc_ids = [d["id"] for d in res_docs.json()]
    assert str(doc.id) in doc_ids


def test_employee_profile_and_organization(db_session):
    emp, emp_token = create_test_user(db_session, "details_officer", role=Role.EMPLOYEE.value)
    emp_client = TestClient(app, cookies={"session_id": emp_token})
    
    res_prof = emp_client.get("/api/employee/profile")
    assert res_prof.status_code == 200
    prof = res_prof.json()
    assert prof["role"] == "EMPLOYEE"
    assert "Credit & Underwriting" in prof["department"]
    
    res_org = emp_client.get("/api/employee/organization")
    assert res_org.status_code == 200
    org = res_org.json()
    assert "organization_name" in org
    assert "regulatory_body" in org
    assert "Sandbox" in org["regulatory_body"]

def test_admin_portal_rbac_separation(db_session):
    # 1. Customer -> 403 on Admin API
    cust, cust_token = create_test_user(db_session, "cust_admin_test", role=Role.CUSTOMER.value)
    cust_client = TestClient(app, cookies={"session_id": cust_token})
    res_cust = cust_client.get("/admin/employee-requests")
    assert res_cust.status_code == 403

    # 2. Employee -> 403 on Admin API
    emp, emp_token = create_test_user(db_session, "emp_admin_test", role=Role.EMPLOYEE.value)
    emp_client = TestClient(app, cookies={"session_id": emp_token})
    res_emp = emp_client.get("/admin/employee-requests")
    assert res_emp.status_code == 403

    # 3. Admin -> 200 on Admin API
    admin, admin_token = create_test_user(db_session, "admin_user_test", role=Role.ADMIN.value)
    admin_client = TestClient(app, cookies={"session_id": admin_token})
    res_admin = admin_client.get("/admin/employee-requests")
    assert res_admin.status_code == 200
