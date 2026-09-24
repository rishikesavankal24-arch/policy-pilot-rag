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
from app.db.session import SessionLocal

client = TestClient(app)

from tests.pdf_fixtures import make_test_pdf_bytes

# Standard byte sequences for valid test files
VALID_PDF_BYTES = make_test_pdf_bytes(1)
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        test_users = db.query(User).filter(User.email.like("test_m07_val_%@example.com")).all()
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
    email = f"test_m07_val_{prefix}_{uid.hex[:6]}@example.com"
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
# 1. Valid Uploads (PDF, PNG, JPEG, Uppercase Extensions) & Metadata Verification
# ==============================================================================

def test_valid_pdf_png_jpeg_and_uppercase_extensions(db_session):
    customer, cookies = create_user_helper(db_session, "valid_formats")

    # 1. Valid PDF upload with SHA-256 and metadata check
    expected_pdf_hash = hashlib.sha256(VALID_PDF_BYTES).hexdigest()
    res_pdf = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("my_passport.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
        cookies=cookies
    )
    assert res_pdf.status_code == 200, res_pdf.text
    pdf_data = res_pdf.json()
    assert pdf_data["original_filename"] == "my_passport.pdf"
    assert pdf_data["file_size_bytes"] == len(VALID_PDF_BYTES)
    assert pdf_data["mime_type"] == "application/pdf"
    assert pdf_data["file_hash"] == expected_pdf_hash

    # Verify physical file was persisted and matches expected bytes
    content_res = client.get(f"/api/documents/{pdf_data['id']}/content", cookies=cookies)
    assert content_res.status_code == 200
    assert content_res.content == VALID_PDF_BYTES

    # 2. Valid PNG upload
    expected_png_hash = hashlib.sha256(VALID_PNG_BYTES).hexdigest()
    res_png = client.post(
        "/api/documents/",
        data={"document_type": "ADDRESS_PROOF"},
        files={"file": ("electric_bill.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
        cookies=cookies
    )
    assert res_png.status_code == 200
    png_data = res_png.json()
    assert png_data["original_filename"] == "electric_bill.png"
    assert png_data["file_size_bytes"] == len(VALID_PNG_BYTES)
    assert png_data["mime_type"] == "image/png"
    assert png_data["file_hash"] == expected_png_hash

    # 3. Valid JPEG upload
    expected_jpeg_hash = hashlib.sha256(VALID_JPEG_BYTES).hexdigest()
    res_jpg = client.post(
        "/api/documents/",
        data={"document_type": "INCOME_PROOF"},
        files={"file": ("salary_slip.jpeg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
        cookies=cookies
    )
    assert res_jpg.status_code == 200
    jpg_data = res_jpg.json()
    assert jpg_data["original_filename"] == "salary_slip.jpeg"
    assert jpg_data["file_size_bytes"] == len(VALID_JPEG_BYTES)
    assert jpg_data["mime_type"] == "image/jpeg"
    assert jpg_data["file_hash"] == expected_jpeg_hash

    # 4. Uppercase extensions (.PDF, .PNG, .JPG) accepted
    res_upper_pdf = client.post(
        "/api/documents/",
        data={"document_type": "BANK_STATEMENT"},
        files={"file": ("STATEMENT.PDF", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
        cookies=cookies
    )
    assert res_upper_pdf.status_code == 200
    assert res_upper_pdf.json()["mime_type"] == "application/pdf"

    res_upper_jpg = client.post(
        "/api/documents/",
        data={"document_type": "OTHER"},
        files={"file": ("PHOTO.JPG", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
        cookies=cookies
    )
    assert res_upper_jpg.status_code == 200
    assert res_upper_jpg.json()["mime_type"] == "image/jpeg"


# ==============================================================================
# 2. Rejection Tests: Unsupported Extensions, 0-byte, >10MB, Invalid Type
# ==============================================================================

def test_unsupported_extensions_and_empty_files_rejected(db_session):
    customer, cookies = create_user_helper(db_session, "reject_tests")

    # 1. Unsupported extensions rejected (.exe, .sh, .html, .zip, .docx)
    for bad_ext in ["malware.exe", "script.sh", "page.html", "archive.zip", "doc.docx", "sheet.xlsx"]:
        res_ext = client.post(
            "/api/documents/",
            data={"document_type": "IDENTITY_PROOF"},
            files={"file": (bad_ext, io.BytesIO(b"dummy payload bytes"), "application/octet-stream")},
            cookies=cookies
        )
        assert res_ext.status_code == 400
        assert "unsupported file type" in res_ext.json()["detail"].lower()

    # 2. Empty file (0 bytes) rejected
    res_empty = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        cookies=cookies
    )
    assert res_empty.status_code == 400
    assert "empty files are not allowed" in res_empty.json()["detail"].lower()

    # 3. File exceeding 10 MB rejected
    # 10 MB + 1 byte
    oversized_bytes = b"0" * (10 * 1024 * 1024 + 1)
    res_oversize = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("huge.pdf", io.BytesIO(oversized_bytes), "application/pdf")},
        cookies=cookies
    )
    assert res_oversize.status_code == 400
    assert "10 mb limit" in res_oversize.json()["detail"].lower()

    # 4. Invalid document type rejected
    res_invalid_type = client.post(
        "/api/documents/",
        data={"document_type": "MALICIOUS_UNAPPROVED_TYPE"},
        files={"file": ("valid.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
        cookies=cookies
    )
    assert res_invalid_type.status_code == 400
    assert "invalid document type" in res_invalid_type.json()["detail"].lower()


# ==============================================================================
# 3. Magic Byte & Content/MIME Mismatch Verification
# ==============================================================================

def test_magic_byte_and_content_mismatch_validation(db_session):
    customer, cookies = create_user_helper(db_session, "magic_bytes")

    # 1. Renamed executable / plain text with .pdf extension rejected
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00This is a Windows executable binary disguised as PDF"
    res_fake_pdf = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("passport.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        cookies=cookies
    )
    assert res_fake_pdf.status_code == 400
    assert "does not match the declared file type" in res_fake_pdf.json()["detail"]

    # 2. File named .pdf containing PNG bytes rejected
    res_png_as_pdf = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("document.pdf", io.BytesIO(VALID_PNG_BYTES), "application/pdf")},
        cookies=cookies
    )
    assert res_png_as_pdf.status_code == 400
    assert "does not match the declared file type" in res_png_as_pdf.json()["detail"]

    # 3. File named .jpg containing PDF bytes rejected
    res_pdf_as_jpg = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("photo.jpg", io.BytesIO(VALID_PDF_BYTES), "image/jpeg")},
        cookies=cookies
    )
    assert res_pdf_as_jpg.status_code == 400
    assert "does not match the declared file type" in res_pdf_as_jpg.json()["detail"]

    # 4. MIME type contradiction (e.g. extension .pdf with declared content-type image/png)
    res_mime_mismatch = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("document.pdf", io.BytesIO(VALID_PDF_BYTES), "image/png")},
        cookies=cookies
    )
    assert res_mime_mismatch.status_code == 400
    assert "does not match" in res_mime_mismatch.json()["detail"].lower()

    # 5. Corrupted / truncated file (e.g. only 3 bytes for PDF)
    corrupted_pdf = b"%PD"
    res_corrupt = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("corrupt.pdf", io.BytesIO(corrupted_pdf), "application/pdf")},
        cookies=cookies
    )
    assert res_corrupt.status_code == 400


# ==============================================================================
# 4. Replacement Atomicity & Metadata Preservation
# ==============================================================================

def test_replacement_atomicity_preserves_old_file_on_validation_failure(db_session):
    customer, cookies_cust = create_user_helper(db_session, "atom_cust")
    employee, cookies_emp = create_user_helper(db_session, "atom_emp", Role.EMPLOYEE.value)

    # 1. Customer creates application & uploads initial valid PDF
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

    initial_pdf_bytes = make_test_pdf_bytes(1)
    initial_hash = hashlib.sha256(initial_pdf_bytes).hexdigest()

    upload_res = client.post(
        "/api/documents/",
        data={"document_type": "INCOME_PROOF", "application_id": str(app_obj.id)},
        files={"file": ("original_salary.pdf", io.BytesIO(initial_pdf_bytes), "application/pdf")},
        cookies=cookies_cust
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    # 2. Employee requires re-upload
    rev_res = client.post(
        f"/api/employee/documents/{doc_id}/review",
        json={"status": "REQUIRES_REUPLOAD", "reason": "Please provide clearer copy"},
        cookies=cookies_emp
    )
    assert rev_res.status_code == 200

    # Verify initial document metadata in DB
    db_doc_before = db_session.query(Document).filter(Document.id == doc_id).first()
    assert db_doc_before.status == "REQUIRES_REUPLOAD"
    assert db_doc_before.file_hash == initial_hash
    assert db_doc_before.original_filename == "original_salary.pdf"

    # 3. Customer attempts invalid replacement (e.g. an executable or corrupted file)
    bad_replacement_bytes = b"MZ executable content that fails magic byte verification"
    fail_res = client.post(
        "/api/documents/",
        data={
            "document_type": "INCOME_PROOF",
            "application_id": str(app_obj.id),
            "replaces_document_id": str(doc_id)
        },
        files={"file": ("replacement.pdf", io.BytesIO(bad_replacement_bytes), "application/pdf")},
        cookies=cookies_cust
    )
    assert fail_res.status_code == 400

    # 4. Critical check: Original document record and physical file are completely intact!
    db_session.refresh(db_doc_before)
    assert db_doc_before.status == "REQUIRES_REUPLOAD"
    assert db_doc_before.file_hash == initial_hash
    assert db_doc_before.original_filename == "original_salary.pdf"
    assert db_doc_before.review_notes == "Please provide clearer copy"

    # Old physical content still serves original bytes
    serve_res = client.get(f"/api/documents/{doc_id}/content", cookies=cookies_cust)
    assert serve_res.status_code == 200
    assert serve_res.content == initial_pdf_bytes

    # 5. Customer uploads valid replacement -> succeeds, preserves Document.id, updates hash
    new_valid_bytes = make_test_pdf_bytes(2)
    new_hash = hashlib.sha256(new_valid_bytes).hexdigest()

    success_rep = client.post(
        "/api/documents/",
        data={
            "document_type": "INCOME_PROOF",
            "application_id": str(app_obj.id),
            "replaces_document_id": str(doc_id)
        },
        files={"file": ("clear_salary_replacement.pdf", io.BytesIO(new_valid_bytes), "application/pdf")},
        cookies=cookies_cust
    )
    assert success_rep.status_code == 200
    rep_json = success_rep.json()
    assert rep_json["id"] == str(doc_id)  # Preserves same Document.id
    assert rep_json["status"] == "UPLOADED"  # Status reset
    assert rep_json["file_hash"] == new_hash
    assert rep_json["original_filename"] == "clear_salary_replacement.pdf"

    # Verify new physical file content is served
    new_serve_res = client.get(f"/api/documents/{doc_id}/content", cookies=cookies_cust)
    assert new_serve_res.status_code == 200
    assert new_serve_res.content == new_valid_bytes


# ==============================================================================
# 5. Additional Information Response Upload Validation
# ==============================================================================

def test_additional_information_response_enforces_validation(db_session):
    customer, cookies_cust = create_user_helper(db_session, "info_val_cust")
    employee, cookies_emp = create_user_helper(db_session, "info_val_emp", Role.EMPLOYEE.value)

    # 1. Setup application and open information request
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

    # 2. Customer attempts invalid upload (empty file) -> rejected, request stays OPEN
    res_empty = client.post(
        f"/api/customer/applications/{app_obj.id}/information-requests/{info_req.id}/respond",
        data={"notes": "Empty response attempt"},
        files={"file": ("fees.pdf", io.BytesIO(b""), "application/pdf")},
        cookies=cookies_cust
    )
    assert res_empty.status_code == 400
    assert "empty files are not allowed" in res_empty.json()["detail"].lower()

    # Request remains OPEN
    db_session.refresh(info_req)
    assert info_req.status == InformationRequestStatus.OPEN.value
    assert info_req.response_document_id is None

    # 3. Customer attempts invalid upload (disguised .exe) -> rejected
    res_fake = client.post(
        f"/api/customer/applications/{app_obj.id}/information-requests/{info_req.id}/respond",
        data={"notes": "Disguised binary attempt"},
        files={"file": ("fees.pdf", io.BytesIO(b"MZ\x00Not a PDF"), "application/pdf")},
        cookies=cookies_cust
    )
    assert res_fake.status_code == 400
    assert info_req.status == InformationRequestStatus.OPEN.value

    # 4. Customer uploads valid PDF -> succeeds, request becomes RESPONDED, metadata populated
    expected_hash = hashlib.sha256(VALID_PDF_BYTES).hexdigest()
    res_valid = client.post(
        f"/api/customer/applications/{app_obj.id}/information-requests/{info_req.id}/respond",
        data={"notes": "Attached official fee structure schedule."},
        files={"file": ("fee_schedule_2026.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
        cookies=cookies_cust
    )
    assert res_valid.status_code == 200
    db_session.refresh(info_req)
    assert info_req.status == InformationRequestStatus.RESPONDED.value
    assert info_req.response_document_id is not None

    resp_doc = db_session.query(Document).filter(Document.id == info_req.response_document_id).first()
    assert resp_doc.original_filename == "fee_schedule_2026.pdf"
    assert resp_doc.file_size_bytes == len(VALID_PDF_BYTES)
    assert resp_doc.mime_type == "application/pdf"
    assert resp_doc.file_hash == expected_hash
