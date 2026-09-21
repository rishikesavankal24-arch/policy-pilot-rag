import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import (
    User, Role, OnboardingStatus, Application, ApplicationStatus,
    Document, DocumentStatus, EmployeeRequest, EmployeeRequestStatus,
    Notification, Session as DBSession, AdditionalInformationRequest,
    InformationRequestStatus, ApplicationAuditEvent
)
from app.core.security import create_user_session
import uuid
import io
from app.db.session import SessionLocal

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        test_users = db.query(User).filter(User.email.like("test_doc_rev_%@example.com")).all()
        for user in test_users:
            apps = db.query(Application).filter(Application.user_id == user.id).all()
            for app_obj in apps:
                db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.application_id == app_obj.id).delete()
                db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.application_id == app_obj.id).delete()
            db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.requested_by == user.id).delete()
            db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.user_id == user.id).delete()
            db.query(Notification).filter(Notification.user_id == user.id).delete()
            db.query(Document).filter((Document.user_id == user.id) | (Document.reviewed_by == user.id)).delete()
            db.query(Application).filter(Application.user_id == user.id).delete()
            db.query(EmployeeRequest).filter((EmployeeRequest.user_id == user.id) | (EmployeeRequest.reviewed_by == user.id)).delete()
            db.query(DBSession).filter(DBSession.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()

def create_user_helper(db, prefix, role=Role.CUSTOMER.value, onboarding_status=OnboardingStatus.COMPLETED.value):
    uid = uuid.uuid4()
    email = f"test_doc_rev_{prefix}_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name=f"User {prefix.capitalize()}",
        role=role,
        requested_role=role,
        onboarding_status=onboarding_status,
        authentication_provider="local",
        provider_subject_id=email,
        phone_number="+919876543210",
        date_of_birth="1992-05-15",
        address="123 Financial District",
        city="Mumbai",
        state="Maharashtra",
        pincode="400051"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if role == Role.EMPLOYEE.value:
        req = EmployeeRequest(
            user_id=user.id,
            organization="PolicyPilot Operations Desk",
            department="Retail Credit Operations",
            employee_id=f"EMP-{uid.hex[:4].upper()}",
            designation="Credit Underwriting Analyst",
            reason="Reviewing loan files",
            status=EmployeeRequestStatus.APPROVED.value if onboarding_status == OnboardingStatus.COMPLETED.value else EmployeeRequestStatus.PENDING.value
        )
        db.add(req)
        db.commit()

    token = create_user_session(db, user.id)
    return user, {"session_id": token}


def test_full_document_review_and_info_request_lifecycle(db_session):
    # 1. Setup Customer A, Customer B, Employee
    customer_a, cookies_cust_a = create_user_helper(db_session, "cust_a", Role.CUSTOMER.value)
    customer_b, cookies_cust_b = create_user_helper(db_session, "cust_b", Role.CUSTOMER.value)
    employee, cookies_emp = create_user_helper(db_session, "emp", Role.EMPLOYEE.value)

    # 2. Customer A creates draft application
    create_res = client.post(
        "/api/applications/",
        json={
            "loan_type": "BUSINESS_EXPANSION",
            "requested_amount": 750000,
            "tenure": 36,
            "purpose": "Equipment purchase",
            "employment_info": "Self Employed",
            "income_info": "3200000",
            "existing_liabilities": "None"
        },
        cookies=cookies_cust_a
    )
    assert create_res.status_code == 200
    app_id = create_res.json()["id"]

    # 3. Customer A uploads 2 documents
    pdf_bytes_1 = b"%PDF-1.4 test certificate alpha 1"
    upload_res_1 = client.post(
        "/api/documents/",
        data={"document_type": "INCORPORATION_CERTIFICATE", "application_id": str(app_id)},
        files={"file": ("cert.pdf", io.BytesIO(pdf_bytes_1), "application/pdf")},
        cookies=cookies_cust_a
    )
    assert upload_res_1.status_code == 200, upload_res_1.text
    doc_1_id = upload_res_1.json()["id"]

    pdf_bytes_2 = b"%PDF-1.4 test financial report alpha 2"
    upload_res_2 = client.post(
        "/api/documents/",
        data={"document_type": "FINANCIAL_STATEMENT", "application_id": str(app_id)},
        files={"file": ("financials.pdf", io.BytesIO(pdf_bytes_2), "application/pdf")},
        cookies=cookies_cust_a
    )
    assert upload_res_2.status_code == 200, upload_res_2.text
    doc_2_id = upload_res_2.json()["id"]

    # 4. Customer A submits application
    submit_res = client.post(f"/api/applications/{app_id}/submit", cookies=cookies_cust_a)
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == ApplicationStatus.SUBMITTED.value

    # 5. Employee inspects application (READ ONLY)
    inspect_res = client.get(f"/api/employee/applications/{app_id}", cookies=cookies_emp)
    assert inspect_res.status_code == 200
    detail = inspect_res.json()
    assert detail["application"]["status"] == ApplicationStatus.SUBMITTED.value
    assert len(detail["documents"]) == 2
    for doc in detail["documents"]:
        assert doc["status"] == DocumentStatus.UPLOADED.value
        assert doc["reviewed_by"] is None

    # 6. Employee starts review (explicit transition)
    start_res = client.post(f"/api/employee/applications/{app_id}/transition-review", cookies=cookies_emp)
    assert start_res.status_code == 200
    assert start_res.json()["application"]["status"] == ApplicationStatus.UNDER_REVIEW.value

    # 7. Employee reviews doc 1: ACCEPT
    review_res_1 = client.post(
        f"/api/employee/documents/{doc_1_id}/review",
        json={"status": "ACCEPTED", "reason": "Certificate verified with ROC records"},
        cookies=cookies_emp
    )
    assert review_res_1.status_code == 200
    assert review_res_1.json()["status"] == DocumentStatus.ACCEPTED.value
    assert review_res_1.json()["reviewed_by"] == str(employee.id)
    assert review_res_1.json()["review_notes"] == "Certificate verified with ROC records"

    # 8. Employee attempts to reject doc 2 with empty reason -> 400 Bad Request
    fail_res = client.post(
        f"/api/employee/documents/{doc_2_id}/review",
        json={"status": "REQUIRES_REUPLOAD", "reason": "   "},
        cookies=cookies_emp
    )
    assert fail_res.status_code == 400
    assert "reason" in fail_res.json()["detail"].lower()

    # 9. Employee requires re-upload for doc 2 with valid reason
    reupload_res = client.post(
        f"/api/employee/documents/{doc_2_id}/review",
        json={"status": "REQUIRES_REUPLOAD", "reason": "CA stamp missing on pages 3 and 4"},
        cookies=cookies_emp
    )
    assert reupload_res.status_code == 200
    assert reupload_res.json()["status"] == DocumentStatus.REQUIRES_REUPLOAD.value
    assert reupload_res.json()["review_notes"] == "CA stamp missing on pages 3 and 4"

    # 10. Employee requests Additional Information
    req_info_res = client.post(
        f"/api/employee/applications/{app_id}/information-requests",
        json={
            "title": "Audited Balance Sheet FY2025",
            "description": "Please upload the complete audited balance sheet with CA attestation.",
            "requested_document_type": "AUDITED_BALANCE_SHEET"
        },
        cookies=cookies_emp
    )
    assert req_info_res.status_code == 200
    info_req_data = req_info_res.json()
    assert info_req_data["title"] == "Audited Balance Sheet FY2025"
    assert info_req_data["status"] == InformationRequestStatus.OPEN.value
    info_req_id = info_req_data["id"]

    # 11. Application status must now be ADDITIONAL_INFO_REQUIRED
    app_check = client.get(f"/api/employee/applications/{app_id}", cookies=cookies_emp).json()
    assert app_check["application"]["status"] == ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value
    assert len(app_check["information_requests"]) == 1

    # 12. Customer A inspects application -> sees ADDITIONAL_INFO_REQUIRED and the request
    cust_app_res = client.get(f"/api/applications/{app_id}", cookies=cookies_cust_a)
    assert cust_app_res.status_code == 200
    assert cust_app_res.json()["application"]["status"] == ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value
    assert len(cust_app_res.json()["information_requests"]) == 1
    assert cust_app_res.json()["information_requests"][0]["id"] == info_req_id

    # 13. Customer A checks /api/customer/actions -> finds pending action
    actions_res = client.get("/api/customer/actions", cookies=cookies_cust_a)
    assert actions_res.status_code == 200
    actions_data = actions_res.json()
    assert actions_data["total_actions"] >= 1
    actions_list = actions_data["actions"]
    matching_action = next((a for a in actions_list if a.get("request_id") == str(info_req_id)), None)
    assert matching_action is not None
    assert matching_action["type"] == "INFORMATION_REQUEST"

    # 14. Unauthorized Customer B attempts to respond -> 403 Forbidden
    unauth_resp = client.post(
        f"/api/customer/applications/{app_id}/information-requests/{info_req_id}/respond",
        data={"notes": "Hacked response"},
        files={"file": ("fake.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf")},
        cookies=cookies_cust_b
    )
    assert unauth_resp.status_code in [403, 404]

    # 15. Customer A responds with requested document
    resp_doc_bytes = b"%PDF-1.4 audited balance sheet FY25 authentic content"
    respond_res = client.post(
        f"/api/customer/applications/{app_id}/information-requests/{info_req_id}/respond",
        data={"notes": "Attached signed balance sheet with partner signature and seal."},
        files={"file": ("audited_balance_sheet.pdf", io.BytesIO(resp_doc_bytes), "application/pdf")},
        cookies=cookies_cust_a
    )
    assert respond_res.status_code == 200
    resp_data = respond_res.json()
    assert resp_data["request"]["status"] == InformationRequestStatus.RESPONDED.value
    assert resp_data["request"]["response_document_id"] is not None
    resp_doc_id = resp_data["request"]["response_document_id"]

    # 16. Application status must automatically transition back to UNDER_REVIEW
    cust_app_after = client.get(f"/api/applications/{app_id}", cookies=cookies_cust_a).json()
    assert cust_app_after["application"]["status"] == ApplicationStatus.UNDER_REVIEW.value

    # 17. Employee views application detail -> sees request RESPONDED with response document
    emp_app_after = client.get(f"/api/employee/applications/{app_id}", cookies=cookies_emp).json()
    assert emp_app_after["application"]["status"] == ApplicationStatus.UNDER_REVIEW.value
    info_req_found = next((r for r in emp_app_after["information_requests"] if r["id"] == info_req_id), None)
    assert info_req_found is not None
    assert info_req_found["status"] == InformationRequestStatus.RESPONDED.value
    assert info_req_found["response_document_id"] == resp_doc_id

    # 18. Employee opens the response document via /api/documents/{id}/content
    content_res = client.get(f"/api/documents/{resp_doc_id}/content", cookies=cookies_emp)
    assert content_res.status_code == 200
    assert content_res.headers["content-type"] == "application/pdf"
    assert b"audited balance sheet FY25 authentic content" in content_res.content

    # 19. Conflict of interest validation: Employee cannot review their own application
    own_app = Application(
        id=uuid.uuid4(),
        user_id=employee.id,
        loan_type="WORKING_CAPITAL",
        requested_amount=100000,
        tenure=12,
        purpose="Test internal loan",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(own_app)
    db_session.commit()

    coi_res = client.post(
        f"/api/employee/applications/{own_app.id}/information-requests",
        json={"title": "Self test", "description": "test"},
        cookies=cookies_emp
    )
    assert coi_res.status_code == 403
    assert "conflict of interest" in coi_res.json()["detail"].lower()

    # 20. Customer cannot access employee document review endpoint
    cust_rev_res = client.post(
        f"/api/employee/documents/{doc_1_id}/review",
        json={"status": "ACCEPTED", "reason": "test"},
        cookies=cookies_cust_a
    )
    assert cust_rev_res.status_code == 403
