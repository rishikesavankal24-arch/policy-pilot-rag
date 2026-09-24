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
    EmployeeRequestStatus,
    ApplicationAuditEvent,
    Notification
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
            apps = db.query(Application).filter(Application.user_id == user.id).all()
            for a in apps:
                db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.application_id == a.id).delete()
            db.query(ApplicationAuditEvent).filter(ApplicationAuditEvent.user_id == user.id).delete()
            db.query(Document).filter(Document.reviewed_by == user.id).update({Document.reviewed_by: None})
            db.query(Document).filter(Document.user_id == user.id).delete()
            db.query(Application).filter(Application.user_id == user.id).delete()
            db.query(EmployeeRequest).filter(EmployeeRequest.user_id == user.id).delete()
            db.query(Notification).filter(Notification.user_id == user.id).delete()
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


def test_document_replacement_serves_new_content(db_session):
    """
    M05.4 E2E replacement test:
    1. Customer uploads PDF A (ORIGINAL DOCUMENT -- TEST A).
    2. Employee views PDF A.
    3. Employee marks document as REQUIRES_REUPLOAD.
    4. Customer replaces document with PDF B (REPLACEMENT DOCUMENT -- TEST B).
    5. Assert same Document.id, status=UPLOADED, review_notes reset.
    6. Assert physical file storage updated and old file cleaned up.
    7. Employee GET /api/documents/{doc_id}/content MUST return PDF B bytes, NOT PDF A.
    8. Assert anti-cache headers are returned.
    9. Assert DOCUMENT_REPLACED audit event is logged.
    10. Assert unauthorized access is blocked (403).
    """
    cust, cust_token = create_user(db_session, "rep_cust")
    emp, emp_token = make_verified_employee(db_session, "rep_emp")
    other_cust, other_cust_token = create_user(db_session, "other_cust")

    cust_client = TestClient(app, cookies={"session_id": cust_token})
    emp_client = TestClient(app, cookies={"session_id": emp_token})
    other_client = TestClient(app, cookies={"session_id": other_cust_token})

    # Create application
    app_record = Application(
        id=uuid.uuid4(),
        user_id=cust.id,
        loan_type="Home Loan",
        requested_amount=5000000.0,
        tenure=240,
        purpose="Purchase apartment",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(app_record)
    db_session.commit()

    # Distinct byte payloads
    pdf_a_bytes = b"%PDF-1.4\nORIGINAL DOCUMENT -- TEST A\n%%EOF"
    pdf_b_bytes = b"%PDF-1.4\nREPLACEMENT DOCUMENT -- TEST B\n%%EOF"

    # 1. Customer uploads PDF A
    upload_res = cust_client.post(
        "/api/documents/",
        data={
            "document_type": "INCOME_PROOF",
            "application_id": str(app_record.id)
        },
        files={"file": ("original_income.pdf", io.BytesIO(pdf_a_bytes), "application/pdf")}
    )
    assert upload_res.status_code == 200, upload_res.text
    doc_id = upload_res.json()["id"]

    # 2. Employee views PDF A
    view_res_1 = emp_client.get(f"/api/documents/{doc_id}/content")
    assert view_res_1.status_code == 200
    assert view_res_1.content == pdf_a_bytes
    assert "no-cache" in view_res_1.headers.get("cache-control", "").lower()

    # 3. Employee marks document as REQUIRES_REUPLOAD
    review_res = emp_client.post(
        f"/api/employee/documents/{doc_id}/review",
        json={"status": "REQUIRES_REUPLOAD", "reason": "Blurry salary slip. Please upload clear copy."}
    )
    assert review_res.status_code == 200

    doc_in_db = db_session.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()
    assert doc_in_db.status == DocumentStatus.REQUIRES_REUPLOAD.value
    assert doc_in_db.review_notes == "Blurry salary slip. Please upload clear copy."

    # 4. Customer uploads replacement PDF B
    replace_res = cust_client.post(
        "/api/documents/",
        data={
            "document_type": "INCOME_PROOF",
            "application_id": str(app_record.id),
            "replaces_document_id": doc_id
        },
        files={"file": ("replacement_income.pdf", io.BytesIO(pdf_b_bytes), "application/pdf")}
    )
    assert replace_res.status_code == 200, replace_res.text
    rep_data = replace_res.json()

    # 5. Assert same Document.id
    assert rep_data["id"] == doc_id

    # 6. Assert DB state after replacement
    db_session.refresh(doc_in_db)
    assert str(doc_in_db.id) == doc_id
    assert doc_in_db.status == DocumentStatus.UPLOADED.value
    assert doc_in_db.review_notes is None
    assert doc_in_db.reviewed_by is None
    assert doc_in_db.reviewed_at is None
    assert doc_in_db.file_url == f"documents/{doc_id}/replacement_income.pdf"

    # 7. Assert physical storage updated
    stored_file = STORAGE_DIR / doc_id / "replacement_income.pdf"
    assert stored_file.exists(), f"Expected {stored_file} to exist on disk"
    assert stored_file.read_bytes() == pdf_b_bytes

    # Old file should have been cleaned up
    old_file = STORAGE_DIR / doc_id / "original_income.pdf"
    assert not old_file.exists(), f"Old file {old_file} should have been unlinked"

    # 8. Employee calls GET /api/documents/{doc_id}/content
    view_res_2 = emp_client.get(f"/api/documents/{doc_id}/content")
    assert view_res_2.status_code == 200
    assert view_res_2.content == pdf_b_bytes, "Content endpoint must return the replacement PDF bytes"
    assert view_res_2.content != pdf_a_bytes, "Content endpoint MUST NOT return the original PDF bytes"
    assert "no-cache" in view_res_2.headers.get("cache-control", "").lower()
    assert view_res_2.headers.get("pragma") == "no-cache"

    # 9. Assert DOCUMENT_REPLACED audit event exists
    audit = db_session.query(ApplicationAuditEvent).filter(
        ApplicationAuditEvent.application_id == app_record.id,
        ApplicationAuditEvent.event_type == "DOCUMENT_REPLACED"
    ).first()
    assert audit is not None
    assert "income" in audit.description.lower()

    # 10. Security assertion: other customer cannot access this document
    unauth_res = other_client.get(f"/api/documents/{doc_id}/content")
    assert unauth_res.status_code == 403

    # 11. Assert exactly 1 document record exists for this application (no duplicate row created)
    doc_count = db_session.query(Document).filter(Document.application_id == app_record.id).count()
    assert doc_count == 1


def test_invalid_document_replacement_attempts(db_session):
    """
    Verify rejection of invalid document replacement attempts:
    - wrong document ID (404)
    - document belonging to another customer (403)
    - document belonging to another application (400)
    - document not in REQUIRES_REUPLOAD state (400)
    """
    cust1, cust1_token = create_user(db_session, "inv_c1")
    cust2, cust2_token = create_user(db_session, "inv_c2")
    emp, emp_token = make_verified_employee(db_session, "inv_emp")

    c1_client = TestClient(app, cookies={"session_id": cust1_token})
    c2_client = TestClient(app, cookies={"session_id": cust2_token})
    emp_client = TestClient(app, cookies={"session_id": emp_token})

    # App 1 for Cust 1
    app1 = Application(
        id=uuid.uuid4(),
        user_id=cust1.id,
        loan_type="Personal Loan",
        requested_amount=100000.0,
        tenure=12,
        purpose="Medical expense",
        status=ApplicationStatus.SUBMITTED.value
    )
    # App 2 for Cust 1
    app2 = Application(
        id=uuid.uuid4(),
        user_id=cust1.id,
        loan_type="Personal Loan",
        requested_amount=200000.0,
        tenure=24,
        purpose="Travel",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add_all([app1, app2])
    db_session.commit()

    # Upload document for App 1
    up_res = c1_client.post(
        "/api/documents/",
        data={"document_type": "ID_PROOF", "application_id": str(app1.id)},
        files={"file": ("aadhaar.pdf", io.BytesIO(b"%PDF-1.4\noriginal\n%%EOF"), "application/pdf")}
    )
    assert up_res.status_code == 200
    doc1_id = up_res.json()["id"]

    dummy_pdf = io.BytesIO(b"%PDF-1.4\nreplacement attempt\n%%EOF")

    # Attempt 1: Non-existent document ID -> 404
    non_existent_id = str(uuid.uuid4())
    res_404 = c1_client.post(
        "/api/documents/",
        data={"document_type": "ID_PROOF", "application_id": str(app1.id), "replaces_document_id": non_existent_id},
        files={"file": ("rep.pdf", io.BytesIO(b"%PDF-1.4\nrep\n%%EOF"), "application/pdf")}
    )
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()

    # Attempt 2: Document is in UPLOADED status, NOT REQUIRES_REUPLOAD -> 400
    res_not_deficient = c1_client.post(
        "/api/documents/",
        data={"document_type": "ID_PROOF", "application_id": str(app1.id), "replaces_document_id": doc1_id},
        files={"file": ("rep.pdf", io.BytesIO(b"%PDF-1.4\nrep\n%%EOF"), "application/pdf")}
    )
    assert res_not_deficient.status_code == 400
    assert "only documents requiring re-upload" in res_not_deficient.json()["detail"].lower()

    # Now mark doc1 as REQUIRES_REUPLOAD
    rev_res = emp_client.post(
        f"/api/employee/documents/{doc1_id}/review",
        json={"status": "REQUIRES_REUPLOAD", "reason": "Unreadable"}
    )
    assert rev_res.status_code == 200

    # App for Cust 2
    app_c2 = Application(
        id=uuid.uuid4(),
        user_id=cust2.id,
        loan_type="Personal Loan",
        requested_amount=150000.0,
        tenure=12,
        purpose="Medical",
        status=ApplicationStatus.SUBMITTED.value
    )
    db_session.add(app_c2)
    db_session.commit()

    # Attempt 3: Another customer tries to replace Cust 1's document -> 403
    res_unauth = c2_client.post(
        "/api/documents/",
        data={"document_type": "ID_PROOF", "application_id": str(app_c2.id), "replaces_document_id": doc1_id},
        files={"file": ("rep.pdf", io.BytesIO(b"%PDF-1.4\nrep\n%%EOF"), "application/pdf")}
    )
    assert res_unauth.status_code == 403
    assert "cannot replace a document belonging to another user" in res_unauth.json()["detail"].lower()

    # Attempt 4: Cust 1 specifies wrong application_id (App 2 instead of App 1) -> 400
    res_wrong_app = c1_client.post(
        "/api/documents/",
        data={"document_type": "ID_PROOF", "application_id": str(app2.id), "replaces_document_id": doc1_id},
        files={"file": ("rep.pdf", io.BytesIO(b"%PDF-1.4\nrep\n%%EOF"), "application/pdf")}
    )
    assert res_wrong_app.status_code == 400
    assert "does not belong to the specified application" in res_wrong_app.json()["detail"].lower()


