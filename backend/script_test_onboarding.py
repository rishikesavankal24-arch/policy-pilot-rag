import urllib.request
import json
import uuid
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import User, Session, EmployeeRequest, OnboardingStatus, Base

# 1. Setup DB
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/policypilot"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# 2. Create Dummy User and Session
user_id = str(uuid.uuid4())
session_id = str(uuid.uuid4())

dummy_user = User(
    id=user_id,
    email="test_employee@example.com",
    full_name="Test Employee",
    provider_subject_id="google_456",
    onboarding_status="ONBOARDING_REQUIRED"
)
db.add(dummy_user)

dummy_session = Session(
    id=session_id,
    user_id=user_id,
    session_token=session_id,
    expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
)
db.add(dummy_session)
db.commit()

# 3. Test Employee Onboarding via API
payload = json.dumps({
    "phone_number": "9876543210",
    "language": "hi",
    "consent_accepted": True,
    "organization": "Test Corp",
    "department": "Compliance",
    "employee_id": "EMP-1234",
    "designation": "Analyst",
    "work_email": "test@testcorp.com",
    "reason": "Need access"
}).encode("utf-8")

req = urllib.request.Request("http://127.0.0.1:8000/onboarding/employee", data=payload, method="POST")
req.add_header("Content-Type", "application/json")
req.add_header("Cookie", f"session_id={session_id}")

print("Testing Employee Onboarding...")
try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.status}")
        print(f"Response: {response.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Response: {e.read().decode('utf-8')}")

# 4. Verify DB
db.refresh(dummy_user)
print(f"User Onboarding Status: {dummy_user.onboarding_status}")
print(f"User Role: {dummy_user.requested_role}")

emp_req = db.query(EmployeeRequest).filter(EmployeeRequest.user_id == user_id).first()
if emp_req:
    print(f"EmployeeRequest Status: {emp_req.status}")
    print(f"EmployeeRequest Org: {emp_req.organization}")
else:
    print("EmployeeRequest NOT FOUND!")

# 5. Clean up
if emp_req:
    db.delete(emp_req)
db.delete(dummy_session)
db.delete(dummy_user)
db.commit()
