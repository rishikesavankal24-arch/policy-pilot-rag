import pytest
import uuid
from app.db.session import SessionLocal
from app.db.models import (
    User, Role, OnboardingStatus,
    Policy, PolicyVersion, RegulatoryAuthority, PolicyApplicability, PolicyStatus
)
from app.services.policy_metadata_service import (
    RegulatoryAuthorityService,
    PolicyMetadataService,
    PolicyApplicabilityService,
    PolicyMetadataValidationError,
    PolicyMetadataNotFoundError,
    PolicyMetadataConflictError,
    validate_and_normalize_url
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Clean up test applicability rows
        session.query(PolicyApplicability).filter(PolicyApplicability.institution.like("TEST_%")).delete(synchronize_session=False)

        # Unlink current_version_id and delete test policies and versions
        test_policies = session.query(Policy).filter(Policy.policy_code.like("POL-TEST-%")).all()
        for p in test_policies:
            p.current_version_id = None
        session.commit()

        for p in test_policies:
            session.query(PolicyVersion).filter(PolicyVersion.policy_id == p.id).delete(synchronize_session=False)
            session.query(PolicyApplicability).filter(PolicyApplicability.policy_id == p.id).delete(synchronize_session=False)
            session.delete(p)

        session.query(RegulatoryAuthority).filter(RegulatoryAuthority.short_name.like("TEST_%")).delete(synchronize_session=False)

        test_users = session.query(User).filter(User.email.like("test_m08_2_%@example.com")).all()
        for u in test_users:
            session.delete(u)

        session.commit()
        session.close()


def create_test_admin(db):
    uid = uuid.uuid4()
    email = f"test_m08_2_admin_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name="M08.2 Admin Tester",
        role=Role.ADMIN.value,
        requested_role=Role.ADMIN.value,
        onboarding_status=OnboardingStatus.COMPLETED.value,
        authentication_provider="local",
        provider_subject_id=email
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ==============================================================================
# 1-8: Regulatory Authority Tests
# ==============================================================================

def test_01_create_valid_authority(db):
    """Test 1: Create a valid regulatory authority with standard parameters."""
    auth = RegulatoryAuthorityService.create_authority(
        db=db,
        name="Reserve Bank of India",
        short_name="TEST_RBI",
        authority_type="CENTRAL_BANK",
        jurisdiction="IN",
        website_url="https://www.rbi.org.in",
        description="India's central bank and financial regulator."
    )
    assert auth.id is not None
    assert auth.name == "Reserve Bank of India"
    assert auth.short_name == "TEST_RBI"
    assert auth.authority_type == "CENTRAL_BANK"
    assert auth.jurisdiction == "IN"
    assert auth.website_url == "https://www.rbi.org.in"
    assert auth.is_active is True


def test_02_duplicate_short_name_rejected(db):
    """Test 2: Rejection of duplicate authority short_name (case-insensitive)."""
    RegulatoryAuthorityService.create_authority(
        db=db,
        name="Unique Authority One",
        short_name="TEST_DUP_AUTH"
    )

    with pytest.raises(PolicyMetadataConflictError) as exc_info:
        RegulatoryAuthorityService.create_authority(
            db=db,
            name="Unique Authority Two",
            short_name="test_dup_auth"  # Case variant
        )
    assert "already exists" in str(exc_info.value)


def test_03_missing_name_rejected(db):
    """Test 3: Rejection of empty or whitespace-only name."""
    with pytest.raises(PolicyMetadataValidationError) as exc_info1:
        RegulatoryAuthorityService.create_authority(
            db=db,
            name="",
            short_name="TEST_NONAME"
        )
    assert "name is required" in str(exc_info1.value)

    with pytest.raises(PolicyMetadataValidationError) as exc_info2:
        RegulatoryAuthorityService.create_authority(
            db=db,
            name="   ",
            short_name="TEST_SPACES"
        )
    assert "name is required" in str(exc_info2.value)


def test_04_missing_short_name_rejected(db):
    """Test 4: Rejection of empty or whitespace-only short_name."""
    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        RegulatoryAuthorityService.create_authority(
            db=db,
            name="Valid Authority Name",
            short_name="   "
        )
    assert "short_name is required" in str(exc_info.value)


def test_05_invalid_authority_type_rejected(db):
    """Test 5: Rejection of unapproved authority_type values."""
    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        RegulatoryAuthorityService.create_authority(
            db=db,
            name="Custom Entity",
            short_name="TEST_BAD_TYPE",
            authority_type="UNKNOWN_CATEGORY"
        )
    assert "Invalid authority_type" in str(exc_info.value)


def test_06_url_validation(db):
    """Test 6: Strict URL format validation without network resolution."""
    # Valid HTTP and HTTPS
    assert validate_and_normalize_url("https://www.rbi.org.in/scripts/BS_ViewMasCirculardetails.aspx") is not None
    assert validate_and_normalize_url("http://localhost:8000/docs") is not None
    assert validate_and_normalize_url(None) is None
    assert validate_and_normalize_url("  ") is None

    # Invalid scheme
    with pytest.raises(PolicyMetadataValidationError) as exc_ftp:
        validate_and_normalize_url("ftp://files.example.com/doc.pdf")
    assert "http or https" in str(exc_ftp.value)

    # Malformed URL without domain
    with pytest.raises(PolicyMetadataValidationError) as exc_malformed:
        validate_and_normalize_url("http:///just-a-path")
    assert "valid host" in str(exc_malformed.value)

    # Invalid domain with spaces
    with pytest.raises(PolicyMetadataValidationError) as exc_domain:
        validate_and_normalize_url("https://invalid domain.com/policy")
    assert "domain" in str(exc_domain.value)


def test_07_update_authority(db):
    """Test 7: Update regulatory authority metadata."""
    auth = RegulatoryAuthorityService.create_authority(
        db=db,
        name="Original Authority Name",
        short_name="TEST_UPDATE_AUTH",
        website_url="https://orig.gov.in"
    )

    updated = RegulatoryAuthorityService.update_authority(
        db=db,
        authority_id=auth.id,
        name="Updated Authority Name",
        website_url="https://updated.gov.in",
        description="Newly added description."
    )
    assert updated.name == "Updated Authority Name"
    assert updated.website_url == "https://updated.gov.in"
    assert updated.description == "Newly added description."
    assert updated.short_name == "TEST_UPDATE_AUTH"


def test_08_deactivate_authority(db):
    """Test 8: Soft deactivation of regulatory authority."""
    auth = RegulatoryAuthorityService.create_authority(
        db=db,
        name="Authority To Deactivate",
        short_name="TEST_DEACT_AUTH"
    )
    assert auth.is_active is True

    deactivated = RegulatoryAuthorityService.deactivate_authority(db, auth.id)
    assert deactivated.is_active is False

    # Listing with filter
    active_list = RegulatoryAuthorityService.list_authorities(db, is_active=True)
    assert auth.id not in [a.id for a in active_list]

    all_list = RegulatoryAuthorityService.list_authorities(db, is_active=False)
    assert auth.id in [a.id for a in all_list]


# ==============================================================================
# 9-15: Policy Metadata Tests
# ==============================================================================

def test_09_valid_policy_metadata(db):
    """Test 9: Create policy with full valid metadata."""
    admin = create_test_admin(db)
    auth = RegulatoryAuthorityService.create_authority(
        db=db,
        name="Securities and Exchange Board",
        short_name="TEST_SEBI",
        authority_type="STATUTORY_BODY"
    )

    policy = PolicyMetadataService.create_policy_metadata(
        db=db,
        policy_code="POL-TEST-001",
        title="Personal Loan Prudential Norms",
        description="Guidelines on consumer credit limits and risk weights.",
        category="RETAIL_CREDIT",
        policy_type="REGULATORY_DIRECTIVE",
        institution="PolicyPilot Bank",
        jurisdiction="IN",
        regulatory_authority_id=auth.id,
        created_by=admin.id
    )

    assert policy.id is not None
    assert policy.policy_code == "POL-TEST-001"
    assert policy.status == PolicyStatus.DRAFT
    assert policy.regulatory_authority_id == auth.id
    assert policy.created_by == admin.id
    assert policy.created_at is not None


def test_10_duplicate_policy_code_rejected(db):
    """Test 10: Rejection of duplicate policy_code."""
    PolicyMetadataService.create_policy_metadata(
        db=db,
        policy_code="POL-TEST-DUP",
        title="First Policy Entry"
    )

    with pytest.raises(PolicyMetadataConflictError) as exc_info:
        PolicyMetadataService.create_policy_metadata(
            db=db,
            policy_code="pol-test-dup",  # case-insensitive check
            title="Second Policy Entry"
        )
    assert "already exists" in str(exc_info.value)


def test_11_empty_whitespace_policy_code_rejected(db):
    """Test 11: Rejection of empty or whitespace policy_code."""
    with pytest.raises(PolicyMetadataValidationError) as exc1:
        PolicyMetadataService.create_policy_metadata(
            db=db,
            policy_code="",
            title="Policy Title"
        )
    assert "Policy code is required" in str(exc1.value)

    with pytest.raises(PolicyMetadataValidationError) as exc2:
        PolicyMetadataService.create_policy_metadata(
            db=db,
            policy_code="    ",
            title="Policy Title"
        )
    assert "Policy code is required" in str(exc2.value)


def test_12_empty_title_rejected(db):
    """Test 12: Rejection of empty or whitespace title."""
    with pytest.raises(PolicyMetadataValidationError) as exc:
        PolicyMetadataService.create_policy_metadata(
            db=db,
            policy_code="POL-TEST-NOTITLE",
            title="   "
        )
    assert "Policy title is required" in str(exc.value)


def test_13_invalid_regulatory_authority_id_rejected(db):
    """Test 13: Rejection of non-existent or malformed regulatory_authority_id."""
    # Malformed UUID string
    with pytest.raises(PolicyMetadataValidationError) as exc_bad_uuid:
        PolicyMetadataService.create_policy_metadata(
            db=db,
            policy_code="POL-TEST-BAD-UUID",
            title="Policy Title",
            regulatory_authority_id="not-a-valid-uuid"
        )
    assert "valid UUID" in str(exc_bad_uuid.value)

    # Non-existent UUID
    random_id = uuid.uuid4()
    with pytest.raises(PolicyMetadataNotFoundError) as exc_missing:
        PolicyMetadataService.create_policy_metadata(
            db=db,
            policy_code="POL-TEST-MISSING-AUTH",
            title="Policy Title",
            regulatory_authority_id=random_id
        )
    assert "not found" in str(exc_missing.value)


def test_14_inactive_authority_handling(db):
    """Test 14: Inactive authorities cannot be linked to policies."""
    auth = RegulatoryAuthorityService.create_authority(
        db=db,
        name="Inactive Authority",
        short_name="TEST_INACTIVE_AUTH",
        is_active=False
    )

    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        PolicyMetadataService.create_policy_metadata(
            db=db,
            policy_code="POL-TEST-INACT-AUTH",
            title="Policy with Inactive Authority",
            regulatory_authority_id=auth.id
        )
    assert "inactive regulatory authority" in str(exc_info.value)


def test_15_metadata_normalization(db):
    """Test 15: String trimming, casing, and normalization of policy metadata."""
    policy = PolicyMetadataService.create_policy_metadata(
        db=db,
        policy_code="  pol-test-norm  ",
        title="  Trimmed Policy Title  ",
        category="  retail_credit  ",
        policy_type="  internal_guideline  ",
        institution="  PolicyPilot Demo Bank  ",
        jurisdiction="  in  "
    )

    assert policy.policy_code == "POL-TEST-NORM"
    assert policy.title == "Trimmed Policy Title"
    assert policy.category == "RETAIL_CREDIT"
    assert policy.policy_type == "INTERNAL_GUIDELINE"
    assert policy.institution == "PolicyPilot Demo Bank"
    assert policy.jurisdiction == "IN"

    # Source metadata extraction
    source_meta = PolicyMetadataService.get_policy_source_metadata(db, policy.id)
    assert source_meta["policy_code"] == "POL-TEST-NORM"
    assert source_meta["has_regulatory_authority"] is False


# ==============================================================================
# 16-20: Applicability Tests
# ==============================================================================

def test_16_valid_applicability(db):
    """Test 16: Adding valid applicability dimensions to a policy."""
    policy = PolicyMetadataService.create_policy_metadata(
        db=db,
        policy_code="POL-TEST-APP-01",
        title="Applicability Test Policy"
    )

    app_rule = PolicyApplicabilityService.add_applicability(
        db=db,
        policy_id=policy.id,
        institution="TEST_BANK",
        jurisdiction="IN",
        loan_type="PERSONAL_LOAN",
        department="Credit Underwriting"
    )

    assert app_rule.id is not None
    assert app_rule.policy_id == policy.id
    assert app_rule.institution == "TEST_BANK"
    assert app_rule.jurisdiction == "IN"
    assert app_rule.loan_type == "PERSONAL_LOAN"
    assert app_rule.department == "Credit Underwriting"

    rules = PolicyApplicabilityService.list_applicabilities(db, policy.id)
    assert len(rules) == 1
    assert rules[0].id == app_rule.id


def test_17_no_applicability_dimension_rejected(db):
    """Test 17: Rejection when zero dimensions are provided."""
    policy = PolicyMetadataService.create_policy_metadata(
        db=db,
        policy_code="POL-TEST-APP-02",
        title="Zero Dimension Policy"
    )

    with pytest.raises(PolicyMetadataValidationError) as exc_info:
        PolicyApplicabilityService.add_applicability(
            db=db,
            policy_id=policy.id,
            institution="   ",
            jurisdiction=None,
            loan_type="",
            department=None
        )
    assert "At least one applicability dimension" in str(exc_info.value)


def test_18_duplicate_applicability_rejected(db):
    """Test 18: Duplicate applicability entries on the same policy rejected."""
    policy = PolicyMetadataService.create_policy_metadata(
        db=db,
        policy_code="POL-TEST-APP-03",
        title="Duplicate Scope Policy"
    )

    PolicyApplicabilityService.add_applicability(
        db=db,
        policy_id=policy.id,
        institution="TEST_BANK",
        loan_type="HOME_LOAN"
    )

    # Identical rule
    with pytest.raises(PolicyMetadataConflictError) as exc_info:
        PolicyApplicabilityService.add_applicability(
            db=db,
            policy_id=policy.id,
            institution="TEST_BANK",
            loan_type="HOME_LOAN"
        )
    assert "identical applicability rule already exists" in str(exc_info.value)


def test_19_invalid_policy_id_rejected(db):
    """Test 19: Rejection of non-existent policy_id when creating applicability."""
    non_existent = uuid.uuid4()
    with pytest.raises(PolicyMetadataNotFoundError) as exc_info:
        PolicyApplicabilityService.add_applicability(
            db=db,
            policy_id=non_existent,
            loan_type="EDUCATION_LOAN"
        )
    assert "not found" in str(exc_info.value)


def test_20_normalization_of_applicability_values(db):
    """Test 20: Normalization (strip, upper case on loan_type and jurisdiction)."""
    policy = PolicyMetadataService.create_policy_metadata(
        db=db,
        policy_code="POL-TEST-APP-04",
        title="Normalized Scope Policy"
    )

    app_rule = PolicyApplicabilityService.add_applicability(
        db=db,
        policy_id=policy.id,
        institution="  TEST_FEDERAL_CREDIT  ",
        jurisdiction="  in  ",
        loan_type="  personal_loan  ",
        department="  Risk & Underwriting  "
    )

    assert app_rule.institution == "TEST_FEDERAL_CREDIT"
    assert app_rule.jurisdiction == "IN"
    assert app_rule.loan_type == "PERSONAL_LOAN"
    assert app_rule.department == "Risk & Underwriting"
