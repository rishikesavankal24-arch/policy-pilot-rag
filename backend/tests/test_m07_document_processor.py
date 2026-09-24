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
from app.api.documents import STORAGE_DIR
import uuid
import io
import shutil
import hashlib
import pypdf
from app.db.session import SessionLocal

client = TestClient(app)

def make_pdf_bytes(page_count: int) -> bytes:
    """Helper to generate a structurally valid minimal PDF with the requested number of pages."""
    writer = pypdf.PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        test_users = db.query(User).filter(User.email.like("test_m07_proc_%@example.com")).all()
        for user in test_users:
            docs = db.query(Document).filter(Document.user_id == user.id).all()
            for d in docs:
                doc_dir = STORAGE_DIR / str(d.id)
                if doc_dir.exists():
                    shutil.rmtree(doc_dir, ignore_errors=True)
            apps = db.query(Application).filter(Application.user_id == user.id).all()
            for app_obj in apps:
                db.query(AdditionalInformationRequest).filter(AdditionalInformationRequest.application_id == app_obj.id).delete()
                db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.application_id == app_obj.id).delete()
            db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.user_id == user.id).delete()
            db.query(Notification).filter(Notification.user_id == user.id).delete()
            db.query(Document).filter(Document.reviewed_by == user.id).update({Document.reviewed_by: None})
            db.query(Document).filter(Document.user_id == user.id).delete()
            db.query(Application).filter(Application.user_id == user.id).delete()
            db.query(EmployeeRequest).filter((EmployeeRequest.user_id == user.id) | (EmployeeRequest.reviewed_by == user.id)).delete()
            db.query(DBSession).filter(DBSession.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()


def create_user_helper(db, prefix, role=Role.CUSTOMER.value, onboarding_status=OnboardingStatus.COMPLETED.value):
    uid = uuid.uuid4()
    email = f"test_m07_proc_{prefix}_{uid.hex[:6]}@example.com"
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
        emp_req = EmployeeRequest(
            user_id=user.id,
            organization="PolicyPilot Verification Desk",
            department="Credit & Compliance Operations",
            employee_id=f"EMP-{uid.hex[:4].upper()}",
            designation="Senior Credit Officer",
            work_email=email,
            status=EmployeeRequestStatus.APPROVED.value if onboarding_status == OnboardingStatus.COMPLETED.value else EmployeeRequestStatus.PENDING.value
        )
        db.add(emp_req)
        db.commit()

    token = create_user_session(db, user.id)
    return user, {"session_id": token}


# ==============================================================================
# 1. One-Page & Multi-Page PDF Page Count Extraction
# ==============================================================================

def test_one_page_and_multipage_pdf_page_count_extraction(db_session):
    customer, cookies = create_user_helper(db_session, "pdf_pages")

    # 1-page PDF
    pdf_1 = make_pdf_bytes(1)
    res_1 = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("passport_1page.pdf", io.BytesIO(pdf_1), "application/pdf")},
        cookies=cookies
    )
    assert res_1.status_code == 200, res_1.text
    data_1 = res_1.json()
    assert data_1["page_count"] == 1
    # Verify DB
    doc_db_1 = db_session.query(Document).filter(Document.id == data_1["id"]).first()
    assert doc_db_1.page_count == 1

    # 3-page PDF
    pdf_3 = make_pdf_bytes(3)
    res_3 = client.post(
        "/api/documents/",
        data={"document_type": "BANK_STATEMENT"},
        files={"file": ("statement_3pages.pdf", io.BytesIO(pdf_3), "application/pdf")},
        cookies=cookies
    )
    assert res_3.status_code == 200, res_3.text
    data_3 = res_3.json()
    assert data_3["page_count"] == 3
    doc_db_3 = db_session.query(Document).filter(Document.id == data_3["id"]).first()
    assert doc_db_3.page_count == 3

    # 5-page PDF
    pdf_5 = make_pdf_bytes(5)
    res_5 = client.post(
        "/api/documents/",
        data={"document_type": "INCOME_PROOF"},
        files={"file": ("tax_return_5pages.pdf", io.BytesIO(pdf_5), "application/pdf")},
        cookies=cookies
    )
    assert res_5.status_code == 200, res_5.text
    data_5 = res_5.json()
    assert data_5["page_count"] == 5
    doc_db_5 = db_session.query(Document).filter(Document.id == data_5["id"]).first()
    assert doc_db_5.page_count == 5


# ==============================================================================
# 2. Image Uploads: page_count Must Remain None
# ==============================================================================

def test_image_uploads_page_count_is_none(db_session):
    customer, cookies = create_user_helper(db_session, "img_pages")

    # PNG upload
    res_png = client.post(
        "/api/documents/",
        data={"document_type": "ADDRESS_PROOF"},
        files={"file": ("proof.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
        cookies=cookies
    )
    assert res_png.status_code == 200, res_png.text
    png_data = res_png.json()
    assert png_data["page_count"] is None
    doc_db_png = db_session.query(Document).filter(Document.id == png_data["id"]).first()
    assert doc_db_png.page_count is None

    # JPEG upload
    res_jpg = client.post(
        "/api/documents/",
        data={"document_type": "OTHER"},
        files={"file": ("photo.jpeg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
        cookies=cookies
    )
    assert res_jpg.status_code == 200, res_jpg.text
    jpg_data = res_jpg.json()
    assert jpg_data["page_count"] is None
    doc_db_jpg = db_session.query(Document).filter(Document.id == jpg_data["id"]).first()
    assert doc_db_jpg.page_count is None


# ==============================================================================
# 3. Structurally Corrupted PDF Fails Safely
# ==============================================================================

def test_structurally_corrupted_pdf_fails_safely(db_session):
    customer, cookies = create_user_helper(db_session, "corrupt_pdf")

    # Has valid PDF header and trailer, but corrupted body / unreadable page tree
    corrupted_pdf = b"%PDF-1.4\nBroken internal xref structure with no valid catalog or pages\n%%EOF"
    res_corrupt = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("corrupted.pdf", io.BytesIO(corrupted_pdf), "application/pdf")},
        cookies=cookies
    )
    assert res_corrupt.status_code == 400
    assert "invalid or corrupted pdf document" in res_corrupt.json()["detail"].lower()

    # Verify no document record created in DB
    db_docs = db_session.query(Document).filter(Document.user_id == customer.id).all()
    assert len(db_docs) == 0


# ==============================================================================
# 4. Client Cannot Spoof page_count
# ==============================================================================

def test_client_cannot_spoof_page_count(db_session):
    customer, cookies = create_user_helper(db_session, "spoof_attempt")

    # Valid 1-page PDF, but client sends page_count=99 in form data
    pdf_1 = make_pdf_bytes(1)
    res_spoof = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF", "page_count": "99"},
        files={"file": ("spoof_attempt.pdf", io.BytesIO(pdf_1), "application/pdf")},
        cookies=cookies
    )
    assert res_spoof.status_code == 200, res_spoof.text
    data = res_spoof.json()
    # Server must compute actual count (1) and ignore client's attempted spoof (99)
    assert data["page_count"] == 1
    doc_db = db_session.query(Document).filter(Document.id == data["id"]).first()
    assert doc_db.page_count == 1


# ==============================================================================
# 5. Replacement Lifecycle & Page Count Updates
# ==============================================================================

def test_replacement_page_count_lifecycle(db_session):
    customer, cookies_cust = create_user_helper(db_session, "rep_cust")
    employee, cookies_emp = create_user_helper(db_session, "rep_emp", Role.EMPLOYEE.value)

    # 1. Customer creates application & uploads initial 1-page PDF
    app_obj = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Personal Loan",
        requested_amount=100000,
        tenure=12,
        purpose="Travel",
        status=ApplicationStatus.UNDER_REVIEW.value
    )
    db_session.add(app_obj)
    db_session.commit()

    initial_pdf = make_pdf_bytes(1)
    upload_res = client.post(
        "/api/documents/",
        data={"document_type": "INCOME_PROOF", "application_id": str(app_obj.id)},
        files={"file": ("salary_1page.pdf", io.BytesIO(initial_pdf), "application/pdf")},
        cookies=cookies_cust
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]
    assert upload_res.json()["page_count"] == 1

    # 2. Employee marks REQUIRES_REUPLOAD
    rev_res = client.post(
        f"/api/employee/documents/{doc_id}/review",
        json={"status": "REQUIRES_REUPLOAD", "reason": "Please attach all 3 months of pay slips"},
        cookies=cookies_emp
    )
    assert rev_res.status_code == 200

    # 3. Customer uploads corrupted PDF as replacement -> fails safely
    corrupt_rep = b"%PDF-1.4\nCorrupted replacement bytes\n%%EOF"
    bad_rep_res = client.post(
        "/api/documents/",
        data={
            "document_type": "INCOME_PROOF",
            "application_id": str(app_obj.id),
            "replaces_document_id": str(doc_id)
        },
        files={"file": ("corrupt_rep.pdf", io.BytesIO(corrupt_rep), "application/pdf")},
        cookies=cookies_cust
    )
    assert bad_rep_res.status_code == 400
    assert "invalid or corrupted pdf document" in bad_rep_res.json()["detail"].lower()

    # Verify old file and old page_count (1) remain completely untouched
    db_session.expire_all()
    old_doc = db_session.query(Document).filter(Document.id == doc_id).first()
    assert old_doc.status == "REQUIRES_REUPLOAD"
    assert old_doc.page_count == 1
    assert old_doc.original_filename == "salary_1page.pdf"

    serve_old = client.get(f"/api/documents/{doc_id}/content", cookies=cookies_cust)
    assert serve_old.status_code == 200
    assert serve_old.content == initial_pdf

    # 4. Customer uploads valid 3-page PDF replacement -> succeeds
    new_pdf_3 = make_pdf_bytes(3)
    good_rep_res = client.post(
        "/api/documents/",
        data={
            "document_type": "INCOME_PROOF",
            "application_id": str(app_obj.id),
            "replaces_document_id": str(doc_id)
        },
        files={"file": ("salary_3months.pdf", io.BytesIO(new_pdf_3), "application/pdf")},
        cookies=cookies_cust
    )
    assert good_rep_res.status_code == 200
    rep_data = good_rep_res.json()
    assert rep_data["id"] == str(doc_id)
    assert rep_data["status"] == "UPLOADED"
    assert rep_data["page_count"] == 3
    assert rep_data["original_filename"] == "salary_3months.pdf"

    # Verify new content served
    serve_new = client.get(f"/api/documents/{doc_id}/content", cookies=cookies_cust)
    assert serve_new.status_code == 200
    assert serve_new.content == new_pdf_3


# ==============================================================================
# 6. Additional Information Upload Page Count Extraction
# ==============================================================================

def test_additional_information_upload_page_count_extraction(db_session):
    customer, cookies_cust = create_user_helper(db_session, "info_cust")
    employee, cookies_emp = create_user_helper(db_session, "info_emp", Role.EMPLOYEE.value)

    app_obj = Application(
        id=uuid.uuid4(),
        user_id=customer.id,
        loan_type="Education Loan",
        requested_amount=500000,
        tenure=24,
        purpose="Higher Studies",
        status=ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value
    )
    db_session.add(app_obj)
    db_session.commit()

    info_req = AdditionalInformationRequest(
        id=uuid.uuid4(),
        application_id=app_obj.id,
        requested_by=employee.id,
        title="College Fee Schedule",
        description="Please upload official university fee schedule.",
        requested_document_type="OTHER",
        status=InformationRequestStatus.OPEN.value
    )
    db_session.add(info_req)
    db_session.commit()

    pdf_2 = make_pdf_bytes(2)
    res_info = client.post(
        f"/api/customer/applications/{app_obj.id}/information-requests/{info_req.id}/respond",
        data={"notes": "Attached official 2-page fee schedule."},
        files={"file": ("fee_schedule_2pages.pdf", io.BytesIO(pdf_2), "application/pdf")},
        cookies=cookies_cust
    )
    assert res_info.status_code == 200, res_info.text
    db_session.refresh(info_req)
    assert info_req.status == InformationRequestStatus.RESPONDED.value

    resp_doc = db_session.query(Document).filter(Document.id == info_req.response_document_id).first()
    assert resp_doc is not None
    assert resp_doc.original_filename == "fee_schedule_2pages.pdf"
    assert resp_doc.page_count == 2
