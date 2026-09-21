import pytest
from fastapi.testclient import TestClient
from fastapi import APIRouter, Depends
from app.main import app
from app.api.deps import require_permissions, check_resource_ownership_or_employee, check_employee_review_not_owner, get_current_active_user
from app.db.models import User, Role, OnboardingStatus
from app.core.security import create_user_session
import uuid
from app.db.session import SessionLocal

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

# Dummy router for RBAC tests
rbac_router = APIRouter(prefix="/test-rbac")

@rbac_router.get("/customer-only")
def customer_only(user: User = Depends(require_permissions(["PROFILE_READ_SELF"]))):
    return {"status": "ok"}

@rbac_router.get("/employee-only")
def employee_only(user: User = Depends(require_permissions(["EMPLOYEE_WORKSPACE_ACCESS"]))):
    return {"status": "ok"}

@rbac_router.get("/admin-only")
def admin_only(user: User = Depends(require_permissions(["ADMIN_USER_MANAGEMENT"]))):
    return {"status": "ok"}

@rbac_router.get("/resource/{resource_user_id}")
def resource_access(resource_user_id: str, current_user: User = Depends(get_current_active_user)):
    check_resource_ownership_or_employee(current_user, resource_user_id)
    return {"status": "ok"}

@rbac_router.post("/resource/{resource_user_id}/approve")
def resource_review(resource_user_id: str, current_user: User = Depends(get_current_active_user)):
    check_employee_review_not_owner(current_user, resource_user_id)
    return {"status": "ok"}

@rbac_router.get("/unsupported-permission")
def unsupported(user: User = Depends(require_permissions(["NON_EXISTENT_PERMISSION"]))):
    return {"status": "ok"}

app.include_router(rbac_router)

client = TestClient(app)

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

def test_rbac_unauthenticated():
    assert client.get("/test-rbac/customer-only").status_code == 401

def test_rbac_customer(db_session):
    data = _create_and_login_user(db_session, Role.CUSTOMER.value)
    cookies = data["cookies"]
    
    assert client.get("/test-rbac/customer-only", cookies=cookies).status_code == 200
    assert client.get("/test-rbac/employee-only", cookies=cookies).status_code == 403
    assert client.get("/test-rbac/admin-only", cookies=cookies).status_code == 403

def test_rbac_pending_employee(db_session):
    # Pending employee has role CUSTOMER, requested_role EMPLOYEE, status PENDING_VERIFICATION
    # For now, their role is actually CUSTOMER in the DB until verified.
    data = _create_and_login_user(db_session, Role.CUSTOMER.value, OnboardingStatus.PENDING_VERIFICATION)
    cookies = data["cookies"]
    
    assert client.get("/test-rbac/customer-only", cookies=cookies).status_code == 200
    assert client.get("/test-rbac/employee-only", cookies=cookies).status_code == 403
    assert client.get("/test-rbac/admin-only", cookies=cookies).status_code == 403

def test_rbac_verified_employee(db_session):
    data = _create_and_login_user(db_session, Role.EMPLOYEE.value)
    cookies = data["cookies"]
    
    assert client.get("/test-rbac/customer-only", cookies=cookies).status_code == 200
    assert client.get("/test-rbac/employee-only", cookies=cookies).status_code == 200
    assert client.get("/test-rbac/admin-only", cookies=cookies).status_code == 403

def test_rbac_admin(db_session):
    data = _create_and_login_user(db_session, Role.ADMIN.value)
    cookies = data["cookies"]
    
    assert client.get("/test-rbac/customer-only", cookies=cookies).status_code == 403
    assert client.get("/test-rbac/employee-only", cookies=cookies).status_code == 403
    assert client.get("/test-rbac/admin-only", cookies=cookies).status_code == 200

def test_rbac_unsupported_permission(db_session):
    data = _create_and_login_user(db_session, Role.ADMIN.value)
    assert client.get("/test-rbac/unsupported-permission", cookies=data["cookies"]).status_code == 403

def test_rbac_resource_ownership_and_coi(db_session):
    customer = _create_and_login_user(db_session, Role.CUSTOMER.value)
    other_customer = _create_and_login_user(db_session, Role.CUSTOMER.value)
    employee = _create_and_login_user(db_session, Role.EMPLOYEE.value)
    
    c_id = str(customer["user"].id)
    oc_id = str(other_customer["user"].id)
    e_id = str(employee["user"].id)
    
    # Ownership isolation
    assert client.get(f"/test-rbac/resource/{c_id}", cookies=customer["cookies"]).status_code == 200
    assert client.get(f"/test-rbac/resource/{oc_id}", cookies=customer["cookies"]).status_code == 403
    assert client.get(f"/test-rbac/resource/{c_id}", cookies=employee["cookies"]).status_code == 200
    assert client.get(f"/test-rbac/resource/{e_id}", cookies=employee["cookies"]).status_code == 200
    
    # Self-review protection (Conflict of Interest)
    assert client.post(f"/test-rbac/resource/{c_id}/approve", cookies=employee["cookies"]).status_code == 200
    assert client.post(f"/test-rbac/resource/{e_id}/approve", cookies=employee["cookies"]).status_code == 403
    assert client.post(f"/test-rbac/resource/{c_id}/approve", cookies=customer["cookies"]).status_code == 403
