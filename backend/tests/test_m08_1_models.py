import pytest
from datetime import datetime, timezone, timedelta
import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect

from app.db.session import SessionLocal, engine
from app.db.models import (
    User, Role, OnboardingStatus,
    Policy, PolicyVersion, RegulatoryAuthority, PolicyApplicability, PolicyStatus
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Clean up any created M08 test records
        session.query(PolicyApplicability).filter(PolicyApplicability.institution.like("TEST_%")).delete(synchronize_session=False)
        test_policies = session.query(Policy).filter(Policy.policy_code.like("POL-TEST-%")).all()
        for p in test_policies:
            p.current_version_id = None
        session.commit()

        for p in test_policies:
            session.query(PolicyVersion).filter(PolicyVersion.policy_id == p.id).delete(synchronize_session=False)
            session.query(PolicyApplicability).filter(PolicyApplicability.policy_id == p.id).delete(synchronize_session=False)
            session.delete(p)

        session.query(RegulatoryAuthority).filter(RegulatoryAuthority.short_name.like("TEST_%")).delete(synchronize_session=False)

        test_users = session.query(User).filter(User.email.like("test_m08_%@example.com")).all()
        for u in test_users:
            session.delete(u)

        session.commit()
        session.close()


def create_test_user(db, prefix="admin"):
    uid = uuid.uuid4()
    email = f"test_m08_{prefix}_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name=f"Test {prefix.capitalize()} User",
        role=Role.ADMIN.value,
        requested_role=Role.ADMIN.value,
        onboarding_status=OnboardingStatus.COMPLETED.value,
        authentication_provider="local",
        provider_subject_id=email,
        phone_number="+919876543210",
        date_of_birth="1990-01-01",
        address="123 Financial District",
        city="Mumbai",
        state="Maharashtra",
        pincode="400051",
        language="English",
        consent_accepted=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_1_policystatus_enum_exists():
    """Verify PolicyStatus enum values."""
    assert PolicyStatus.DRAFT.value == "DRAFT"
    assert PolicyStatus.PUBLISHED.value == "PUBLISHED"
    assert PolicyStatus.ACTIVE.value == "ACTIVE"
    assert PolicyStatus.SUPERSEDED.value == "SUPERSEDED"
    assert PolicyStatus.ARCHIVED.value == "ARCHIVED"
    assert len(PolicyStatus) == 5


def test_2_policy_creation_defaults(db):
    """Verify Policy model creation and default values."""
    policy = Policy(
        policy_code="POL-TEST-001",
        title="Retail Credit Underwriting Guidelines",
        description="Standard operating guidelines for personal credit verification.",
        category="RETAIL_CREDIT",
        policy_type="CREDIT_POLICY",
        status=PolicyStatus.DRAFT,
        institution="PolicyPilot Bank",
        jurisdiction="IN"
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    assert policy.id is not None
    assert isinstance(policy.id, uuid.UUID)
    assert policy.policy_code == "POL-TEST-001"
    assert policy.title == "Retail Credit Underwriting Guidelines"
    assert policy.status == PolicyStatus.DRAFT
    assert policy.created_at is not None
    assert policy.current_version_id is None


def test_3_policy_code_uniqueness(db):
    """Verify unique constraint on policy_code."""
    p1 = Policy(
        policy_code="POL-TEST-UNIQUE",
        title="First Unique Policy"
    )
    db.add(p1)
    db.commit()

    p2 = Policy(
        policy_code="POL-TEST-UNIQUE",
        title="Duplicate Code Policy"
    )
    db.add(p2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_4_policy_version_can_reference_policy(db):
    """Verify PolicyVersion creation and relationship to Policy."""
    policy = Policy(
        policy_code="POL-TEST-VER",
        title="Versioned Policy"
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    now = datetime.now(timezone.utc)
    version = PolicyVersion(
        policy_id=policy.id,
        version_number="1.0.0",
        changelog="Initial baseline version",
        file_url="storage/policies/pol_test_ver_v1.pdf",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_size_bytes=1048576,
        page_count=12,
        effective_from=now,
        effective_to=now + timedelta(days=365)
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    assert version.id is not None
    assert version.policy_id == policy.id
    assert version.policy.policy_code == "POL-TEST-VER"
    assert len(policy.versions) == 1
    assert policy.versions[0].version_number == "1.0.0"


def test_5_policy_applicability_can_reference_policy(db):
    """Verify PolicyApplicability relationship to Policy."""
    policy = Policy(
        policy_code="POL-TEST-APP",
        title="Applicable Policy"
    )
    db.add(policy)
    db.commit()

    applicability = PolicyApplicability(
        policy_id=policy.id,
        institution="TEST_DEMO_BANK",
        jurisdiction="IN",
        loan_type="PERSONAL_LOAN",
        department="Retail Credit"
    )
    db.add(applicability)
    db.commit()
    db.refresh(policy)

    assert len(policy.applicabilities) == 1
    app = policy.applicabilities[0]
    assert app.loan_type == "PERSONAL_LOAN"
    assert app.department == "Retail Credit"
    assert app.policy.policy_code == "POL-TEST-APP"


def test_6_regulatory_authority_creation(db):
    """Verify RegulatoryAuthority creation, defaults, and short_name uniqueness."""
    auth = RegulatoryAuthority(
        name="Reserve Bank of India",
        short_name="TEST_RBI",
        authority_type="CENTRAL_BANK",
        jurisdiction="IN",
        website_url="https://www.rbi.org.in",
        description="Central banking and regulatory authority of India."
    )
    db.add(auth)
    db.commit()
    db.refresh(auth)

    assert auth.id is not None
    assert auth.short_name == "TEST_RBI"
    assert auth.is_active is True
    assert auth.created_at is not None

    # Verify duplicate short_name raises IntegrityError
    dup = RegulatoryAuthority(
        name="Duplicate RBI",
        short_name="TEST_RBI",
        authority_type="CENTRAL_BANK"
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_7_user_foreign_keys(db):
    """Verify User foreign keys on Policy and PolicyVersion."""
    creator = create_test_user(db, prefix="creator")
    publisher = create_test_user(db, prefix="publisher")

    policy = Policy(
        policy_code="POL-TEST-USER-FK",
        title="User FK Policy",
        created_by=creator.id
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    assert policy.creator.id == creator.id
    assert policy.creator.email == creator.email

    version = PolicyVersion(
        policy_id=policy.id,
        version_number="1.0",
        created_by=creator.id,
        published_by=publisher.id
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    assert version.creator.id == creator.id
    assert version.publisher.id == publisher.id


def test_8_nullable_applicability_dimensions(db):
    """Verify that broad policies support nullable applicability dimensions."""
    policy = Policy(
        policy_code="POL-TEST-BROAD",
        title="Broad Institutional Policy"
    )
    db.add(policy)
    db.commit()

    # Broad scope: applies to all loan types and departments within an institution
    broad_app = PolicyApplicability(
        policy_id=policy.id,
        institution="TEST_DEMO_BANK",
        jurisdiction=None,
        loan_type=None,
        department=None
    )
    db.add(broad_app)
    db.commit()
    db.refresh(broad_app)

    assert broad_app.institution == "TEST_DEMO_BANK"
    assert broad_app.jurisdiction is None
    assert broad_app.loan_type is None
    assert broad_app.department is None


def test_9_current_version_relationship(db):
    """Verify circular relationship between Policy and its current PolicyVersion."""
    policy = Policy(
        policy_code="POL-TEST-CURR-VER",
        title="Current Version Test Policy"
    )
    db.add(policy)
    db.commit()

    v1 = PolicyVersion(
        policy_id=policy.id,
        version_number="1.0",
        changelog="V1 initial"
    )
    v2 = PolicyVersion(
        policy_id=policy.id,
        version_number="2.0",
        changelog="V2 update"
    )
    db.add_all([v1, v2])
    db.commit()

    # Link active current version to v2
    policy.current_version_id = v2.id
    policy.status = PolicyStatus.ACTIVE
    db.commit()
    db.refresh(policy)

    assert policy.current_version is not None
    assert policy.current_version.id == v2.id
    assert policy.current_version.version_number == "2.0"
    assert len(policy.versions) == 2


def test_10_migration_schema_integrity():
    """Verify PostgreSQL database tables, foreign keys, and indexes via inspection."""
    insp = inspect(engine)
    table_names = insp.get_table_names()

    for expected_table in ["policies", "policy_versions", "regulatory_authorities", "policy_applicability"]:
        assert expected_table in table_names, f"Table {expected_table} missing from schema"

    # Policies FKs and indexes
    policies_fks = [fk["referred_table"] for fk in insp.get_foreign_keys("policies")]
    assert "users" in policies_fks
    assert "policy_versions" in policies_fks
    assert "regulatory_authorities" in policies_fks

    policies_indexes = [i["name"] for i in insp.get_indexes("policies")]
    assert "ix_policies_policy_code" in policies_indexes
    assert "ix_policies_status" in policies_indexes
    assert "ix_policies_current_version_id" in policies_indexes

    # Policy versions unique constraint and indexes
    pv_indexes = [i["name"] for i in insp.get_indexes("policy_versions")]
    assert "ix_policy_versions_policy_id" in pv_indexes
    assert "ix_policy_versions_version_number" in pv_indexes
    assert "ix_policy_versions_effective_from" in pv_indexes
    assert "ix_policy_versions_file_hash" in pv_indexes

    pv_unique = [u["name"] for u in insp.get_unique_constraints("policy_versions")]
    assert "uq_policy_versions_policy_id_version_number" in pv_unique

    # Policy applicability FKs
    app_fks = [fk["referred_table"] for fk in insp.get_foreign_keys("policy_applicability")]
    assert "policies" in app_fks
