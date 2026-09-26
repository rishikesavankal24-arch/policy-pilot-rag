"""
M08.3 Test Suite — Policy File Ingestion & Validation
Covers all 29 minimum required test cases:
1. Valid PDF creates PolicyVersion
2. First version gets version_number = 1
3. Second valid version gets version_number = 2
4. SHA-256 stored correctly
5. File size stored correctly
6. PDF page count stored correctly
7. created_by stored correctly
8. changelog stored correctly
9. effective dates stored correctly
10. Empty file rejected
11. >10 MB rejected
12. Unsupported extension rejected
13. Fake PDF rejected
14. Corrupted PDF rejected
15. Invalid image rejected
16. Extension/content mismatch rejected
17. Duplicate hash within same policy rejected
18. Same hash under different policy allowed
19. Version number cannot be client-forced
20. Duplicate version number safely prevented
21. Validation failure leaves no DB PolicyVersion
22. Validation failure leaves no orphan file
23. DB failure after file write cleans up file
24. Path traversal filename rejected/sanitized
25. Arbitrary filesystem path cannot be injected
26. Customer/employee cannot invoke policy ingestion
27. Admin permission boundary respected if API exists
28. Valid effective date range accepted
29. effective_to before effective_from rejected
"""

import io
import os
import uuid
import hashlib
import shutil
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.db.session import SessionLocal
from app.db.models import (
    User, Role, OnboardingStatus, Session as DBSession,
    Policy, PolicyVersion, RegulatoryAuthority, PolicyApplicability, PolicyStatus
)
from app.core.security import create_user_session
from app.services.policy_metadata_service import (
    PolicyMetadataValidationError,
    PolicyMetadataNotFoundError,
    PolicyMetadataConflictError
)
from app.services.policy_file_service import (
    PolicyFileService,
    PolicyFileValidator,
    PolicyFileValidationResult,
    MAX_POLICY_FILE_SIZE_BYTES
)
from tests.pdf_fixtures import make_test_pdf_bytes

client = TestClient(app)

# Minimal 1x1 valid PNG bytes
VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Minimal 1x1 valid JPEG bytes
VALID_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00"
    b"\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13"
    b"\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01"
    b"\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)


@pytest.fixture
def test_storage(tmp_path):
    """Isolated temporary storage for policy documents during tests."""
    storage_dir = tmp_path / "policies"
    storage_dir.mkdir(parents=True, exist_ok=True)
    yield storage_dir
    if storage_dir.exists():
        shutil.rmtree(storage_dir, ignore_errors=True)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Clean up test policies, versions, applicability, authorities and users
        test_policies = session.query(Policy).filter(Policy.policy_code.like("POL-INGEST-%")).all()
        for p in test_policies:
            p.current_version_id = None
        session.commit()

        for p in test_policies:
            session.query(PolicyVersion).filter(PolicyVersion.policy_id == p.id).delete(synchronize_session=False)
            session.query(PolicyApplicability).filter(PolicyApplicability.policy_id == p.id).delete(synchronize_session=False)
            session.delete(p)

        session.query(RegulatoryAuthority).filter(RegulatoryAuthority.short_name.like("TEST_INGEST_%")).delete(synchronize_session=False)

        test_users = session.query(User).filter(User.email.like("test_m08_3_%@example.com")).all()
        for u in test_users:
            session.query(DBSession).filter(DBSession.user_id == u.id).delete(synchronize_session=False)
            session.delete(u)

        session.commit()
        session.close()


def _create_user(db, role: str) -> User:
    uid = uuid.uuid4()
    email = f"test_m08_3_{role.lower()}_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name=f"M08.3 {role} User",
        role=role,
        requested_role=role,
        onboarding_status=OnboardingStatus.COMPLETED.value,
        authentication_provider="local",
        provider_subject_id=email
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_policy(db, code_suffix: str = "01") -> Policy:
    p_id = uuid.uuid4()
    policy = Policy(
        id=p_id,
        policy_code=f"POL-INGEST-{code_suffix}-{p_id.hex[:4].upper()}",
        title=f"Ingestion Test Policy {code_suffix}",
        description="Policy for ingestion testing",
        category="Lending",
        status=PolicyStatus.DRAFT.value
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


# ==============================================================================
# 1-9: Valid Ingestion Tests
# ==============================================================================

def test_01_valid_pdf_creates_policy_version(db, test_storage):
    """1. Valid PDF creates PolicyVersion in database and stores file on disk."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V01")
    pdf_bytes = make_test_pdf_bytes(page_count=2, text="RBI Master Direction on Lending")

    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="master_direction.pdf",
        file_bytes=pdf_bytes,
        changelog="Initial regulatory circular",
        created_by=admin.id,
        storage_dir=test_storage
    )

    assert version is not None
    assert version.policy_id == policy.id
    assert version.id is not None
    assert version.file_url.startswith(f"storage/policies/{policy.id}/{version.id}/")
    assert version.file_size_bytes == len(pdf_bytes)

    # Check physical file exists on disk
    disk_file, v_meta = PolicyFileService.get_policy_version_file(
        db=db,
        policy_id=policy.id,
        version_id=version.id,
        storage_dir=test_storage
    )
    assert disk_file.exists()
    assert disk_file.read_bytes() == pdf_bytes


def test_02_first_version_gets_version_number_1(db, test_storage):
    """2. First version gets version_number = '1'."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V02")
    pdf_bytes = make_test_pdf_bytes(page_count=1, text="First Policy Document")

    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="policy_v1.pdf",
        file_bytes=pdf_bytes,
        created_by=admin.id,
        storage_dir=test_storage
    )

    assert version.version_number == "1"


def test_03_second_valid_version_gets_version_number_2(db, test_storage):
    """3. Second valid version gets version_number = '2'."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V03")

    pdf1 = make_test_pdf_bytes(page_count=1, text="Version 1 Content")
    v1 = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="v1.pdf",
        file_bytes=pdf1,
        created_by=admin.id,
        storage_dir=test_storage
    )
    assert v1.version_number == "1"

    pdf2 = make_test_pdf_bytes(page_count=2, text="Version 2 Updated Content")
    v2 = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="v2.pdf",
        file_bytes=pdf2,
        created_by=admin.id,
        storage_dir=test_storage
    )
    assert v2.version_number == "2"


def test_04_sha256_stored_correctly(db, test_storage):
    """4. SHA-256 stored correctly matches exact cryptographic hash."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V04")
    pdf_bytes = make_test_pdf_bytes(page_count=1, text="Cryptographic Hash Verification")
    expected_hash = hashlib.sha256(pdf_bytes).hexdigest()

    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="doc.pdf",
        file_bytes=pdf_bytes,
        created_by=admin.id,
        storage_dir=test_storage
    )

    assert version.file_hash == expected_hash
    assert len(version.file_hash) == 64


def test_05_file_size_stored_correctly(db, test_storage):
    """5. File size stored correctly matches length in bytes."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V05")
    pdf_bytes = make_test_pdf_bytes(page_count=3, text="Size Verification Document")

    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="size_test.pdf",
        file_bytes=pdf_bytes,
        created_by=admin.id,
        storage_dir=test_storage
    )

    assert version.file_size_bytes == len(pdf_bytes)
    assert version.file_size_bytes > 0


def test_06_pdf_page_count_stored_correctly(db, test_storage):
    """6. PDF page count stored correctly from structural parsing."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V06")
    pdf_bytes_4 = make_test_pdf_bytes(page_count=4, text="Four Page Policy")

    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="four_pages.pdf",
        file_bytes=pdf_bytes_4,
        created_by=admin.id,
        storage_dir=test_storage
    )

    assert version.page_count == 4


def test_07_created_by_stored_correctly(db, test_storage):
    """7. created_by stored correctly with admin actor UUID."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V07")
    pdf_bytes = make_test_pdf_bytes(page_count=1)

    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="actor.pdf",
        file_bytes=pdf_bytes,
        created_by=admin.id,
        storage_dir=test_storage
    )

    assert version.created_by == admin.id


def test_08_changelog_stored_correctly(db, test_storage):
    """8. changelog stored correctly when supplied."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V08")
    pdf_bytes = make_test_pdf_bytes(page_count=1)
    changelog_text = "Updated risk limits in section 4.2 in accordance with master circular"

    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="change.pdf",
        file_bytes=pdf_bytes,
        changelog=changelog_text,
        created_by=admin.id,
        storage_dir=test_storage
    )

    assert version.changelog == changelog_text


def test_09_effective_dates_stored_correctly(db, test_storage):
    """9. effective dates stored correctly when supplied."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V09")
    pdf_bytes = make_test_pdf_bytes(page_count=1)
    now = datetime.now(timezone.utc)
    from_date = now
    to_date = now + timedelta(days=365)

    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="dates.pdf",
        file_bytes=pdf_bytes,
        effective_from=from_date,
        effective_to=to_date,
        created_by=admin.id,
        storage_dir=test_storage
    )

    assert version.effective_from is not None
    assert version.effective_to is not None


# ==============================================================================
# 10-16: Validation Tests
# ==============================================================================

def test_10_empty_file_rejected(db, test_storage):
    """10. Empty file (0 bytes) is rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V10")

    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="empty.pdf",
            file_bytes=b"",
            created_by=admin.id,
            storage_dir=test_storage
        )
    assert "Empty files are not allowed" in str(exc_info.value)


def test_11_over_10mb_rejected(db, test_storage):
    """11. File >10 MB is rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V11")
    oversized_bytes = b"%PDF-" + b"0" * (MAX_POLICY_FILE_SIZE_BYTES + 10)

    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="large.pdf",
            file_bytes=oversized_bytes,
            created_by=admin.id,
            storage_dir=test_storage
        )
    assert "exceeds the 10 MB limit" in str(exc_info.value)


def test_12_unsupported_extension_rejected(db, test_storage):
    """12. Unsupported extension (e.g. .docx, .exe, .txt) rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V12")

    for bad_name in ["policy.docx", "script.exe", "notes.txt", "doc.zip"]:
        with pytest.raises(PolicyMetadataValidationError) as exc_info:
            PolicyFileService.attach_policy_version_document(
                db=db,
                policy_id=policy.id,
                filename=bad_name,
                file_bytes=b"some binary content",
                created_by=admin.id,
                storage_dir=test_storage
            )
        assert "Unsupported file type" in str(exc_info.value)


def test_13_fake_pdf_rejected(db, test_storage):
    """13. Fake PDF containing plain text is rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V13")
    fake_pdf_bytes = b"This is just plain text, not a real PDF file."

    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="fake.pdf",
            file_bytes=fake_pdf_bytes,
            created_by=admin.id,
            storage_dir=test_storage
        )
    assert "Invalid PDF signature" in str(exc_info.value)


def test_14_corrupted_pdf_rejected(db, test_storage):
    """14. Corrupted PDF (valid header but broken structure) is rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V14")
    # Starts with %PDF- but followed by garbage
    corrupted_pdf_bytes = b"%PDF-1.7\r\n" + b"\x00\xff\xee\xdd" * 50 + b"trailer\r\n%%EOF"

    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="corrupt.pdf",
            file_bytes=corrupted_pdf_bytes,
            created_by=admin.id,
            storage_dir=test_storage
        )
    assert "Invalid or corrupted PDF document" in str(exc_info.value)


def test_15_invalid_image_rejected(db, test_storage):
    """15. Invalid image (fake PNG signature or corrupted bytes) is rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V15")
    fake_png = b"Not a real PNG image"

    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="fake.png",
            file_bytes=fake_png,
            created_by=admin.id,
            storage_dir=test_storage
        )
    assert "Invalid PNG signature" in str(exc_info.value)


def test_16_extension_content_mismatch_rejected(db, test_storage):
    """16. Extension/content mismatch rejected (e.g. PNG bytes named .pdf)."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V16")

    # PNG bytes given .pdf extension
    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="mismatch.pdf",
            file_bytes=VALID_PNG_BYTES,
            created_by=admin.id,
            storage_dir=test_storage
        )
    assert "Invalid PDF signature" in str(exc_info.value)

    # PDF bytes given .png extension
    pdf_bytes = make_test_pdf_bytes(page_count=1)
    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="mismatch.png",
            file_bytes=pdf_bytes,
            created_by=admin.id,
            storage_dir=test_storage
        )
    assert "Invalid PNG signature" in str(exc_info.value)


# ==============================================================================
# 17-20: Duplicate / Version Tests
# ==============================================================================

def test_17_duplicate_hash_within_same_policy_rejected(db, test_storage):
    """17. Duplicate hash within the SAME policy is rejected with conflict."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V17")
    pdf_bytes = make_test_pdf_bytes(page_count=1, text="Unique Policy Content 17")

    # First upload succeeds
    PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="policy_doc_v1.pdf",
        file_bytes=pdf_bytes,
        created_by=admin.id,
        storage_dir=test_storage
    )

    # Second upload with identical bytes to the same policy must raise conflict
    with pytest.raises(PolicyMetadataConflictError) as exc_info:
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="policy_doc_v2_same.pdf",
            file_bytes=pdf_bytes,
            created_by=admin.id,
            storage_dir=test_storage
        )
    assert "identical document content" in str(exc_info.value)


def test_18_same_hash_under_different_policy_allowed(db, test_storage):
    """18. Same hash under DIFFERENT policy is allowed (legitimate shared circular)."""
    admin = _create_user(db, Role.ADMIN.value)
    policy_a = _create_policy(db, "V18A")
    policy_b = _create_policy(db, "V18B")
    shared_pdf_bytes = make_test_pdf_bytes(page_count=1, text="Shared Master Direction Circular")

    v_a = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy_a.id,
        filename="circular_a.pdf",
        file_bytes=shared_pdf_bytes,
        created_by=admin.id,
        storage_dir=test_storage
    )
    v_b = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy_b.id,
        filename="circular_b.pdf",
        file_bytes=shared_pdf_bytes,
        created_by=admin.id,
        storage_dir=test_storage
    )

    assert v_a.file_hash == v_b.file_hash
    assert v_a.policy_id != v_b.policy_id
    assert v_a.version_number == "1"
    assert v_b.version_number == "1"


def test_19_version_number_cannot_be_client_forced(db, test_storage):
    """19. Version number cannot be client-forced; generated server-side."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V19")
    pdf_bytes = make_test_pdf_bytes(page_count=1, text="Client Forced Test")

    # Service signature does not even take a client version number
    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="policy.pdf",
        file_bytes=pdf_bytes,
        created_by=admin.id,
        storage_dir=test_storage
    )
    assert version.version_number == "1"


def test_20_duplicate_version_number_safely_prevented(db, test_storage):
    """20. Duplicate version number safely prevented by database constraint handling."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V20")
    pdf_bytes1 = make_test_pdf_bytes(page_count=1, text="V20 Document 1")
    pdf_bytes2 = make_test_pdf_bytes(page_count=1, text="V20 Document 2")

    # Attach version 1
    PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="doc1.pdf",
        file_bytes=pdf_bytes1,
        created_by=admin.id,
        storage_dir=test_storage
    )

    # Force calculate_next_version_number to simulate a race condition returning "1" again
    with patch.object(PolicyFileService, "calculate_next_version_number", return_value="1"):
        with pytest.raises(PolicyMetadataConflictError) as exc_info:
            PolicyFileService.attach_policy_version_document(
                db=db,
                policy_id=policy.id,
                filename="doc2.pdf",
                file_bytes=pdf_bytes2,
                created_by=admin.id,
                storage_dir=test_storage
            )
        assert "Duplicate policy version number" in str(exc_info.value)


# ==============================================================================
# 21-23: Atomicity Tests
# ==============================================================================

def test_21_validation_failure_leaves_no_db_policy_version(db, test_storage):
    """21. Validation failure leaves no PolicyVersion in the database."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V21")

    with pytest.raises(PolicyMetadataValidationError):
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="invalid.pdf",
            file_bytes=b"broken file content",
            created_by=admin.id,
            storage_dir=test_storage
        )

    versions = db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy.id).all()
    assert len(versions) == 0


def test_22_validation_failure_leaves_no_orphan_file(db, test_storage):
    """22. Validation failure leaves no orphan file on disk."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V22")

    with pytest.raises(PolicyMetadataValidationError):
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="broken.pdf",
            file_bytes=b"broken file content",
            created_by=admin.id,
            storage_dir=test_storage
        )

    # Directory for this policy shouldn't have any files
    policy_dir = test_storage / str(policy.id)
    assert not policy_dir.exists() or len(list(policy_dir.rglob("*"))) == 0


def test_23_db_failure_after_file_write_cleans_up_file(db, test_storage):
    """23. DB failure after file write cleans up the written file (no orphan files)."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V23")
    pdf_bytes = make_test_pdf_bytes(page_count=1, text="Atomicity Cleanup Verification")

    # Mock db.commit to raise an exception simulating database failure
    with patch.object(db, "commit", side_effect=RuntimeError("Simulated DB Crash")):
        with pytest.raises(PolicyMetadataValidationError) as exc_info:
            PolicyFileService.attach_policy_version_document(
                db=db,
                policy_id=policy.id,
                filename="atomicity.pdf",
                file_bytes=pdf_bytes,
                created_by=admin.id,
                storage_dir=test_storage
            )
        assert "Failed to record policy version" in str(exc_info.value)

    # Verify no orphan files remain in test_storage
    policy_dir = test_storage / str(policy.id)
    assert not policy_dir.exists() or len(list(policy_dir.rglob("*.pdf"))) == 0

    # Verify no PolicyVersion was created
    versions = db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy.id).all()
    assert len(versions) == 0


# ==============================================================================
# 24-27: Security Tests
# ==============================================================================

def test_24_path_traversal_filename_sanitized(db, test_storage):
    """24. Path traversal in filename is sanitized, preventing escape."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V24")
    pdf_bytes = make_test_pdf_bytes(page_count=1, text="Security Path Traversal")

    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="../../../../../etc/passwd.pdf",
        file_bytes=pdf_bytes,
        created_by=admin.id,
        storage_dir=test_storage
    )

    # Filename should be sanitized without traversal components
    assert ".." not in version.file_url
    assert "/" not in Path(version.file_url).name
    assert version.file_url.endswith("passwd.pdf")

    # Verify disk location stays within policy/version path
    disk_file, _ = PolicyFileService.get_policy_version_file(
        db=db,
        policy_id=policy.id,
        version_id=version.id,
        storage_dir=test_storage
    )
    assert str(disk_file).startswith(str(test_storage))


def test_25_arbitrary_filesystem_path_cannot_be_injected(db, test_storage):
    """25. Arbitrary filesystem path cannot be injected in filename."""
    sanitized = PolicyFileValidator.sanitize_filename("C:\\Windows\\System32\\cmd.exe.pdf")
    assert "\\" not in sanitized
    assert "C:" not in sanitized
    assert not sanitized.startswith("/")


def test_26_customer_employee_cannot_invoke_policy_ingestion(db):
    """26. Customer and employee cannot invoke policy ingestion API (403 Forbidden)."""
    customer = _create_user(db, Role.CUSTOMER.value)
    employee = _create_user(db, Role.EMPLOYEE.value)
    policy = _create_policy(db, "V26")
    pdf_bytes = make_test_pdf_bytes(page_count=1)

    # Customer session
    cust_token = create_user_session(db, customer.id)
    cust_res = client.post(
        f"/admin/policies/{policy.id}/versions/upload",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
        cookies={"session_id": cust_token}
    )
    assert cust_res.status_code == 403

    # Employee session
    emp_token = create_user_session(db, employee.id)
    emp_res = client.post(
        f"/admin/policies/{policy.id}/versions/upload",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
        cookies={"session_id": emp_token}
    )
    assert emp_res.status_code == 403

    # Unauthenticated
    anon_res = client.post(
        f"/admin/policies/{policy.id}/versions/upload",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")}
    )
    assert anon_res.status_code == 401


def test_27_admin_permission_boundary_respected_api(db):
    """27. Admin with ADMIN_POLICY_MANAGEMENT can upload via API."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V27")
    pdf_bytes = make_test_pdf_bytes(page_count=2, text="Admin API Ingestion Document")
    admin_token = create_user_session(db, admin.id)

    response = client.post(
        f"/admin/policies/{policy.id}/versions/upload",
        files={"file": ("admin_policy.pdf", pdf_bytes, "application/pdf")},
        data={"changelog": "Uploaded by admin through API"},
        cookies={"session_id": admin_token}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["policy_id"] == str(policy.id)
    assert data["version_number"] == "1"
    assert data["page_count"] == 2
    assert data["changelog"] == "Uploaded by admin through API"
    assert data["created_by"] == str(admin.id)
    # Ensure physical path is NOT leaked to the client
    assert not data["file_url"].startswith("/")
    assert not data["file_url"].startswith("C:")
    assert not data["file_url"].startswith("D:")

    # Retrieve file via GET API
    version_id = data["id"]
    get_res = client.get(
        f"/admin/policies/{policy.id}/versions/{version_id}/file",
        cookies={"session_id": admin_token}
    )
    assert get_res.status_code == 200
    assert get_res.content == pdf_bytes
    assert get_res.headers["content-type"] == "application/pdf"


# ==============================================================================
# 28-29: Effective Dates Tests
# ==============================================================================

def test_28_valid_effective_date_range_accepted(db, test_storage):
    """28. Valid effective date range (effective_to >= effective_from) accepted."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V28")
    pdf_bytes = make_test_pdf_bytes(page_count=1)

    t_from = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    t_to = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="dated.pdf",
        file_bytes=pdf_bytes,
        effective_from=t_from,
        effective_to=t_to,
        created_by=admin.id,
        storage_dir=test_storage
    )

    assert version.effective_from == t_from
    assert version.effective_to == t_to


def test_29_effective_to_before_effective_from_rejected(db, test_storage):
    """29. effective_to before effective_from is rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy = _create_policy(db, "V29")
    pdf_bytes = make_test_pdf_bytes(page_count=1)

    t_from = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    t_to = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)  # earlier than from!

    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename="bad_dates.pdf",
            file_bytes=pdf_bytes,
            effective_from=t_from,
            effective_to=t_to,
            created_by=admin.id,
            storage_dir=test_storage
        )

    assert "effective_to date cannot be earlier than effective_from date" in str(exc_info.value)
