import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"))

import pytest
from fastapi.testclient import TestClient
from fastapi import APIRouter, Depends
from app.main import app
from app.db.session import SessionLocal
from app.db.models import User, OnboardingStatus, Role, Session as DBSession
from app.core.security import get_fully_onboarded_user, create_user_session
from sqlalchemy.orm import Session

# Add a dummy protected route for testing
test_router = APIRouter()
@test_router.get("/test/protected")
def dummy_protected_route(user: User = Depends(get_fully_onboarded_user)):
    return {"message": "Success", "user_id": user.id}

app.include_router(test_router)

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    # Cleanup test users
    db.query(DBSession).filter(DBSession.user_id.in_(
        db.query(User.id).filter(User.email.like("%@test.internal"))
    )).delete(synchronize_session=False)
    db.query(User).filter(User.email.like("%@test.internal")).delete(synchronize_session=False)
    db.commit()
    
    yield db
    
    db.query(DBSession).filter(DBSession.user_id.in_(
        db.query(User.id).filter(User.email.like("%@test.internal"))
    )).delete(synchronize_session=False)
    db.query(User).filter(User.email.like("%@test.internal")).delete(synchronize_session=False)
    db.commit()
    db.close()

def create_test_user(db: Session, status: str, role: str, email: str) -> str:
    user = User(
        email=email,
        full_name="Test User",
        authentication_provider="mobile",
        provider_subject_id=email,
        onboarding_status=status,
        requested_role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_user_session(db, user.id)
    return token

def test_new_user_blocked(db_session: Session):
    token = create_test_user(db_session, OnboardingStatus.NEW.value, Role.CUSTOMER.value, "new@test.internal")
    client.cookies.set("session_id", token)
    res = client.get("/test/protected")
    assert res.status_code == 403
    assert res.json()["detail"] == "Onboarding incomplete"

def test_pending_user_blocked(db_session: Session):
    token = create_test_user(db_session, OnboardingStatus.PENDING_VERIFICATION.value, Role.EMPLOYEE.value, "pending@test.internal")
    client.cookies.set("session_id", token)
    res = client.get("/test/protected")
    assert res.status_code == 403
    assert res.json()["detail"] == "Account pending verification"

def test_completed_user_allowed(db_session: Session):
    token = create_test_user(db_session, OnboardingStatus.COMPLETED.value, Role.CUSTOMER.value, "completed@test.internal")
    client.cookies.set("session_id", token)
    res = client.get("/test/protected")
    assert res.status_code == 200
    assert res.json()["message"] == "Success"
