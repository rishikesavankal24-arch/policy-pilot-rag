import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import (
    User, Role, OnboardingStatus, EmployeeRequest, EmployeeRequestStatus,
    Session as DBSession
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
        test_users = db.query(User).filter(User.email.like("test_iso_%@example.com")).all()
        for user in test_users:
            db.query(EmployeeRequest).filter(EmployeeRequest.user_id == user.id).delete()
            db.query(DBSession).filter(DBSession.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()

def create_user_with_session(db, prefix: str, role: str):
    uid = uuid.uuid4()
    email = f"test_iso_{prefix}_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name=f"User {prefix.capitalize()}",
        role=role,
        requested_role=role,
        onboarding_status=OnboardingStatus.COMPLETED.value,
        authentication_provider="local",
        provider_subject_id=email
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if role == Role.EMPLOYEE.value:
        req = EmployeeRequest(
            user_id=user.id,
            organization="PolicyPilot Credit Desk",
            department="Operations",
            employee_id=f"EMP-{uid.hex[:4].upper()}",
            designation="Credit Specialist",
            work_email=f"work_{email}",
            status=EmployeeRequestStatus.APPROVED.value
        )
        db.add(req)
        db.commit()

    token = create_user_session(db, user.id)
    return user, token

def test_multi_source_token_resolution(db_session):
    """Test that get_current_user resolves session tokens from Bearer header, X-Session-ID, query param, and cookie."""
    client = TestClient(app)
    user, token = create_user_with_session(db_session, "multi", Role.CUSTOMER.value)

    # 1. Bearer Header
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["id"] == str(user.id)
    assert res.json()["session_token"] == token

    # 2. X-Session-ID Header
    res = client.get("/auth/me", headers={"X-Session-ID": token})
    assert res.status_code == 200
    assert res.json()["id"] == str(user.id)
    assert res.json()["session_token"] == token

    # 3. Query Param
    res = client.get(f"/auth/me?session_token={token}")
    assert res.status_code == 200
    assert res.json()["id"] == str(user.id)
    assert res.json()["session_token"] == token

    # 4. Cookie
    res = client.get("/auth/me", cookies={"session_id": token})
    assert res.status_code == 200
    assert res.json()["id"] == str(user.id)
    assert res.json()["session_token"] == token

def test_same_browser_cookie_collision_override(db_session):
    """
    Test the critical bug scenario:
    Customer and Employee exist in different tabs of the same browser.
    One cookie is active on the origin, but each tab sends its own Bearer token.
    Header MUST take precedence over the conflicting cookie.
    """
    client = TestClient(app)
    cust_user, cust_token = create_user_with_session(db_session, "cust", Role.CUSTOMER.value)
    emp_user, emp_token = create_user_with_session(db_session, "emp", Role.EMPLOYEE.value)

    # Scenario A: Browser cookie is set to CUSTOMER token (e.g. customer just logged in / refreshed)
    # Employee tab requests /api/employee/applications with Authorization: Bearer <emp_token>
    # It MUST authenticate as Employee and succeed (200), NOT fail with 403 Forbidden!
    client.cookies.set("session_id", cust_token)
    res_emp = client.get(
        "/api/employee/applications",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert res_emp.status_code == 200, f"Expected 200 for employee, got {res_emp.status_code}: {res_emp.text}"

    # Scenario B: Browser cookie is set to EMPLOYEE token (e.g. employee just logged in / refreshed)
    # Customer tab requests /auth/me with Authorization: Bearer <cust_token>
    # It MUST authenticate as Customer
    client.cookies.set("session_id", emp_token)
    res_cust = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert res_cust.status_code == 200
    assert res_cust.json()["role"] == Role.CUSTOMER.value
    assert res_cust.json()["id"] == str(cust_user.id)

    # Customer trying to access employee endpoint with customer token must be blocked (403)
    res_cust_blocked = client.get(
        "/api/employee/applications",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert res_cust_blocked.status_code == 403

def test_selective_logout(db_session):
    """
    Test that logging out in one tab (e.g. Employee) only deletes that tab's session
    and leaves the other tab's session (e.g. Customer) active in the database.
    """
    client = TestClient(app)
    cust_user, cust_token = create_user_with_session(db_session, "custlog", Role.CUSTOMER.value)
    emp_user, emp_token = create_user_with_session(db_session, "emplog", Role.EMPLOYEE.value)

    # Employee logs out via Authorization header
    res_logout = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {emp_token}"},
        cookies={"session_id": emp_token}
    )
    assert res_logout.status_code == 200

    # Employee token is now invalid
    res_emp = client.get("/auth/me", headers={"Authorization": f"Bearer {emp_token}"})
    assert res_emp.status_code == 401

    # Customer token MUST STILL BE VALID and operational
    res_cust = client.get("/auth/me", headers={"Authorization": f"Bearer {cust_token}"})
    assert res_cust.status_code == 200
    assert res_cust.json()["id"] == str(cust_user.id)

def test_portal_scope_isolation(db_session):
    """
    Test X-Portal-Scope header enforcement:
    A request tagged with X-Portal-Scope: employee MUST reject a Customer session with 401,
    preventing an unauthenticated employee tab from silently adopting a Customer cookie.
    A request tagged with X-Portal-Scope: customer MUST reject an Employee session with 401.
    """
    client = TestClient(app)
    cust_user, cust_token = create_user_with_session(db_session, "custscope", Role.CUSTOMER.value)
    emp_user, emp_token = create_user_with_session(db_session, "empscope", Role.EMPLOYEE.value)

    # 1. Employee portal scope with Customer session (cookie or header) must be rejected with 401
    res_rejected = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {cust_token}", "X-Portal-Scope": "employee"}
    )
    assert res_rejected.status_code == 401
    assert "Employee session required" in res_rejected.json()["detail"]

    # Also with cookie:
    client.cookies.set("session_id", cust_token)
    res_cookie_rejected = client.get(
        "/auth/me",
        headers={"X-Portal-Scope": "employee"}
    )
    assert res_cookie_rejected.status_code == 401
    assert "Employee session required" in res_cookie_rejected.json()["detail"]

    # 2. Employee portal scope with Employee session must succeed
    res_emp_allowed = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {emp_token}", "X-Portal-Scope": "employee"}
    )
    assert res_emp_allowed.status_code == 200
    assert res_emp_allowed.json()["role"] == Role.EMPLOYEE.value

    # 3. Customer portal scope with Employee session must be rejected with 401
    res_emp_rejected_on_cust = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {emp_token}", "X-Portal-Scope": "customer"}
    )
    assert res_emp_rejected_on_cust.status_code == 401
    assert "Customer session required" in res_emp_rejected_on_cust.json()["detail"]

    # 4. Customer portal scope with Customer session must succeed
    res_cust_allowed = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {cust_token}", "X-Portal-Scope": "customer"}
    )
    assert res_cust_allowed.status_code == 200
    assert res_cust_allowed.json()["role"] == Role.CUSTOMER.value
