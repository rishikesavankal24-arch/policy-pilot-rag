import requests
import json
import uuid
import os

BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def print_section(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")

def run_tests():
    session = requests.Session()
    
    # 1. Login to get a session cookie
    print_section("AUTHENTICATION REGRESSION & LOGIN")
    email_a = f"customer_a_{uuid.uuid4().hex[:6]}@example.com"
    email_b = f"customer_b_{uuid.uuid4().hex[:6]}@example.com"
    
    login_data = {
        "identifier": email_a,
        "password": "password123"
    }
    # Register customer first if not exists
    res = session.post(f"{BASE_URL}/auth/local/register", json={
        "email": email_a,
        "password": "password123",
        "full_name": "Test Customer",
        "phone_number": "1234567890",
        "consent_accepted": True,
        "role": "CUSTOMER"
    })
    print(f"Register status: {res.status_code}")
    print(res.text)
    
    res = session.post(f"{BASE_URL}/auth/local/login", json=login_data)
    print(f"Login status: {res.status_code}")
    print(res.text)
    assert res.status_code == 200
    
    res = session.get(f"{BASE_URL}/auth/me")
    print(f"/auth/me status: {res.status_code}")
    print(res.json())
    assert res.status_code == 200
    
    # 2. Test Customer Dashboard API
    print_section("CUSTOMER DASHBOARD DATA")
    res = session.get(f"{BASE_URL}/api/customer/dashboard/summary")
    print(f"Dashboard summary status: {res.status_code}")
    print(res.json())
    assert res.status_code == 200

    # 3. Profile Update
    print_section("PROFILE PERSISTENCE")
    profile_update = {
        "full_name": "Test Customer User",
        "phone_number": "9876543210",
        "address": "123 Test St",
        "city": "Test City",
        "state": "Test State",
        "pincode": "123456"
    }
    res = session.patch(f"{BASE_URL}/api/customer/profile", json=profile_update)
    print(f"Profile update status: {res.status_code}")
    print(res.text)
    assert res.status_code == 200

    res = session.get(f"{BASE_URL}/api/customer/profile")
    print(f"Profile fetch status: {res.status_code}")
    data = res.json()
    print(data)
    assert data["phone_number"] == "9876543210"

    # 4. Application Creation
    print_section("APPLICATION DRAFT & SUBMISSION")
    app_data = {
        "loan_type": "Personal Loan",
        "requested_amount": 500000,
        "tenure": 24,
        "purpose": "Test application flow",
    }
    res = session.post(f"{BASE_URL}/api/applications/", json=app_data)
    print(f"Create Application status: {res.status_code}")
    assert res.status_code == 200
    app_id = res.json()["id"]
    print(f"Created Application ID: {app_id}")
    
    res = session.get(f"{BASE_URL}/api/applications/{app_id}")
    assert res.status_code == 200
    print(f"Application Draft Status: {res.json()['application']['status']}")

    res = session.post(f"{BASE_URL}/api/applications/{app_id}/submit")
    print(f"Submit Application status: {res.status_code}")
    assert res.status_code == 200
    
    res = session.get(f"{BASE_URL}/api/applications/{app_id}")
    assert res.status_code == 200
    print(f"Application New Status: {res.json()['application']['status']}")

    # 5. Document Upload
    print_section("DOCUMENT UPLOAD")
    files = {
        'document_type': (None, 'Identity Proof'),
        'application_id': (None, app_id),
        'file': ('test.pdf', b'fake pdf content', 'application/pdf')
    }
    res = session.post(f"{BASE_URL}/api/documents/", files=files)
    print(f"Upload Document status: {res.status_code}")
    assert res.status_code == 200
    doc_id = res.json()["id"]
    print(f"Created Document ID: {doc_id}")
    
    res = session.get(f"{BASE_URL}/api/documents/")
    print(f"Fetch Documents status: {res.status_code}")
    docs = res.json()
    assert len(docs) > 0
    print(docs)

    # 6. Notifications
    print_section("NOTIFICATIONS")
    res = session.get(f"{BASE_URL}/api/notifications/")
    print(f"Fetch Notifications status: {res.status_code}")
    print(res.json())

    # 7. Security / Ownership check
    print_section("OWNERSHIP / SECURITY CHECK")
    # Register/Login as Customer B
    session_b = requests.Session()
    session_b.post(f"{BASE_URL}/auth/local/register", json={
        "email": email_b,
        "password": "password123",
        "full_name": "Test Customer B",
        "phone_number": "0987654321",
        "consent_accepted": True,
        "role": "CUSTOMER"
    })
    session_b.post(f"{BASE_URL}/auth/local/login", json={
        "identifier": email_b,
        "password": "password123"
    })
    
    res = session_b.get(f"{BASE_URL}/api/applications/{app_id}")
    print(f"Customer B trying to read Customer A's application. Status: {res.status_code}")
    assert res.status_code == 404
    
    res = session_b.delete(f"{BASE_URL}/api/documents/{doc_id}")
    print(f"Customer B trying to delete Customer A's document. Status: {res.status_code}")
    assert res.status_code == 404

    print_section("TESTS COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    run_tests()
