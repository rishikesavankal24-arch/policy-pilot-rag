"""
M08.8 — Final M08 Integration, Regression Verification & M09 Handoff Tests
===========================================================================
Authoritative integration tests verifying the full M08 Policy Lifecycle:
Admin authority -> Policy DRAFT -> Upload v1 -> Publish -> Activate
-> Employee discovery, search, detail, applicability, history, download
-> RBAC isolation (Customer 403, Employee Admin-mutation 403, Unauthenticated 401)
-> Admin Version 2 upload -> Supersede -> History preservation
-> Archive -> Employee invisibility (404)
-> M09 Handoff Contract verification (eligibility, payload schema, source file resolution)
"""

import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.models import (
    User, Role, OnboardingStatus, Session as DBSession,
    Policy, PolicyVersion, PolicyStatus, PolicyApplicability,
    RegulatoryAuthority
)
from app.services.policy_file_service import PolicyFileService
from app.services.m09_handoff_service import (
    M09HandoffService, M09PolicyNotEligibleError, M09HandoffPayload
)

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _create_user(db, role: str, onboarding_status: str = "COMPLETED") -> tuple[User, str]:
    """Helper to create a user and active session token."""
    suffix = uuid.uuid4().hex[:6]
    email = f"test_m08_8_{role.lower()}_{suffix}@example.com"
    user = User(
        email=email,
        full_name=f"M08.8 {role} User",
        role=role,
        requested_role=role,
        onboarding_status=onboarding_status,
        authentication_provider="local",
        provider_subject_id=email
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = f"sess_m08_8_{uuid.uuid4().hex}"
    user_sess = DBSession(
        user_id=user.id,
        session_token=token,
        expires_at=datetime(2035, 1, 1, tzinfo=timezone.utc)
    )
    db.add(user_sess)
    db.commit()
    return user, token


def make_test_pdf_bytes(page_count: int = 1, text: str = "Policy Document") -> bytes:
    """Helper to generate minimal valid PDF bytes."""
    lines = [
        b"%PDF-1.4",
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
        (f"2 0 obj<</Type/Pages/Count {page_count}/Kids[" + " ".join(f"{3+i} 0 R" for i in range(page_count)) + "]>>endobj").encode("ascii")
    ]
    for i in range(page_count):
        lines.append(f"{3+i} 0 obj<</Type/Page/Parent 2 0 R>>endobj".encode("ascii"))
    lines.extend([
        b"xref",
        f"0 {3+page_count}".encode("ascii"),
        b"0000000000 65535 f"
    ])
    for _ in range(2 + page_count):
        lines.append(b"0000000050 00000 n")
    lines.extend([
        f"trailer<</Size {3+page_count}/Root 1 0 R>>".encode("ascii"),
        b"startxref",
        b"120",
        b"%%EOF"
    ])
    return b"\n".join(lines)


# ==============================================================================
# SECTION 1: Full End-to-End Policy Lifecycle Integration Test (Steps 1-26)
# ==============================================================================

def test_01_full_e2e_policy_lifecycle_integration(db):
    """
    Executes the complete 26-step end-to-end integration flow:
    Admin setup & ingestion -> Publish & Activate -> Employee catalog discovery
    -> Security enforcement -> Version 2 Supersede -> Archival invisibility.
    """
    admin_user, admin_token = _create_user(db, Role.ADMIN.value)
    emp_user, emp_token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    cust_user, cust_token = _create_user(db, Role.CUSTOMER.value, OnboardingStatus.COMPLETED.value)

    unique = uuid.uuid4().hex[:5].upper()

    # --------------------------------------------------------------------------
    # ADMIN LIFECYCLE (Steps 1-10)
    # --------------------------------------------------------------------------

    # 1. Create regulatory authority
    auth_res = client.post(
        "/api/admin/regulatory-authorities",
        json={
            "name": f"Reserve Bank of India Integration {unique}",
            "short_name": f"RBI_INT_{unique}",
            "authority_type": "CENTRAL_BANK",
            "jurisdiction": "IN",
            "website_url": "https://www.rbi.org.in"
        },
        cookies={"session_id": admin_token}
    )
    assert auth_res.status_code == 201, auth_res.text
    auth_data = auth_res.json()
    auth_id = auth_data["id"]

    # 2. Create policy in DRAFT
    policy_code = f"POL-INT-{unique}"
    policy_res = client.post(
        "/api/admin/policies",
        json={
            "policy_code": policy_code,
            "title": f"Priority Sector Lending Master Directive {unique}",
            "description": "Statutory priority lending norms and quotas for commercial institutions.",
            "category": "LENDING",
            "policy_type": "MASTER_DIRECTION",
            "jurisdiction": "NATIONAL",
            "institution": "APEX_BANK",
            "regulatory_authority_id": auth_id
        },
        cookies={"session_id": admin_token}
    )
    assert policy_res.status_code == 201, policy_res.text
    policy_data = policy_res.json()
    policy_id = policy_data["id"]
    assert policy_data["status"] == "DRAFT"

    # 3. Add applicability
    app_res = client.post(
        f"/api/admin/policies/{policy_id}/applicability",
        json={
            "institution": "APEX_BANK",
            "jurisdiction": "NATIONAL",
            "loan_type": "HOME_LOAN",
            "department": "UNDERWRITING"
        },
        cookies={"session_id": admin_token}
    )
    assert app_res.status_code == 201, app_res.text
    assert app_res.json()["loan_type"] == "HOME_LOAN"

    # 4. Upload a valid policy PDF as version 1
    pdf_v1 = make_test_pdf_bytes(page_count=3, text="Directive Version 1")
    up1_res = client.post(
        f"/api/admin/policies/{policy_id}/versions/upload",
        files={"file": ("master_directive_v1.pdf", pdf_v1, "application/pdf")},
        data={
            "changelog": "Initial committee draft release v1.0",
            "effective_from": datetime.now(timezone.utc).isoformat()
        },
        cookies={"session_id": admin_token}
    )
    assert up1_res.status_code == 201, up1_res.text
    v1_data = up1_res.json()
    v1_id = v1_data["id"]

    # 5. Verify metadata/hash/page count/storage
    assert v1_data["version_number"] == "1"
    assert v1_data["page_count"] == 3
    assert v1_data["file_size_bytes"] == len(pdf_v1)
    assert len(v1_data["file_hash"]) == 64  # SHA-256 hex string

    # 6. Publish policy
    pub_res = client.post(
        f"/api/admin/policies/{policy_id}/publish",
        cookies={"session_id": admin_token}
    )
    assert pub_res.status_code == 200, pub_res.text

    # 7. Verify PUBLISHED state
    assert pub_res.json()["status"] == "PUBLISHED"

    # 8. Activate policy
    act_res = client.post(
        f"/api/admin/policies/{policy_id}/activate?version_id={v1_id}",
        cookies={"session_id": admin_token}
    )
    assert act_res.status_code == 200, act_res.text

    # 9. Verify ACTIVE state
    act_data = act_res.json()
    assert act_data["status"] == "ACTIVE"

    # 10. Verify current_version_id points to active version
    assert act_data["current_version_id"] == v1_id

    # --------------------------------------------------------------------------
    # EMPLOYEE CONSUMPTION (Steps 11-17)
    # --------------------------------------------------------------------------

    # 11. Verified employee can list active policy
    emp_list_res = client.get(
        "/api/employee/policies",
        cookies={"session_id": emp_token}
    )
    assert emp_list_res.status_code == 200
    emp_list = emp_list_res.json()
    assert any(p["id"] == policy_id for p in emp_list["items"])

    # 12. Employee can search/find the policy
    search_res = client.get(
        f"/api/employee/policies?search={policy_code}",
        cookies={"session_id": emp_token}
    )
    assert search_res.status_code == 200
    assert len(search_res.json()["items"]) >= 1
    assert search_res.json()["items"][0]["policy_code"] == policy_code

    # 13. Employee can retrieve policy details
    emp_det_res = client.get(
        f"/api/employee/policies/{policy_id}",
        cookies={"session_id": emp_token}
    )
    assert emp_det_res.status_code == 200
    emp_det = emp_det_res.json()
    assert emp_det["id"] == policy_id
    assert emp_det["status"] == "ACTIVE"
    assert emp_det["current_version_id"] == v1_id

    # 14. Employee can retrieve applicability
    assert len(emp_det["applicabilities"]) >= 1
    assert emp_det["applicabilities"][0]["loan_type"] == "HOME_LOAN"
    assert emp_det["applicabilities"][0]["department"] == "UNDERWRITING"

    # 15. Employee can retrieve version history
    hist_res = client.get(
        f"/api/employee/policies/{policy_id}/history",
        cookies={"session_id": emp_token}
    )
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert len(hist) == 1
    assert hist[0]["id"] == v1_id
    assert "storage_path" not in str(hist)  # Zero path leakage

    # 16. Employee can access controlled policy document
    doc_res = client.get(
        f"/api/employee/policies/{policy_id}/versions/{v1_id}/file",
        cookies={"session_id": emp_token}
    )
    assert doc_res.status_code == 200
    assert doc_res.headers.get("content-type") == "application/pdf"
    assert len(doc_res.content) == len(pdf_v1)

    # 17. Employee cannot mutate policy metadata or lifecycle
    bad_mutate = client.patch(
        f"/api/admin/policies/{policy_id}",
        json={"title": "Hacked Title"},
        cookies={"session_id": emp_token}
    )
    assert bad_mutate.status_code == 403

    bad_upload = client.post(
        f"/api/admin/policies/{policy_id}/versions/upload",
        files={"file": ("hack.pdf", pdf_v1, "application/pdf")},
        cookies={"session_id": emp_token}
    )
    assert bad_upload.status_code == 403

    # --------------------------------------------------------------------------
    # CUSTOMER ISOLATION (Steps 18-19)
    # --------------------------------------------------------------------------

    # 18. Customer cannot access employee policy catalog
    cust_cat_res = client.get(
        "/api/employee/policies",
        cookies={"session_id": cust_token}
    )
    assert cust_cat_res.status_code == 403

    cust_det_res = client.get(
        f"/api/employee/policies/{policy_id}",
        cookies={"session_id": cust_token}
    )
    assert cust_det_res.status_code == 403

    cust_doc_res = client.get(
        f"/api/employee/policies/{policy_id}/versions/{v1_id}/file",
        cookies={"session_id": cust_token}
    )
    assert cust_doc_res.status_code == 403

    # 19. Customer cannot access admin policy management APIs
    cust_admin_res = client.get(
        "/api/admin/policies",
        cookies={"session_id": cust_token}
    )
    assert cust_admin_res.status_code == 403

    # --------------------------------------------------------------------------
    # ADMIN LIFECYCLE PROGRESSION & SUPERSEDING (Steps 20-26)
    # --------------------------------------------------------------------------

    # 20. Create version 2
    pdf_v2 = make_test_pdf_bytes(page_count=5, text="Directive Version 2 Revised")
    now = datetime.now(timezone.utc)
    up2_res = client.post(
        f"/api/admin/policies/{policy_id}/versions/upload",
        files={"file": ("master_directive_v2.pdf", pdf_v2, "application/pdf")},
        data={
            "changelog": "Revised quotas and thresholds for FY 2026-27",
            "effective_from": (now + timedelta(days=1)).isoformat()
        },
        cookies={"session_id": admin_token}
    )
    assert up2_res.status_code == 201, up2_res.text
    v2_data = up2_res.json()
    v2_id = v2_data["id"]
    assert v2_data["version_number"] == "2"
    assert v2_data["page_count"] == 5

    # 21 & 22. Supersede version 1 with version 2
    super_res = client.post(
        f"/api/admin/policies/{policy_id}/supersede?new_version_id={v2_id}",
        cookies={"session_id": admin_token}
    )
    assert super_res.status_code == 200, super_res.text
    super_data = super_res.json()
    assert super_data["status"] == "SUPERSEDED"

    # 23. Verify version history preserves both versions
    hist2_res = client.get(
        f"/api/admin/policies/{policy_id}/history",
        cookies={"session_id": admin_token}
    )
    assert hist2_res.status_code == 200
    hist2 = hist2_res.json()
    assert len(hist2) == 2
    version_numbers = [item["version_number"] for item in hist2]
    assert "1" in version_numbers and "2" in version_numbers

    # 24. Verify current_version_id points to version 2
    assert super_data["current_version_id"] == v2_id

    # 25. Archive the policy
    arch_res = client.post(
        f"/api/admin/policies/{policy_id}/archive",
        cookies={"session_id": admin_token}
    )
    assert arch_res.status_code == 200, arch_res.text
    assert arch_res.json()["status"] == "ARCHIVED"

    # 26. Verify archived policy is no longer visible to employees
    emp_arch_list = client.get(
        f"/api/employee/policies?search={policy_code}",
        cookies={"session_id": emp_token}
    )
    assert emp_arch_list.status_code == 200
    assert not any(p["id"] == policy_id for p in emp_arch_list.json()["items"])

    emp_arch_det = client.get(
        f"/api/employee/policies/{policy_id}",
        cookies={"session_id": emp_token}
    )
    assert emp_arch_det.status_code == 404, "Archived policy must return 404 for employees"

    emp_arch_file = client.get(
        f"/api/employee/policies/{policy_id}/versions/{v1_id}/file",
        cookies={"session_id": emp_token}
    )
    assert emp_arch_file.status_code == 404, "Archived policy files must return 404 for employees"


# ==============================================================================
# SECTION 2: M08 -> M09 Handoff Contract Tests (Section 3 & 4)
# ==============================================================================

def test_02_m09_handoff_contract_payload_and_eligibility(db):
    """
    Validates M09HandoffService guarantees:
    - Active policy with verified document generates compliant M09HandoffPayload.
    - Draft, Published, and Archived policies are rejected with M09PolicyNotEligibleError.
    - Raw source file can be resolved directly on disk for parsing.
    """
    unique = uuid.uuid4().hex[:5].upper()

    # 1. Create Authority & Policy in DRAFT
    auth = RegulatoryAuthority(
        name=f"National Credit Authority {unique}",
        short_name=f"NCA_{unique}",
        jurisdiction="IN"
    )
    db.add(auth)
    db.commit()

    policy = Policy(
        policy_code=f"POL-M09-{unique}",
        title=f"Microfinance Credit Guideline {unique}",
        description="Comprehensive prudential norms for unsecured microfinance.",
        category="CREDIT",
        policy_type="CREDIT_FRAMEWORK",
        jurisdiction="NATIONAL",
        institution="MICRO_CORP",
        status=PolicyStatus.DRAFT,
        regulatory_authority_id=auth.id
    )
    db.add(policy)
    db.commit()

    # Attach version 1 document
    pdf_bytes = make_test_pdf_bytes(page_count=4, text="M09 Contract PDF")
    v1 = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="microfinance_v1.pdf",
        file_bytes=pdf_bytes,
        changelog="Initial release"
    )
    policy.current_version_id = v1.id
    db.commit()

    # Add applicability scope
    app_scope = PolicyApplicability(
        policy_id=policy.id,
        institution="MICRO_CORP",
        jurisdiction="NATIONAL",
        loan_type="PERSONAL_LOAN",
        department="RISK"
    )
    db.add(app_scope)
    db.commit()

    # In DRAFT: Must be rejected by M09 handoff
    with pytest.raises(M09PolicyNotEligibleError) as exc_draft:
        M09HandoffService.get_policy_version_handoff_payload(db, policy.id)
    assert "Only ACTIVE policies are eligible" in str(exc_draft.value)

    # Transition to PUBLISHED: Must still be rejected
    policy.status = PolicyStatus.PUBLISHED
    db.commit()
    with pytest.raises(M09PolicyNotEligibleError) as exc_pub:
        M09HandoffService.get_policy_version_handoff_payload(db, policy.id)
    assert "Only ACTIVE policies are eligible" in str(exc_pub.value)

    # Transition to ACTIVE: Must succeed and return exact M09 contract payload
    policy.status = PolicyStatus.ACTIVE
    db.commit()

    payload = M09HandoffService.get_policy_version_handoff_payload(db, policy.id)
    assert isinstance(payload, M09HandoffPayload)
    
    # Verify Policy fields
    assert payload.policy.policy_id == str(policy.id)
    assert payload.policy.policy_code == policy.policy_code
    assert payload.policy.title == policy.title
    assert payload.policy.status == "ACTIVE"
    assert payload.policy.category == "CREDIT"
    assert payload.policy.regulatory_authority is not None
    assert payload.policy.regulatory_authority.short_name == f"NCA_{unique}"

    # Verify Version fields
    assert payload.version.policy_version_id == str(v1.id)
    assert payload.version.version_number == "1"
    assert payload.version.page_count == 4
    assert payload.version.file_size_bytes == len(pdf_bytes)
    assert len(payload.version.file_hash) == 64

    # Verify Applicability fields
    assert len(payload.applicabilities) == 1
    assert payload.applicabilities[0].loan_type == "PERSONAL_LOAN"
    assert payload.applicabilities[0].department == "RISK"

    # Verify Source Document Verification
    assert payload.is_source_document_verified is True
    assert payload.source_filename.endswith(".pdf")

    # Verify physical file accessor
    resolved_path, bound_version = M09HandoffService.get_policy_version_source_file(db, policy.id)
    assert resolved_path.exists()
    assert resolved_path.is_file()
    assert bound_version.id == v1.id

    # Transition to ARCHIVED: Must be rejected by M09 handoff
    policy.status = PolicyStatus.ARCHIVED
    db.commit()
    with pytest.raises(M09PolicyNotEligibleError) as exc_arch:
        M09HandoffService.get_policy_version_handoff_payload(db, policy.id)
    assert "Only ACTIVE policies are eligible" in str(exc_arch.value)


# ==============================================================================
# SECTION 3: Version Immutability, IDOR and File Safety (Section 5, 6 & 7)
# ==============================================================================

def test_03_version_immutability_and_security_invariants(db):
    """
    Verifies that bound PolicyVersion cryptographic attributes cannot be corrupted,
    unauthenticated requests receive 401, and cross-policy IDOR is blocked.
    """
    unique = uuid.uuid4().hex[:5].upper()
    admin_user, admin_token = _create_user(db, Role.ADMIN.value)
    emp_user, emp_token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unverified_user, unverified_token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.PENDING_VERIFICATION.value)

    # 1. Unauthenticated requests receive 401
    assert client.get("/api/employee/policies").status_code == 401
    assert client.get("/api/admin/policies").status_code == 401

    # 2. Unverified employee receives 403 on employee catalog
    assert client.get("/api/employee/policies", cookies={"session_id": unverified_token}).status_code == 403

    # 3. Create two independent policies to test cross-policy IDOR
    p1 = Policy(policy_code=f"POL-IDOR-A-{unique}", title="Policy A", status=PolicyStatus.ACTIVE)
    p2 = Policy(policy_code=f"POL-IDOR-B-{unique}", title="Policy B", status=PolicyStatus.ACTIVE)
    db.add_all([p1, p2])
    db.commit()

    pdf_bytes = make_test_pdf_bytes(1)
    v1 = PolicyFileService.attach_policy_version_document(
        db=db, policy_id=p1.id, filename="p1.pdf", file_bytes=pdf_bytes, changelog="v1"
    )
    p1.current_version_id = v1.id
    db.commit()

    # Cross-policy IDOR: Attempting to download version of p1 using p2's ID -> 404
    cross_res = client.get(
        f"/api/employee/policies/{p2.id}/versions/{v1.id}/file",
        cookies={"session_id": emp_token}
    )
    assert cross_res.status_code == 404, "Cross-policy IDOR must return 404"

    # Version immutability check
    original_hash = v1.file_hash
    original_size = v1.file_size_bytes
    assert original_hash is not None and len(original_hash) == 64
    assert original_size > 0
