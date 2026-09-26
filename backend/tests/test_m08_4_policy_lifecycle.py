"""
M08.4 Test Suite — Policy Lifecycle State Machine & Versioning
Covers all 42 required test scenarios:
- Transition tests (1-12)
- Publishing validation (13-16)
- Activation (17-20)
- Version history (21-23)
- Immutability (24-27)
- Superseding (28-32)
- Archiving (33-35)
- Consistency (36-38)
- Authorization (39-42)
"""

import uuid
import shutil
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.models import (
    User, Role, OnboardingStatus, Session as DBSession,
    Policy, PolicyVersion, PolicyStatus
)
from app.core.security import create_user_session
from app.services.policy_lifecycle_service import (
    PolicyLifecycleService,
    PolicyLifecycleValidationError,
    PolicyLifecycleNotFoundError,
    PolicyLifecycleConflictError
)
from app.services.policy_file_service import PolicyFileService
from tests.pdf_fixtures import make_test_pdf_bytes

client = TestClient(app)


@pytest.fixture
def test_storage(tmp_path):
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
        test_policies = session.query(Policy).filter(Policy.policy_code.like("POL-LC-%")).all()
        for p in test_policies:
            p.current_version_id = None
        session.commit()

        for p in test_policies:
            session.query(PolicyVersion).filter(PolicyVersion.policy_id == p.id).delete(synchronize_session=False)
            session.delete(p)

        test_users = session.query(User).filter(User.email.like("test_m08_4_%@example.com")).all()
        for u in test_users:
            session.query(DBSession).filter(DBSession.user_id == u.id).delete(synchronize_session=False)
            session.delete(u)

        session.commit()
        session.close()


def _create_user(db, role: str) -> User:
    uid = uuid.uuid4()
    email = f"test_m08_4_{role.lower()}_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name=f"M08.4 {role} User",
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


def _create_policy_with_version(
    db,
    storage_dir,
    suffix: str = "01",
    effective_from: datetime = None,
    effective_to: datetime = None
) -> tuple[Policy, PolicyVersion]:
    p_id = uuid.uuid4()
    policy = Policy(
        id=p_id,
        policy_code=f"POL-LC-{suffix}-{p_id.hex[:4].upper()}",
        title=f"Lifecycle Test Policy {suffix}",
        description="Policy for lifecycle testing",
        category="Lending",
        status=PolicyStatus.DRAFT
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    now = datetime.now(timezone.utc)
    pdf_bytes = make_test_pdf_bytes(page_count=1, text=f"Lifecycle Doc {suffix}")
    version = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename=f"doc_{suffix}.pdf",
        file_bytes=pdf_bytes,
        changelog=f"Initial version for {suffix}",
        effective_from=effective_from or now,
        effective_to=effective_to or (now + timedelta(days=365)),
        storage_dir=storage_dir
    )
    return policy, version


# ==============================================================================
# 1-12: Transition Tests
# ==============================================================================

def test_01_draft_to_published_succeeds(db, test_storage):
    """1. DRAFT -> PUBLISHED succeeds."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, _ = _create_policy_with_version(db, test_storage, "T01")

    published = PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    assert published.status == PolicyStatus.PUBLISHED


def test_02_published_to_active_succeeds(db, test_storage):
    """2. PUBLISHED -> ACTIVE succeeds."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T02")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)

    active = PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v.id, actor_id=admin.id)
    assert active.status == PolicyStatus.ACTIVE
    assert active.current_version_id == v.id


def test_03_active_to_superseded_succeeds(db, test_storage):
    """3. ACTIVE -> SUPERSEDED succeeds."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v1 = _create_policy_with_version(db, test_storage, "T03")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v1.id, actor_id=admin.id)

    # Attach v2
    now = datetime.now(timezone.utc)
    pdf2 = make_test_pdf_bytes(page_count=2, text="Version 2 Content")
    v2 = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="v2.pdf",
        file_bytes=pdf2,
        effective_from=now + timedelta(days=30),
        storage_dir=test_storage
    )

    superseded = PolicyLifecycleService.supersede_policy(db, policy.id, new_version_id=v2.id, actor_id=admin.id)
    assert superseded.status == PolicyStatus.SUPERSEDED
    assert superseded.current_version_id == v2.id


def test_04_superseded_to_archived_succeeds(db, test_storage):
    """4. SUPERSEDED -> ARCHIVED succeeds."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v1 = _create_policy_with_version(db, test_storage, "T04")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v1.id, actor_id=admin.id)

    pdf2 = make_test_pdf_bytes(page_count=1, text="V2")
    v2 = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="v2.pdf",
        file_bytes=pdf2,
        effective_from=datetime.now(timezone.utc) + timedelta(days=10),
        storage_dir=test_storage
    )
    PolicyLifecycleService.supersede_policy(db, policy.id, new_version_id=v2.id, actor_id=admin.id)

    archived = PolicyLifecycleService.archive_policy(db, policy.id, actor_id=admin.id)
    assert archived.status == PolicyStatus.ARCHIVED


def test_05_draft_to_archived_behavior(db, test_storage):
    """5. DRAFT -> ARCHIVED administrative archival succeeds."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, _ = _create_policy_with_version(db, test_storage, "T05")
    assert policy.status == PolicyStatus.DRAFT

    archived = PolicyLifecycleService.archive_policy(db, policy.id, actor_id=admin.id)
    assert archived.status == PolicyStatus.ARCHIVED


def test_06_draft_to_active_rejected(db, test_storage):
    """6. DRAFT -> ACTIVE rejected (must publish first)."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T06")

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v.id, actor_id=admin.id)
    assert "Invalid policy lifecycle transition" in str(exc.value)


def test_07_draft_to_superseded_rejected(db, test_storage):
    """7. DRAFT -> SUPERSEDED rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T07")

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.supersede_policy(db, policy.id, new_version_id=v.id, actor_id=admin.id)
    assert "Invalid policy lifecycle transition" in str(exc.value)


def test_08_published_to_draft_rejected(db, test_storage):
    """8. PUBLISHED -> DRAFT rejected (no backward transition)."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, _ = _create_policy_with_version(db, test_storage, "T08")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleValidationError):
        PolicyLifecycleService._verify_transition_allowed(policy.status, PolicyStatus.DRAFT)


def test_09_active_to_draft_rejected(db, test_storage):
    """9. ACTIVE -> DRAFT rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T09")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleValidationError):
        PolicyLifecycleService._verify_transition_allowed(policy.status, PolicyStatus.DRAFT)


def test_10_active_to_published_rejected(db, test_storage):
    """10. ACTIVE -> PUBLISHED rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T10")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    assert "Invalid policy lifecycle transition" in str(exc.value)


def test_11_archived_to_active_rejected(db, test_storage):
    """11. ARCHIVED -> ACTIVE rejected (archived is terminal)."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T11")
    PolicyLifecycleService.archive_policy(db, policy.id, actor_id=admin.id)
    assert policy.status == PolicyStatus.ARCHIVED

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v.id, actor_id=admin.id)
    assert "Invalid policy lifecycle transition" in str(exc.value)


def test_12_archived_to_published_rejected(db, test_storage):
    """12. ARCHIVED -> PUBLISHED rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, _ = _create_policy_with_version(db, test_storage, "T12")
    PolicyLifecycleService.archive_policy(db, policy.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    assert "Invalid policy lifecycle transition" in str(exc.value)


# ==============================================================================
# 13-16: Publishing Validation Tests
# ==============================================================================

def test_13_publish_without_policy_version_rejected(db):
    """13. Publish without PolicyVersion is rejected."""
    p_id = uuid.uuid4()
    policy = Policy(
        id=p_id,
        policy_code=f"POL-LC-NOVER-{p_id.hex[:4].upper()}",
        title="No Version Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(policy)
    db.commit()

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.publish_policy(db, policy.id)
    assert "at least one PolicyVersion" in str(exc.value)


def test_14_publish_incomplete_version_rejected(db):
    """14. Publish with incomplete version (missing file or 0 bytes) rejected."""
    p_id = uuid.uuid4()
    policy = Policy(
        id=p_id,
        policy_code=f"POL-LC-INCOMPLETE-{p_id.hex[:4].upper()}",
        title="Incomplete Version Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(policy)
    db.commit()

    # Incomplete version with no file_hash and 0 file_size_bytes
    v = PolicyVersion(
        id=uuid.uuid4(),
        policy_id=policy.id,
        version_number="1",
        file_hash=None,
        file_url=None,
        file_size_bytes=0
    )
    db.add(v)
    db.commit()

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.publish_policy(db, policy.id)
    assert "incomplete or missing source document" in str(exc.value)


def test_15_publish_valid_policy_succeeds(db, test_storage):
    """15. Publish valid policy with complete version succeeds."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T15")

    published = PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    assert published.status == PolicyStatus.PUBLISHED
    db.refresh(v)
    assert v.published_by == admin.id


def test_16_publishing_does_not_automatically_activate(db, test_storage):
    """16. Publishing does not automatically activate the policy."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, _ = _create_policy_with_version(db, test_storage, "T16")

    published = PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    assert published.status == PolicyStatus.PUBLISHED
    assert published.status != PolicyStatus.ACTIVE
    assert published.current_version_id is None


# ==============================================================================
# 17-20: Activation Tests
# ==============================================================================

def test_17_activate_valid_published_version(db, test_storage):
    """17. Activate valid published version succeeds."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T17")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)

    active = PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v.id, actor_id=admin.id)
    assert active.status == PolicyStatus.ACTIVE
    assert active.current_version_id == v.id


def test_18_activation_sets_current_version_id(db, test_storage):
    """18. Activation explicitly sets current_version_id on Policy."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T18")
    assert policy.current_version_id is None

    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    active = PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v.id, actor_id=admin.id)
    assert active.current_version_id == v.id


def test_19_activation_without_effective_from_rejected(db, test_storage):
    """19. Activation without effective_from date is rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    p_id = uuid.uuid4()
    policy = Policy(
        id=p_id,
        policy_code=f"POL-LC-NOFROM-{p_id.hex[:4].upper()}",
        title="No Effective From Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(policy)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=1)
    v = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="nofrom.pdf",
        file_bytes=pdf_bytes,
        effective_from=None,  # Intentionally missing
        storage_dir=test_storage
    )
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v.id, actor_id=admin.id)
    assert "without an effective_from date" in str(exc.value)


def test_20_activation_of_non_published_policy_rejected(db, test_storage):
    """20. Activation of non-published (e.g. DRAFT or ARCHIVED) policy is rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T20")
    assert policy.status == PolicyStatus.DRAFT

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v.id, actor_id=admin.id)
    assert "Invalid policy lifecycle transition" in str(exc.value)


# ==============================================================================
# 21-23: Version History Tests
# ==============================================================================

def test_21_version_history_ordered_descending(db, test_storage):
    """21. Version history is ordered by version_number DESC."""
    policy, _ = _create_policy_with_version(db, test_storage, "T21_1")

    # Add v2 and v3
    pdf2 = make_test_pdf_bytes(page_count=1, text="Version 2")
    pdf3 = make_test_pdf_bytes(page_count=1, text="Version 3")
    PolicyFileService.attach_policy_version_document(
        db=db, policy_id=policy.id, filename="v2.pdf", file_bytes=pdf2, storage_dir=test_storage
    )
    PolicyFileService.attach_policy_version_document(
        db=db, policy_id=policy.id, filename="v3.pdf", file_bytes=pdf3, storage_dir=test_storage
    )

    history = PolicyLifecycleService.get_policy_version_history(db, policy.id)
    assert len(history) == 3
    version_numbers = [item["version_number"] for item in history]
    assert version_numbers == ["3", "2", "1"]


def test_22_historical_versions_preserved(db, test_storage):
    """22. Historical versions are completely preserved in database."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v1 = _create_policy_with_version(db, test_storage, "T22")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v1.id, actor_id=admin.id)

    pdf2 = make_test_pdf_bytes(page_count=1, text="V2")
    v2 = PolicyFileService.attach_policy_version_document(
        db=db, policy_id=policy.id, filename="v2.pdf", file_bytes=pdf2,
        effective_from=datetime.now(timezone.utc) + timedelta(days=1), storage_dir=test_storage
    )
    PolicyLifecycleService.supersede_policy(db, policy.id, new_version_id=v2.id, actor_id=admin.id)

    all_versions = db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy.id).all()
    assert len(all_versions) == 2
    assert any(v.id == v1.id for v in all_versions)
    assert any(v.id == v2.id for v in all_versions)


def test_23_raw_filesystem_paths_not_exposed(db, test_storage):
    r"""23. Raw filesystem paths (e.g. C:\ or D:\) are not exposed in history."""
    policy, _ = _create_policy_with_version(db, test_storage, "T23")
    history = PolicyLifecycleService.get_policy_version_history(db, policy.id)

    for item in history:
        file_url = item["file_url"]
        assert not file_url.startswith("C:")
        assert not file_url.startswith("D:")
        assert not file_url.startswith("/")
        assert file_url.startswith("storage/policies/")


# ==============================================================================
# 24-27: Immutability Tests
# ==============================================================================

def test_24_historical_version_file_hash_cannot_be_changed(db, test_storage):
    """24. Historical version file_hash cannot be changed."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T24")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleConflictError) as exc:
        PolicyLifecycleService.update_policy_version_metadata(
            db=db,
            policy_id=policy.id,
            version_id=v.id,
            attempted_immutable_fields={"file_hash": "tampered_fake_hash_1234567890"}
        )
    assert "strictly immutable" in str(exc.value)


def test_25_version_number_cannot_be_changed(db, test_storage):
    """25. version_number cannot be modified."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T25")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleConflictError) as exc:
        PolicyLifecycleService.update_policy_version_metadata(
            db=db,
            policy_id=policy.id,
            version_id=v.id,
            attempted_immutable_fields={"version_number": "99"}
        )
    assert "strictly immutable" in str(exc.value)


def test_26_file_url_cannot_be_changed(db, test_storage):
    """26. file_url cannot be modified."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T26")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleConflictError) as exc:
        PolicyLifecycleService.update_policy_version_metadata(
            db=db,
            policy_id=policy.id,
            version_id=v.id,
            attempted_immutable_fields={"file_url": "malicious/path/fake.pdf"}
        )
    assert "strictly immutable" in str(exc.value)


def test_27_page_count_cannot_be_changed(db, test_storage):
    """27. page_count cannot be modified."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T27")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleConflictError) as exc:
        PolicyLifecycleService.update_policy_version_metadata(
            db=db,
            policy_id=policy.id,
            version_id=v.id,
            attempted_immutable_fields={"page_count": 999}
        )
    assert "strictly immutable" in str(exc.value)


# ==============================================================================
# 28-32: Superseding Tests
# ==============================================================================

def test_28_active_version_can_be_superseded(db, test_storage):
    """28. Active version can be superseded."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v1 = _create_policy_with_version(db, test_storage, "T28")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v1.id, actor_id=admin.id)

    pdf2 = make_test_pdf_bytes(page_count=2, text="V2")
    v2 = PolicyFileService.attach_policy_version_document(
        db=db, policy_id=policy.id, filename="v2.pdf", file_bytes=pdf2,
        effective_from=datetime.now(timezone.utc) + timedelta(days=1), storage_dir=test_storage
    )

    superseded = PolicyLifecycleService.supersede_policy(db, policy.id, new_version_id=v2.id, actor_id=admin.id)
    assert superseded.status == PolicyStatus.SUPERSEDED


def test_29_new_version_becomes_current(db, test_storage):
    """29. New version becomes current_version_id when superseded."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v1 = _create_policy_with_version(db, test_storage, "T29")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v1.id, actor_id=admin.id)

    pdf2 = make_test_pdf_bytes(page_count=2, text="V2")
    v2 = PolicyFileService.attach_policy_version_document(
        db=db, policy_id=policy.id, filename="v2.pdf", file_bytes=pdf2,
        effective_from=datetime.now(timezone.utc) + timedelta(days=1), storage_dir=test_storage
    )

    superseded = PolicyLifecycleService.supersede_policy(db, policy.id, new_version_id=v2.id, actor_id=admin.id)
    assert superseded.current_version_id == v2.id


def test_30_previous_version_preserved(db, test_storage):
    """30. Previous version preserved in DB after superseding."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v1 = _create_policy_with_version(db, test_storage, "T30")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v1.id, actor_id=admin.id)

    pdf2 = make_test_pdf_bytes(page_count=1, text="V2")
    v2 = PolicyFileService.attach_policy_version_document(
        db=db, policy_id=policy.id, filename="v2.pdf", file_bytes=pdf2,
        effective_from=datetime.now(timezone.utc) + timedelta(days=1), storage_dir=test_storage
    )
    PolicyLifecycleService.supersede_policy(db, policy.id, new_version_id=v2.id, actor_id=admin.id)

    v1_recheck = db.query(PolicyVersion).filter(PolicyVersion.id == v1.id).first()
    assert v1_recheck is not None
    assert v1_recheck.version_number == "1"


def test_31_invalid_new_version_rejected(db, test_storage):
    """31. Invalid new version (missing file or invalid dates) is rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v1 = _create_policy_with_version(db, test_storage, "T31")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v1.id, actor_id=admin.id)

    # Incomplete new version
    bad_v = PolicyVersion(
        id=uuid.uuid4(),
        policy_id=policy.id,
        version_number="2",
        file_hash=None,
        file_url=None,
        file_size_bytes=0,
        effective_from=None
    )
    db.add(bad_v)
    db.commit()

    with pytest.raises(PolicyLifecycleValidationError):
        PolicyLifecycleService.supersede_policy(db, policy.id, new_version_id=bad_v.id, actor_id=admin.id)


def test_32_superseding_without_new_version_rejected(db, test_storage):
    """32. Superseding without new version rejected."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v1 = _create_policy_with_version(db, test_storage, "T32")
    PolicyLifecycleService.publish_policy(db, policy.id, actor_id=admin.id)
    PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v1.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.supersede_policy(db, policy.id, new_version_id=None, actor_id=admin.id)
    assert "Superseding without new version rejected" in str(exc.value)


# ==============================================================================
# 33-35: Archiving Tests
# ==============================================================================

def test_33_archive_policy_succeeds_when_valid(db, test_storage):
    """33. Archive policy succeeds when valid (from SUPERSEDED or DRAFT)."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, _ = _create_policy_with_version(db, test_storage, "T33")
    archived = PolicyLifecycleService.archive_policy(db, policy.id, actor_id=admin.id)
    assert archived.status == PolicyStatus.ARCHIVED


def test_34_archived_policy_cannot_reactivate(db, test_storage):
    """34. Archived policy cannot reactivate."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v = _create_policy_with_version(db, test_storage, "T34")
    PolicyLifecycleService.archive_policy(db, policy.id, actor_id=admin.id)

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.activate_policy_version(db, policy.id, version_id=v.id, actor_id=admin.id)
    assert "Invalid policy lifecycle transition" in str(exc.value)


def test_35_archived_policy_history_preserved(db, test_storage):
    """35. Archived policy preserves all version history."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v1 = _create_policy_with_version(db, test_storage, "T35")
    PolicyLifecycleService.archive_policy(db, policy.id, actor_id=admin.id)

    history = PolicyLifecycleService.get_policy_version_history(db, policy.id)
    assert len(history) == 1
    assert history[0]["id"] == str(v1.id)


# ==============================================================================
# 36-38: Consistency Tests
# ==============================================================================

def test_36_active_without_current_version_rejected(db):
    """36. ACTIVE policy without current_version_id fails consistency check."""
    p_id = uuid.uuid4()
    policy = Policy(
        id=p_id,
        policy_code=f"POL-LC-INCON1-{p_id.hex[:4].upper()}",
        title="Inconsistent Active Policy",
        status=PolicyStatus.ACTIVE,
        current_version_id=None
    )
    db.add(policy)
    db.commit()

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.validate_policy_lifecycle_state(db, policy.id)
    assert "current_version_id is NULL" in str(exc.value)


def test_37_published_without_valid_version_rejected(db):
    """37. PUBLISHED policy without valid version fails consistency check."""
    p_id = uuid.uuid4()
    policy = Policy(
        id=p_id,
        policy_code=f"POL-LC-INCON2-{p_id.hex[:4].upper()}",
        title="Inconsistent Published Policy",
        status=PolicyStatus.PUBLISHED
    )
    db.add(policy)
    db.commit()

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.validate_policy_lifecycle_state(db, policy.id)
    assert "has no PolicyVersions" in str(exc.value)


def test_38_invalid_current_version_rejected(db, test_storage):
    """38. ACTIVE policy with invalid current_version_id (belonging to another policy) fails consistency check."""
    policy_a, v_a = _create_policy_with_version(db, test_storage, "T38A")

    p_id = uuid.uuid4()
    policy_b = Policy(
        id=p_id,
        policy_code=f"POL-LC-INCON3-{p_id.hex[:4].upper()}",
        title="Inconsistent Foreign Version",
        status=PolicyStatus.ACTIVE,
        current_version_id=v_a.id  # Belongs to policy_a, not policy_b
    )
    db.add(policy_b)
    db.commit()

    with pytest.raises(PolicyLifecycleValidationError) as exc:
        PolicyLifecycleService.validate_policy_lifecycle_state(db, policy_b.id)
    assert "does not exist" in str(exc.value)


# ==============================================================================
# 39-42: Authorization Tests
# ==============================================================================

def test_39_customer_cannot_perform_lifecycle_operation(db, test_storage):
    """39. Customer cannot perform lifecycle operation (403 Forbidden)."""
    customer = _create_user(db, Role.CUSTOMER.value)
    policy, _ = _create_policy_with_version(db, test_storage, "T39")
    token = create_user_session(db, customer.id)

    res = client.post(
        f"/admin/policies/{policy.id}/publish",
        cookies={"session_id": token}
    )
    assert res.status_code == 403


def test_40_employee_cannot_perform_lifecycle_operation(db, test_storage):
    """40. Employee cannot perform lifecycle operation (403 Forbidden)."""
    employee = _create_user(db, Role.EMPLOYEE.value)
    policy, _ = _create_policy_with_version(db, test_storage, "T40")
    token = create_user_session(db, employee.id)

    res = client.post(
        f"/admin/policies/{policy.id}/publish",
        cookies={"session_id": token}
    )
    assert res.status_code == 403


def test_41_unauthorized_request_rejected(db, test_storage):
    """41. Unauthenticated request rejected (401 Unauthorized)."""
    policy, _ = _create_policy_with_version(db, test_storage, "T41")

    res = client.post(f"/admin/policies/{policy.id}/publish")
    assert res.status_code == 401


def test_42_admin_permission_boundary_respected(db, test_storage):
    """42. Admin with ADMIN_POLICY_MANAGEMENT can execute full lifecycle through API."""
    admin = _create_user(db, Role.ADMIN.value)
    policy, v1 = _create_policy_with_version(db, test_storage, "T42")
    token = create_user_session(db, admin.id)

    # 1. Publish
    pub_res = client.post(
        f"/admin/policies/{policy.id}/publish",
        cookies={"session_id": token}
    )
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "PUBLISHED"

    # 2. Activate
    act_res = client.post(
        f"/admin/policies/{policy.id}/activate",
        cookies={"session_id": token}
    )
    assert act_res.status_code == 200
    assert act_res.json()["status"] == "ACTIVE"
    assert act_res.json()["current_version_id"] == str(v1.id)

    # 3. Supersede with v2
    pdf2 = make_test_pdf_bytes(page_count=2, text="V2")
    v2 = PolicyFileService.attach_policy_version_document(
        db=db, policy_id=policy.id, filename="v2.pdf", file_bytes=pdf2,
        effective_from=datetime.now(timezone.utc) + timedelta(days=5), storage_dir=test_storage
    )
    sup_res = client.post(
        f"/admin/policies/{policy.id}/supersede?new_version_id={v2.id}",
        cookies={"session_id": token}
    )
    assert sup_res.status_code == 200
    assert sup_res.json()["status"] == "SUPERSEDED"
    assert sup_res.json()["current_version_id"] == str(v2.id)

    # 4. Archive
    arch_res = client.post(
        f"/admin/policies/{policy.id}/archive",
        cookies={"session_id": token}
    )
    assert arch_res.status_code == 200
    assert arch_res.json()["status"] == "ARCHIVED"

    # 5. Get History
    hist_res = client.get(
        f"/admin/policies/{policy.id}/history",
        cookies={"session_id": token}
    )
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 2
    assert history[0]["version_number"] == "2"
    assert history[1]["version_number"] == "1"
