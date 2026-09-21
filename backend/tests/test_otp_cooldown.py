import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from app.main import app
from app.db.session import SessionLocal
from app.db.models import OTPRecord
from sqlalchemy.orm import Session
import os

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    # clean up previous records for the test phone number
    db.query(OTPRecord).filter(OTPRecord.phone_number == "+919999999999").delete()
    db.commit()
    yield db
    db.query(OTPRecord).filter(OTPRecord.phone_number == "+919999999999").delete()
    db.commit()
    db.close()

def test_otp_cooldown_flow(db_session: Session):
    phone = "9999999999"
    payload = {"phone_number": phone}
    
    # Ensure env vars are set
    os.environ["OTP_RESEND_COOLDOWN_SECONDS"] = "60"
    os.environ["OTP_EXPIRY_SECONDS"] = "300"
    
    # 1. First request should succeed
    with patch("app.services.sms.sms_service.send_otp") as mock_send:
        res = client.post("/auth/mobile/send-otp", json=payload)
        assert res.status_code == 200
        assert res.json() == {"message": "OTP sent successfully"}
    
    # Check DB record
    record = db_session.query(OTPRecord).filter_by(phone_number="+919999999999").order_by(OTPRecord.created_at.desc()).first()
    assert record is not None
    
    # Verify expiry is 5 minutes (300 seconds) ahead
    expiry_diff = (record.expires_at - record.created_at).total_seconds()
    assert 295 <= expiry_diff <= 305  # roughly 300 seconds
    
    # 2. Immediate second request should fail with 429 and retry_after_seconds ~ 60
    res2 = client.post("/auth/mobile/send-otp", json=payload)
    assert res2.status_code == 429
    data = res2.json()
    assert "retry_after_seconds" in data["detail"]
    assert 58 <= data["detail"]["retry_after_seconds"] <= 60
    assert res2.headers.get("retry-after") == str(data["detail"]["retry_after_seconds"])
    
    # 3. Simulate 10 seconds passing by modifying the created_at in the DB
    record.created_at = record.created_at - timedelta(seconds=10)
    db_session.commit()
    
    res3 = client.post("/auth/mobile/send-otp", json=payload)
    assert res3.status_code == 429
    data = res3.json()
    assert 48 <= data["detail"]["retry_after_seconds"] <= 50
    
    # 4. Simulate 65 seconds passing (meaning cooldown is over)
    record.created_at = record.created_at - timedelta(seconds=55) # total 65
    db_session.commit()
    
    with patch("app.services.sms.sms_service.send_otp") as mock_send:
        res4 = client.post("/auth/mobile/send-otp", json=payload)
        assert res4.status_code == 200
        assert res4.json() == {"message": "OTP sent successfully"}
        
    # Check that a new record was created
    new_record = db_session.query(OTPRecord).filter_by(phone_number="+919999999999").order_by(OTPRecord.created_at.desc()).first()
    assert new_record.id != record.id
    
    # 5. Simulate a stale/broken record from the future (e.g. clock drift)
    new_record.created_at = new_record.created_at + timedelta(minutes=65)
    db_session.commit()
    
    with patch("app.services.sms.sms_service.send_otp") as mock_send:
        res5 = client.post("/auth/mobile/send-otp", json=payload)
        assert res5.status_code == 200 # should succeed and bypass because it's from the future
        
