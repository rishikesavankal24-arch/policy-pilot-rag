import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import (
    User, 
    Role, 
    OnboardingStatus, 
    Application, 
    ApplicationStatus, 
    Document, 
    DocumentStatus, 
    Session as DBSession,
    EmployeeRequest,
    EmployeeRequestStatus
)
from app.core.security import create_user_session
from app.api.documents import STORAGE_DIR, sanitize_filename
import uuid
import io
from pathlib import Path
from app.db.session import SessionLocal

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        test_users = db.query(User).filter(User.email.like("test_doc_%@example.com")).all()
        for user in test_users:
            docs = db.query(Document).filter(Document.user_id == user.id).all()
            for d in docs:
                doc_dir = STORAGE_DIR / str(d.id)
                if doc_dir.exists():
                    import shutil
                    shutil.rmtree(doc_dir, ignore_errors=True)
            db.query(Document).filter(Document.user_id == user.id).delete()
            db.query(Application).filter(Application.user_id == user.id).delete()
            db.query(EmployeeRequest).filter(EmployeeRequest.user_id == user.id).delete()
            db.query(DBSession).filter(DBSession.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()


def create_user(db, email_prefix, role=Role.CUSTOMER.value, status=OnboardingStatus.COMPLETED.value):
    uid = uuid.uuid4()
    email = f"test_doc_{email_prefix}_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name=f"User {email_prefix.capitalize()}",
        role=role,
        requested_role=role,
        onboarding_status=status,
        authentication_provider="local",
        provider_subject_id=email
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_user_session(db, user.id)
    return user, token


def make_verified_employee(db, email_prefix):
    emp, token = create_user(db, email_prefix, role=Role.EMPLOYEE.value, status=OnboardingStatus.COMPLETED.value)
    req = EmployeeRequest(
        user_id=emp.id,
        organization="PolicyPilot Verification Unit",
        department="Underwriting",
        employee_id=f"EMP-{uuid.uuid4().hex[:4].upper()}",
        designation="Senior Underwriter",
        work_email=emp.email,
        status=EmployeeRequestStatus.APPROVED.value
    )
    db.add(req)
    db.commit()
    return emp, token


def test_customer_can_upload_and_serve_real_pdf(db_session):
    cust, token = create_user(db_session, "uploader")
    client = TestClient(app, cookies={"session_id": token})

    # Real PDF bytes
    pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0>>endobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\ntrailer<</Size 3/Root 1 0 R>>\nstartxref\n99\n%%EOF\n"
    
    upload_res = client.post(
        "/api/documents/",
        data={"document_type": "IDENTITY_PROOF"},
        files={"file": ("passport.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert upload_res.status_code == 200, upload_res.text
    doc_data = upload_res.json()
    doc_id = doc_data["id"]

    # 1. Verify no mock:// URL
    assert not doc_data["file_url"].startswith("mock://")
    assert f"/api/documents/{doc_id}/content" in doc_data["file_url"]

    # 2. Verify file was saved on disk
    stored_path = STORAGE_DIR / str(doc_id) / "passport.pdf"
    assert stored_path.exists()
    assert stored_path.read_bytes() == pdf_bytes

    # 3. Customer accesses own document content
    content_res = client.get(f"/api/documents/{doc_id}/content")
    assert content_res.status_code == 200
    assert content_res.headers["content-type"] == "application/pdf"
    assert "inline" in content_res.headers.get("content-disposition", "")
    assert content_res.content == pdf_bytes


def test_customer_cannot_access_another_customer_document(db_session):
    cust_a, token_a = create_user(db_session, "cust_a")
    cust_b, token_b = create_user(db_session, "cust_b")

    client_a = TestClient(app, cookies={"session_id": token_a})
    client_b = TestClient(app, cookies={"session_id": token_b})

    # Customer A uploads document
    pdf_bytes = b"%PDF-1.4 Sample Customer A Document %%EOF"
    upload_res = client_a.post(
        "/api/documents/",
        data={"document_type": "INCOME_PROOF"},
        files={"file": ("salary_slip.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    # Customer B attempts to access Customer A's document content
    res_b = client_b.get(f"/api/documents/{doc_id}/content")
    assert res_b.status_code == 403, res_b.text


def test_authorized_employee_can_access_application_document(db_session):
    cust, cust_token = create_user(db_session, "applicant")
    emp, emp_token = make_verified_employee(db_session, "officer")

    cust_client = TestClient(app, cookies={"session_id": cust_token})
    emp_client = TestClient(app, cookies={"session_id": emp_token})

    # Customer creates application
    app_res = cust_client.post(
        "/api/applications/",
        json={
            "loan_type": "Personal Loan",
            "requested_amount": 500000,
            "tenure": 36,
            "purpose": "Home upgrade"
        }
    )
    assert app_res.status_code == 200
    app_id = app_res.json()["id"]

    # Customer uploads document attached to application
    doc_bytes = b"%PDF-1.4 Application Attached Certificate %%EOF"
    upload_res = cust_client.post(
        "/api/documents/",
        data={"document_type": "REGISTRATION_CERTIFICATE", "application_id": app_id},
        files={"file": ("registration_certificate.pdf", io.BytesIO(doc_bytes), "application/pdf")}
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    # Customer submits application
    cust_client.post(f"/api/applications/{app_id}/submit")

    # Employee views application detail
    detail_res = emp_client.get(f"/api/employee/applications/{app_id}")
    assert detail_res.status_code == 200
    docs = detail_res.json()["documents"]
    assert len(docs) == 1
    assert not docs[0]["file_url"].startswith("mock://")
    assert docs[0]["file_url"] == f"/api/documents/{doc_id}/content"

    # Authorized employee opens document content
    doc_content_res = emp_client.get(f"/api/documents/{doc_id}/content")
    assert doc_content_res.status_code == 200
    assert doc_content_res.headers["content-type"] == "application/pdf"
    assert doc_content_res.content == doc_bytes


def test_employee_conflict_of_interest_blocked(db_session):
    # Employee who is also the applicant on their own application
    emp, emp_token = make_verified_employee(db_session, "self_reviewer")
    emp_client = TestClient(app, cookies={"session_id": emp_token})

    # Employee creates their own personal loan application
    app_record = Application(
        user_id=emp.id,
        loan_type="Personal Loan",
        requested_amount=100000,
        tenure=12,
        purpose="Personal",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(app_record)
    db_session.commit()

    # Create document for this application
    doc_id = uuid.uuid4()
    doc_dir = STORAGE_DIR / str(doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    doc_file = doc_dir / "pan_card.pdf"
    doc_file.write_bytes(b"%PDF-1.4 Employee's Own Document %%EOF")

    doc = Document(
        id=doc_id,
        user_id=emp.id,
        application_id=app_record.id,
        document_type="PAN_CARD",
        file_url=f"documents/{doc_id}/pan_card.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    # Employee attempts to access own application document in employee role
    # Should trigger conflict of interest 403
    res = emp_client.get(f"/api/documents/{doc_id}/content")
    assert res.status_code == 403
    assert "conflict-of-interest" in res.json()["detail"].lower()


def test_unverified_employee_cannot_access_document(db_session):
    cust, _ = create_user(db_session, "victim")
    unverified_emp, emp_token = create_user(
        db_session, 
        "unverified", 
        role=Role.EMPLOYEE.value, 
        status=OnboardingStatus.NEW.value
    )
    
    # Store a document for customer
    doc_id = uuid.uuid4()
    doc_dir = STORAGE_DIR / str(doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "test.pdf").write_bytes(b"%PDF-1.4 Sample %%EOF")

    doc = Document(
        id=doc_id,
        user_id=cust.id,
        document_type="ID",
        file_url=f"documents/{doc_id}/test.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    emp_client = TestClient(app, cookies={"session_id": emp_token})
    res = emp_client.get(f"/api/documents/{doc_id}/content")
    assert res.status_code == 403


def test_admin_can_access_document(db_session):
    cust, _ = create_user(db_session, "cust_admin_test")
    admin, admin_token = create_user(db_session, "superadmin", role=Role.ADMIN.value)

    doc_id = uuid.uuid4()
    doc_dir = STORAGE_DIR / str(doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "statement.pdf").write_bytes(b"%PDF-1.4 Admin Audited Statement %%EOF")

    doc = Document(
        id=doc_id,
        user_id=cust.id,
        document_type="BANK_STATEMENT",
        file_url=f"documents/{doc_id}/statement.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    admin_client = TestClient(app, cookies={"session_id": admin_token})
    res = admin_client.get(f"/api/documents/{doc_id}/content")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content == b"%PDF-1.4 Admin Audited Statement %%EOF"


def test_missing_document_returns_404(db_session):
    admin, token = create_user(db_session, "admin_404", role=Role.ADMIN.value)
    client = TestClient(app, cookies={"session_id": token})

    fake_id = uuid.uuid4()
    res = client.get(f"/api/documents/{fake_id}/content")
    assert res.status_code == 404
    assert res.json()["detail"] == "Document not found"


def test_missing_physical_file_returns_404_with_reupload_guidance(db_session):
    cust, token = create_user(db_session, "lost_bytes")
    client = TestClient(app, cookies={"session_id": token})

    doc_id = uuid.uuid4()
    # Notice: do NOT create file on disk
    doc = Document(
        id=doc_id,
        user_id=cust.id,
        document_type="IDENTITY",
        file_url=f"documents/{doc_id}/lost.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    res = client.get(f"/api/documents/{doc_id}/content")
    assert res.status_code == 404
    assert "re-upload" in res.json()["detail"].lower()


def test_image_uploads_return_correct_mime_type(db_session):
    cust, token = create_user(db_session, "media_user")
    client = TestClient(app, cookies={"session_id": token})

    # PNG test
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    upload_png = client.post(
        "/api/documents/",
        data={"document_type": "PHOTO"},
        files={"file": ("applicant_photo.png", io.BytesIO(png_bytes), "image/png")}
    )
    assert upload_png.status_code == 200
    png_id = upload_png.json()["id"]

    res_png = client.get(f"/api/documents/{png_id}/content")
    assert res_png.status_code == 200
    assert res_png.headers["content-type"] == "image/png"
    assert res_png.content == png_bytes

    # JPEG test
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
    upload_jpg = client.post(
        "/api/documents/",
        data={"document_type": "PHOTO"},
        files={"file": ("signature.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    )
    assert upload_jpg.status_code == 200
    jpg_id = upload_jpg.json()["id"]

    res_jpg = client.get(f"/api/documents/{jpg_id}/content")
    assert res_jpg.status_code == 200
    assert res_jpg.headers["content-type"] == "image/jpeg"
    assert res_jpg.content == jpeg_bytes


def test_filename_sanitization_prevents_path_traversal():
    # Verify sanitizer extracts safe basename and strips directory traversals
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\win.ini") == "win.ini"
    assert sanitize_filename("/absolute/path/doc.pdf") == "doc.pdf"
    assert sanitize_filename("C:\\users\\admin\\test.pdf") == "test.pdf"
    assert sanitize_filename("normal_file.pdf") == "normal_file.pdf"
