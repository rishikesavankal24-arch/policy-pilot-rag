import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.models import User, Session as DBSession
from sqlalchemy.orm import Session

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    # Cleanup test users
    db.query(DBSession).filter(DBSession.user_id.in_(
        db.query(User.id).filter(User.email == "localtest@test.internal")
    )).delete(synchronize_session=False)
    db.query(User).filter(User.email == "localtest@test.internal").delete(synchronize_session=False)
    db.commit()
    
    yield db
    
    db.query(DBSession).filter(DBSession.user_id.in_(
        db.query(User.id).filter(User.email == "localtest@test.internal")
    )).delete(synchronize_session=False)
    db.query(User).filter(User.email == "localtest@test.internal").delete(synchronize_session=False)
    db.commit()
    db.close()

def test_local_registration_flow(db_session: Session):
    # 1. Register a new user
    res = client.post("/auth/local/register", json={
        "email": "localtest@test.internal",
        "password": "SecurePassword123!",
        "role": "CUSTOMER",
        "full_name": "Test User",
        "phone_number": "+919876543210",
        "language": "English",
        "consent_accepted": True
    })
    assert res.status_code == 200
    assert res.json()["message"] == "Account created/upgraded successfully"
    
    # Verify in DB
    user = db_session.query(User).filter(User.email == "localtest@test.internal").first()
    assert user is not None
    assert user.hashed_password is not None
    assert user.onboarding_status == "COMPLETED"
    
    # 2. Login with wrong password
    res_wrong = client.post("/auth/local/login", json={
        "identifier": "localtest@test.internal",
        "password": "WrongPassword!"
    })
    assert res_wrong.status_code == 401
    
    # 3. Login with correct password
    res_correct = client.post("/auth/local/login", json={
        "identifier": "localtest@test.internal",
        "password": "SecurePassword123!"
    })
    assert res_correct.status_code == 200
    assert res_correct.json()["redirect"] == "/dashboard"
    
    # Check if session_id cookie is present
    session_id = res_correct.cookies.get("session_id")
    assert session_id is not None
    
    # 4. Authenticated /auth/me works
    res_me = client.get("/auth/me")
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "localtest@test.internal"
    assert res_me.json()["onboarding_status"] == "COMPLETED"
