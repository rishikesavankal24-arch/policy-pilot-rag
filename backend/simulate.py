import httpx
import os
import sys

from app.db.session import SessionLocal
from app.db.models import User, OTPRecord
from app.core.security import hash_otp

db = SessionLocal()

print("MOBILE USERS:")
for u in db.query(User).filter(User.authentication_provider=='mobile').all():
    print(u.id, u.email, u.phone_number, u.onboarding_status, u.requested_role)

client = httpx.Client(base_url="http://127.0.0.1:8000")
phone = "+919999999889" # Completely new phone number
print("Sending OTP to", phone)
res = client.post("/auth/mobile/send-otp", json={"phone_number": phone})
print(res.status_code, res.text)

# Simulate OTP verify
known_otp = "123456"
hashed = hash_otp(known_otp)

record = db.query(OTPRecord).filter(OTPRecord.phone_number==phone).order_by(OTPRecord.created_at.desc()).first()
record.otp_hash = hashed
db.commit()

print("Verifying OTP")
res2 = client.post("/auth/mobile/verify-otp", json={"phone_number": phone, "otp": known_otp})
print(res2.status_code, res2.text)

cookie = res2.cookies.get("session_id")
print("Session cookie:", cookie)

res3 = client.get("/auth/me", cookies={"session_id": cookie})
print("Me API:", res3.status_code, res3.json())

user_in_db = db.query(User).filter(User.phone_number == phone).first()
print("USER IN DB AFTER OTP:", user_in_db.onboarding_status, user_in_db.requested_role)
