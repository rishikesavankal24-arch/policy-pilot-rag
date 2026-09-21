import pytest
from fastapi.testclient import TestClient
import uuid
from datetime import datetime, timezone

from app.main import app
from app.db.models import User, Role, OnboardingStatus, EmployeeRequest, EmployeeRequestStatus
from app.core.security import create_user_session
from app.db.session import SessionLocal

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    # We should clean up created test users
    from app.db.models import Session as DBSession, EmployeeRequest, Application, Document, Notification, AdditionalInformationRequest, ApplicationAuditEvent
    test_users = db.query(User).filter(User.email.like("test_%@example.com")).all()
    for user in test_users:
        apps = db.query(Application).filter(Application.user_id == user.id).all()
        for app in apps:
            db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.application_id == app.id).delete()
            db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.application_id == app.id).delete()
        db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.requested_by == user.id).delete()
        db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.user_id == user.id).delete()
        db.query(Document).filter((Document.user_id == user.id) | (Document.reviewed_by == user.id)).delete()
        db.query(Application).filter(Application.user_id == user.id).delete()
        db.query(Notification).filter(Notification.user_id == user.id).delete()
        db.query(EmployeeRequest).filter((EmployeeRequest.user_id == user.id) | (EmployeeRequest.reviewed_by == user.id)).delete()
        db.query(DBSession).filter(DBSession.user_id == user.id).delete()
        db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()

def _create_and_login_user(db_session, role: str, status: OnboardingStatus = OnboardingStatus.COMPLETED) -> dict:
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        id=uuid.uuid4(),
        email=f"test_{role.lower()}_{unique_id}@example.com",
        authentication_provider="local",
        provider_subject_id=f"test_{role.lower()}_{unique_id}@example.com",
        onboarding_status=status.value,
        role=role,
        requested_role=role
    )
    db_session.add(user)
    db_session.commit()
    session_token = create_user_session(db_session, user.id)
    
    return {
        "user": user,
        "cookies": {"session_id": session_token}
    }

def _create_employee_request(db_session, user_id, status=EmployeeRequestStatus.PENDING.value):
    req = EmployeeRequest(
        user_id=user_id,
        organization="Test Org",
        status=status
    )
    db_session.add(req)
    db_session.commit()
    return req

def test_admin_rbac(db_session):
    # Customer cannot access Admin API
    customer = _create_and_login_user(db_session, Role.CUSTOMER.value)
    assert client.get("/admin/employee-requests", cookies=customer["cookies"]).status_code == 403

    # Pending employee cannot access Admin API
    pending_emp = _create_and_login_user(db_session, Role.CUSTOMER.value, OnboardingStatus.PENDING_VERIFICATION)
    assert client.get("/admin/employee-requests", cookies=pending_emp["cookies"]).status_code == 403

    # Verified employee cannot access Admin API
    verified_emp = _create_and_login_user(db_session, Role.EMPLOYEE.value)
    assert client.get("/admin/employee-requests", cookies=verified_emp["cookies"]).status_code == 403

    # Admin can list employee requests
    admin = _create_and_login_user(db_session, Role.ADMIN.value)
    res = client.get("/admin/employee-requests", cookies=admin["cookies"])
    assert res.status_code == 200

def test_admin_employee_actions(db_session):
    admin = _create_and_login_user(db_session, Role.ADMIN.value)
    customer = _create_and_login_user(db_session, Role.CUSTOMER.value)
    pending_emp = _create_and_login_user(db_session, Role.CUSTOMER.value, OnboardingStatus.PENDING_VERIFICATION)
    req = _create_employee_request(db_session, pending_emp["user"].id)

    req_id = str(req.id)

    # Admin can view request
    res = client.get(f"/admin/employee-requests/{req_id}", cookies=admin["cookies"])
    assert res.status_code == 200
    assert res.json()["status"] == "PENDING"

    # Non-admin cannot approve
    res = client.post(f"/admin/employee-requests/{req_id}/approve", cookies=customer["cookies"])
    assert res.status_code == 403

    # Employee cannot self-approve
    res = client.post(f"/admin/employee-requests/{req_id}/approve", cookies=pending_emp["cookies"])
    assert res.status_code == 403

    # Admin can request information
    res = client.post(f"/admin/employee-requests/{req_id}/request-information", json={"note": "Need ID"}, cookies=admin["cookies"])
    assert res.status_code == 200

    # Admin can reject request
    res = client.post(f"/admin/employee-requests/{req_id}/reject", json={"reason": "Incomplete"}, cookies=admin["cookies"])
    assert res.status_code == 200
    db_session.refresh(req)
    assert req.status == "REJECTED"
    assert req.rejection_reason == "Incomplete"
    assert req.reviewed_by == admin["user"].id

    # Reset to pending for approval
    req.status = "PENDING"
    db_session.commit()

    # Admin can approve request
    res = client.post(f"/admin/employee-requests/{req_id}/approve", cookies=admin["cookies"])
    assert res.status_code == 200
    db_session.refresh(req)
    assert req.status == "APPROVED"
    assert req.reviewed_by == admin["user"].id

    db_session.refresh(pending_emp["user"])
    assert pending_emp["user"].role == "EMPLOYEE"
    assert pending_emp["user"].onboarding_status == "COMPLETED"

def test_auto_approval(db_session, monkeypatch):
    import os
    
    # Enable auto approval for testing
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("EMPLOYEE_AUTO_APPROVE", "true")

    # Simulate sending a registration payload
    res = client.post("/auth/local/register", json={
        "email": "test_auto@example.com",
        "password": "password123",
        "role": "EMPLOYEE",
        "full_name": "Test Auto",
        "phone_number": "1234567890",
        "consent_accepted": True,
        "organization": "Test Org",
        "department": "Test Dept",
        "employee_id": "EMP123",
        "designation": "Manager",
        "work_email": "test@test.com"
    })
    
    assert res.status_code == 200
    
    # Check DB
    user = db_session.query(User).filter(User.email == "test_auto@example.com").first()
    assert user.role == "EMPLOYEE"
    assert user.onboarding_status == "COMPLETED"
    
    req = db_session.query(EmployeeRequest).filter(EmployeeRequest.user_id == user.id).first()
    assert req.status == "APPROVED"
    assert req.admin_note == "SYSTEM_DEVELOPMENT_AUTO_APPROVAL"
    
    # Clean up
    db_session.delete(req)
    db_session.delete(user)
    db_session.commit()

def test_auto_approval_disabled_in_prod(db_session, monkeypatch):
    import os
    
    # Disable auto approval for testing
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("EMPLOYEE_AUTO_APPROVE", "true") # Even if true, production should ignore it

    res = client.post("/auth/local/register", json={
        "email": "test_prod@example.com",
        "password": "password123",
        "role": "EMPLOYEE",
        "full_name": "Test Prod",
        "phone_number": "0987654321",
        "consent_accepted": True,
        "organization": "Test Org",
        "department": "Test Dept",
        "employee_id": "EMP123",
        "designation": "Manager",
        "work_email": "test@test.com"
    })
    
    assert res.status_code == 200
    
    # Check DB
    user = db_session.query(User).filter(User.email == "test_prod@example.com").first()
    assert user.role == "CUSTOMER" # pending employee
    assert user.onboarding_status == "PENDING_VERIFICATION"
    
    req = db_session.query(EmployeeRequest).filter(EmployeeRequest.user_id == user.id).first()
    assert req.status == "PENDING"
    assert req.admin_note is None
    
    # Clean up
    db_session.delete(req)
    db_session.delete(user)
    db_session.commit()

def test_admin_google_oauth_flow_and_authorization(db_session, monkeypatch):
    from unittest.mock import AsyncMock, patch

    # 1. Verify /auth/google/login preserves state=admin
    res = client.get("/auth/google/login?state=admin", follow_redirects=False)
    assert res.status_code in [302, 307]
    assert "state=admin" in res.headers["location"]

    # 2. Verify /auth/google/login without state behaves normally
    res_no_state = client.get("/auth/google/login", follow_redirects=False)
    assert res_no_state.status_code in [302, 307]
    assert "state=" not in res_no_state.headers["location"]

    # 3. Simulate Google callback with state=admin for a non-admin user
    # Mock httpx responses
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
        def json(self):
            return self._json

    async def mock_post(*args, **kwargs):
        return MockResponse(200, {"access_token": "mock_token"})

    # Case A: Non-admin Google user
    async def mock_get_non_admin(*args, **kwargs):
        return MockResponse(200, {
            "email": "test_google_customer@example.com",
            "id": "mock_google_id_customer",
            "name": "Customer User",
            "picture": "http://example.com/pic.jpg"
        })

    with patch("httpx.AsyncClient.post", side_effect=mock_post), \
         patch("httpx.AsyncClient.get", side_effect=mock_get_non_admin):
        res_cb = client.get("/auth/google/callback?code=mock_code&state=admin", follow_redirects=False)
        assert res_cb.status_code in [302, 307]
        assert "login?error=access_denied" in res_cb.headers["location"]
        assert "3001" in res_cb.headers["location"]
        assert "session_id" not in res_cb.cookies

    # Case B: Admin Google user
    admin_user = User(
        id=uuid.uuid4(),
        email="test_google_admin@example.com",
        authentication_provider="google",
        provider_subject_id="mock_google_id_admin",
        onboarding_status=OnboardingStatus.COMPLETED.value,
        role=Role.ADMIN.value,
        requested_role=Role.ADMIN.value
    )
    db_session.add(admin_user)
    db_session.commit()

    async def mock_get_admin(*args, **kwargs):
        return MockResponse(200, {
            "email": "test_google_admin@example.com",
            "id": "mock_google_id_admin",
            "name": "Admin User",
            "picture": "http://example.com/admin_pic.jpg"
        })

    with patch("httpx.AsyncClient.post", side_effect=mock_post), \
         patch("httpx.AsyncClient.get", side_effect=mock_get_admin):
        res_admin = client.get("/auth/google/callback?code=mock_code&state=admin", follow_redirects=False)
        assert res_admin.status_code in [302, 307]
        assert "3001/dashboard" in res_admin.headers["location"]
        assert "session_id" in res_admin.cookies

    # Clean up test admin
    db_session.delete(admin_user)
    db_session.commit()

def test_admin_employees_and_customers_management(db_session):
    customer = _create_and_login_user(db_session, Role.CUSTOMER.value)
    employee = _create_and_login_user(db_session, Role.EMPLOYEE.value)
    admin = _create_and_login_user(db_session, Role.ADMIN.value)

    # 1. Customer and Employee are strictly forbidden from /admin/employees & /admin/customers
    assert client.get("/admin/employees", cookies=customer["cookies"]).status_code == 403
    assert client.get("/admin/customers", cookies=customer["cookies"]).status_code == 403
    assert client.get("/admin/employees", cookies=employee["cookies"]).status_code == 403
    assert client.get("/admin/customers", cookies=employee["cookies"]).status_code == 403

    # 2. Admin can access /admin/employees
    res_emp = client.get("/admin/employees", cookies=admin["cookies"])
    assert res_emp.status_code == 200
    emp_list = res_emp.json()
    assert isinstance(emp_list, list)
    # Check that the employee we created is present
    emp_ids = [e["id"] for e in emp_list]
    assert str(employee["user"].id) in emp_ids

    # Verify no sensitive fields in response
    for e in emp_list:
        assert "hashed_password" not in e
        assert "reset_token" not in e
        assert "sessions" not in e

    # Detail view
    res_emp_detail = client.get(f"/admin/employees/{employee['user'].id}", cookies=admin["cookies"])
    assert res_emp_detail.status_code == 200
    assert res_emp_detail.json()["id"] == str(employee["user"].id)
    assert "hashed_password" not in res_emp_detail.json()

    # 3. Admin can access /admin/customers
    res_cust = client.get("/admin/customers", cookies=admin["cookies"])
    assert res_cust.status_code == 200
    cust_list = res_cust.json()
    assert isinstance(cust_list, list)
    cust_ids = [c["id"] for c in cust_list]
    assert str(customer["user"].id) in cust_ids

    # Verify no sensitive fields in response
    for c in cust_list:
        assert "hashed_password" not in c
        assert "reset_token" not in c
        assert "application_count" in c

    # Detail view
    res_cust_detail = client.get(f"/admin/customers/{customer['user'].id}", cookies=admin["cookies"])
    assert res_cust_detail.status_code == 200
    assert res_cust_detail.json()["id"] == str(customer["user"].id)
    assert "applications" in res_cust_detail.json()
    assert "hashed_password" not in res_cust_detail.json()
