import io
import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.models import (
    User, Role, OnboardingStatus, Application, ApplicationStatus,
    Document, DocumentStatus, AdditionalInformationRequest,
    InformationRequestStatus, Session as SessionModel
)

client = TestClient(app)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def create_test_user(db, email, role):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name=f"Test {role}",
            role=role,
            provider_subject_id=email,
            onboarding_status=OnboardingStatus.COMPLETED.value,
            authentication_provider="local"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def create_session_for_user(db, user_id):
    token = f"test_session_{uuid.uuid4()}"
    sess = SessionModel(
        user_id=user_id,
        session_token=token,
        expires_at=datetime.now(timezone.utc).replace(year=2030)
    )
    db.add(sess)
    db.commit()
    return token

def test_full_employee_review_and_customer_sync(db):
    cust = create_test_user(db, f"cust_sync_{uuid.uuid4().hex[:6]}@example.com", Role.CUSTOMER.value)
    emp = create_test_user(db, f"emp_sync_{uuid.uuid4().hex[:6]}@example.com", Role.EMPLOYEE.value)
    other_cust = create_test_user(db, f"other_cust_{uuid.uuid4().hex[:6]}@example.com", Role.CUSTOMER.value)

    cust_token = create_session_for_user(db, cust.id)
    emp_token = create_session_for_user(db, emp.id)
    other_cust_token = create_session_for_user(db, other_cust.id)

    cust_headers = {"Cookie": f"session_id={cust_token}"}
    emp_headers = {"Cookie": f"session_id={emp_token}"}
    other_cust_headers = {"Cookie": f"session_id={other_cust_token}"}

    # 1. Customer creates and submits application
    loan_app = Application(
        user_id=cust.id,
        loan_type="Personal Loan",
        requested_amount=100000,
        tenure=12,
        purpose="Medical",
        status=ApplicationStatus.SUBMITTED.value
    )
    db.add(loan_app)
    db.commit()
    db.refresh(loan_app)

    # 2. Customer uploads document
    doc = Document(
        application_id=loan_app.id,
        user_id=cust.id,
        document_type="IDENTITY_PROOF",
        file_url="uploads/test.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 3. Employee accepts document
    res_accept = client.post(
        f"/api/employee/documents/{doc.id}/review",
        headers=emp_headers,
        json={"status": "ACCEPTED", "reason": "Verified and valid"}
    )
    assert res_accept.status_code == 200, res_accept.text

    # 4. Customer API returns ACCEPTED after refresh
    res_cust_get = client.get(
        f"/api/applications/{loan_app.id}",
        headers=cust_headers
    )
    assert res_cust_get.status_code == 200
    cust_detail = res_cust_get.json()
    assert len(cust_detail["documents"]) == 1
    assert cust_detail["documents"][0]["status"] == "ACCEPTED"
    assert cust_detail["documents"][0]["review_notes"] == "Verified and valid"

    # 5. Employee requires re-upload
    res_reupload = client.post(
        f"/api/employee/documents/{doc.id}/review",
        headers=emp_headers,
        json={"status": "REQUIRES_REUPLOAD", "reason": "Blurred photo, please provide clearer copy"}
    )
    assert res_reupload.status_code == 200

    # 6. Customer API returns REQUIRES_REUPLOAD with review notes visible to customer
    res_cust_get2 = client.get(
        f"/api/applications/{loan_app.id}",
        headers=cust_headers
    )
    assert res_cust_get2.status_code == 200
    cust_detail2 = res_cust_get2.json()
    assert cust_detail2["documents"][0]["status"] == "REQUIRES_REUPLOAD"
    assert cust_detail2["documents"][0]["review_notes"] == "Blurred photo, please provide clearer copy"

    # 7. Employee creates additional information request
    res_req_info = client.post(
        f"/api/employee/applications/{loan_app.id}/information-requests",
        headers=emp_headers,
        json={"title": "Need Bank Statement", "description": "Last 6 months salary account statement", "requested_document_type": "BANK_STATEMENT"}
    )
    assert res_req_info.status_code == 200
    created_info_req = res_req_info.json()
    req_id = created_info_req["id"]

    # 8. Customer API returns ADDITIONAL_INFO_REQUIRED and displays the open request
    res_cust_get3 = client.get(
        f"/api/applications/{loan_app.id}",
        headers=cust_headers
    )
    assert res_cust_get3.status_code == 200
    cust_detail3 = res_cust_get3.json()
    assert cust_detail3["application"]["status"] == "ADDITIONAL_INFO_REQUIRED"
    assert len(cust_detail3["information_requests"]) == 1
    assert cust_detail3["information_requests"][0]["status"] == "OPEN"
    assert cust_detail3["information_requests"][0]["title"] == "Need Bank Statement"

    # 9. Customer response changes server state (uploads requested document)
    from tests.pdf_fixtures import make_test_pdf_bytes
    pdf_content = make_test_pdf_bytes(1)
    res_respond = client.post(
        f"/api/customer/applications/{loan_app.id}/information-requests/{req_id}/respond",
        headers=cust_headers,
        data={"notes": "Uploaded HDFC salary statement for last 6 months"},
        files={"file": ("salary_statement.pdf", io.BytesIO(pdf_content), "application/pdf")}
    )
    assert res_respond.status_code == 200, res_respond.text
    respond_data = res_respond.json()
    assert respond_data["request"]["status"] == "RESPONDED"
    assert respond_data["application_status"] == "UNDER_REVIEW"

    # Customer detail immediately reflects RESPONDED and application returns to UNDER_REVIEW
    res_cust_after_respond = client.get(
        f"/api/applications/{loan_app.id}",
        headers=cust_headers
    )
    assert res_cust_after_respond.status_code == 200
    cust_detail_after = res_cust_after_respond.json()
    assert cust_detail_after["application"]["status"] == "UNDER_REVIEW"
    assert cust_detail_after["information_requests"][0]["status"] == "RESPONDED"
    assert cust_detail_after["information_requests"][0]["response_notes"] == "Uploaded HDFC salary statement for last 6 months"

    # 10. Employee sees customer response in employee dossier
    res_emp_dossier = client.get(
        f"/api/employee/applications/{loan_app.id}",
        headers=emp_headers
    )
    assert res_emp_dossier.status_code == 200
    emp_dossier = res_emp_dossier.json()
    assert emp_dossier["application"]["status"] == "UNDER_REVIEW"
    assert len(emp_dossier["information_requests"]) == 1
    assert emp_dossier["information_requests"][0]["status"] == "RESPONDED"
    assert emp_dossier["information_requests"][0]["response_notes"] == "Uploaded HDFC salary statement for last 6 months"

    # 11. Customer application ownership remains enforced
    # Another customer cannot access or sync this application
    res_other_cust_blocked = client.get(
        f"/api/applications/{loan_app.id}",
        headers=other_cust_headers
    )
    assert res_other_cust_blocked.status_code == 404

    # 12. Document authorization remains enforced
    # Another customer cannot view or serve the uploaded document content
    res_other_doc_blocked = client.get(
        f"/api/documents/{doc.id}/content",
        headers=other_cust_headers
    )
    assert res_other_doc_blocked.status_code == 403
