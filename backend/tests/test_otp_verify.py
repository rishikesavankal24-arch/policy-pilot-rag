import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from app.main import app
from app.db.session import SessionLocal
from app.db.models import OTPRecord, User, Session as DBSession, OnboardingStatus
from sqlalchemy.orm import Session

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    phone = "+918888888888"
    db.query(OTPRecord).filter(OTPRecord.phone_number == phone).delete()
    user = db.query(User).filter(User.phone_number == phone).first()
    if user:
        db.query(DBSession).filter(DBSession.user_id == user.id).delete()
        db.query(User).filter(User.id == user.id).delete()
    db.commit()
    yield db
    db.query(OTPRecord).filter(OTPRecord.phone_number == phone).delete()
    user = db.query(User).filter(User.phone_number == phone).first()
    if user:
        db.query(DBSession).filter(DBSession.user_id == user.id).delete()
        db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()

def test_otp_verify_flow(db_session: Session):
    phone = "8888888888"
    norm_phone = "+918888888888"
    
    with patch("app.services.sms.sms_service.send_otp") as mock_send:
        res = client.post("/auth/mobile/send-otp", json={"phone_number": phone})
        assert res.status_code == 200
        
    record = db_session.query(OTPRecord).filter_by(phone_number=norm_phone).order_by(OTPRecord.created_at.desc()).first()
    assert record is not None
    
    from app.core.security import hash_otp
    test_otp = "123456"
    record.otp_hash = hash_otp(test_otp)
    db_session.commit()
    
    # 7. Wrong OTP
    res_wrong = client.post("/auth/mobile/verify-otp", json={"phone_number": phone, "otp": "000000"})
    assert res_wrong.status_code == 400
    assert res_wrong.json()["detail"] == "Incorrect OTP"
    db_session.refresh(record)
    assert record.attempts == 1
    
    # 1, 2, 3, 4, 5. Correct OTP
    res_correct = client.post("/auth/mobile/verify-otp", json={"phone_number": phone, "otp": test_otp})
    assert res_correct.status_code == 200
    assert res_correct.json()["redirect"] == "/register"
    
    # Check if session_id cookie is present
    session_id = res_correct.cookies.get("session_id")
    assert session_id is not None
    
    # 4. authenticated /auth/me works
    res_me = client.get("/auth/me")
    assert res_me.status_code == 200
    user_data = res_me.json()
    assert user_data["phone_number"] == norm_phone
    assert user_data["onboarding_status"] == "NEW"
    
    # 9. Consumed OTP -> rejected
    res_consumed = client.post("/auth/mobile/verify-otp", json={"phone_number": phone, "otp": test_otp})
    assert res_consumed.status_code == 400
    assert res_consumed.json()["detail"] == "No active OTP found"
    
def test_otp_verify_expired(db_session: Session):
    phone = "8888888888"
    norm_phone = "+918888888888"
    
    with patch("app.services.sms.sms_service.send_otp") as mock_send:
        client.post("/auth/mobile/send-otp", json={"phone_number": phone})
        
    record = db_session.query(OTPRecord).filter_by(phone_number=norm_phone).order_by(OTPRecord.created_at.desc()).first()
    from app.core.security import hash_otp
    test_otp = "123456"
    record.otp_hash = hash_otp(test_otp)
    record.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()
    
    # 8. Expired OTP
    res_expired = client.post("/auth/mobile/verify-otp", json={"phone_number": phone, "otp": test_otp})
    if res_expired.status_code != 400:
        print("EXPIRED RESPONSE:", res_expired.json())
    assert res_expired.status_code == 400
    assert res_expired.json()["detail"] == "OTP expired"

def test_otp_verify_completed_user(db_session: Session):
    phone = "8888888888"
    norm_phone = "+918888888888"
    
    user = User(
        email=f"{norm_phone.strip('+')}@mobile.policypilot.internal",
        full_name="Mobile User",
        authentication_provider="mobile",
        provider_subject_id=norm_phone,
        phone_number=norm_phone,
        onboarding_status=OnboardingStatus.COMPLETED.value
    )
    db_session.add(user)
    db_session.commit()
    
    with patch("app.services.sms.sms_service.send_otp") as mock_send:
        client.post("/auth/mobile/send-otp", json={"phone_number": phone})
        
    record = db_session.query(OTPRecord).filter_by(phone_number=norm_phone).order_by(OTPRecord.created_at.desc()).first()
    from app.core.security import hash_otp
    test_otp = "123456"
    record.otp_hash = hash_otp(test_otp)
    db_session.commit()
    
    res_correct = client.post("/auth/mobile/verify-otp", json={"phone_number": phone, "otp": test_otp})
    assert res_correct.status_code == 200
    # 6. Completed user goes to dashboard
    assert res_correct.json()["redirect"] == "/dashboard"

def test_otp_verify_duplicate_mobile_prevention(db_session: Session):
    phone = "8888888888"
    norm_phone = "+918888888888"
    
    # Create an existing user who registered via Google but added their phone number during onboarding
    user = User(
        email="google.user@example.com",
        full_name="Google User",
        authentication_provider="google",
        provider_subject_id="google_id_12345",
        phone_number=norm_phone,
        onboarding_status=OnboardingStatus.COMPLETED.value
    )
    db_session.add(user)
    db_session.commit()
    user_id = user.id
    
    with patch("app.services.sms.sms_service.send_otp") as mock_send:
        client.post("/auth/mobile/send-otp", json={"phone_number": phone})
        
    record = db_session.query(OTPRecord).filter_by(phone_number=norm_phone).order_by(OTPRecord.created_at.desc()).first()
    from app.core.security import hash_otp
    test_otp = "123456"
    record.otp_hash = hash_otp(test_otp)
    db_session.commit()
    
    res_correct = client.post("/auth/mobile/verify-otp", json={"phone_number": phone, "otp": test_otp})
    assert res_correct.status_code == 200
    assert res_correct.json()["redirect"] == "/dashboard"
    
    # Verify no duplicate user was created
    users_with_phone = db_session.query(User).filter(User.phone_number == norm_phone).all()
    assert len(users_with_phone) == 1
    assert users_with_phone[0].id == user_id
    assert users_with_phone[0].authentication_provider == "google" # Provider wasn't overridden

