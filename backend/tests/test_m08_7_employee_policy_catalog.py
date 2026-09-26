"""
M08.7 — Employee Policy Catalog Tests
=====================================
Tests verified employee policy discovery, search, filtering, detail projection,
version history, secure document streaming, active-only visibility constraints,
and strict read-only RBAC enforcement.
"""

import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.models import (
    User, Role, OnboardingStatus, Session as UserSession,
    Policy, PolicyVersion, PolicyStatus, PolicyApplicability,
    RegulatoryAuthority
)
from app.services.policy_file_service import PolicyFileService

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
    """Helper to create a user with a valid active session token."""
    suffix = uuid.uuid4().hex[:6]
    email = f"user_{suffix}@example.com"
    user = User(
        email=email,
        full_name=f"Test User {suffix}",
        role=role,
        provider_subject_id=email,
        onboarding_status=onboarding_status
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = f"sess_{uuid.uuid4().hex}"
    session = UserSession(
        user_id=user.id,
        session_token=token,
        expires_at=datetime(2035, 1, 1, tzinfo=timezone.utc)
    )
    db.add(session)
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
# 1-7: Employee Policy Catalog Discovery, Retrieval, Search, Filters & Pagination
# ==============================================================================

def test_01_verified_employee_can_list_active_policies(db):
    """1. Verified employee can list active policies."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-EMP-LIST-{unique_suffix}",
        title="Active Lending Framework",
        status=PolicyStatus.ACTIVE
    )
    db.add(p)
    db.commit()

    res = client.get("/api/employee/policies", cookies={"session_id": token})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    matching = [x for x in data["items"] if x["policy_code"] == p.policy_code]
    assert len(matching) == 1
    assert matching[0]["status"] == "ACTIVE"


def test_02_verified_employee_can_retrieve_active_policy(db):
    """2. Verified employee can retrieve full active policy details."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    auth = RegulatoryAuthority(
        name=f"Reserve Bank of India {unique_suffix}",
        short_name=f"RBI_{unique_suffix}",
        authority_type="CENTRAL_BANK"
    )
    db.add(auth)
    db.commit()

    p = Policy(
        policy_code=f"POL-EMP-GET-{unique_suffix}",
        title="Housing Loan Underwriting Policy",
        description="Comprehensive prudential norms for credit facilities",
        category="MORTGAGE",
        policy_type="REGULATORY",
        institution="PolicyPilot Bank",
        jurisdiction="IN",
        status=PolicyStatus.ACTIVE,
        regulatory_authority_id=auth.id
    )
    db.add(p)
    db.commit()

    res = client.get(f"/api/employee/policies/{p.id}", cookies={"session_id": token})
    assert res.status_code == 200
    detail = res.json()
    assert detail["id"] == str(p.id)
    assert detail["policy_code"] == p.policy_code
    assert detail["title"] == "Housing Loan Underwriting Policy"
    assert detail["category"] == "MORTGAGE"
    assert detail["regulatory_authority"]["short_name"] == f"RBI_{unique_suffix}"
    assert detail["status"] == "ACTIVE"


def test_03_verified_employee_can_retrieve_history(db):
    """3. Verified employee can view version history for an active policy."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-EMP-HIST-{unique_suffix}",
        title="Multi Version Policy",
        status=PolicyStatus.ACTIVE
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=1)
    v1 = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=p.id,
        filename="v1.pdf",
        file_bytes=pdf_bytes,
        changelog="Version 1 original"
    )

    res = client.get(f"/api/employee/policies/{p.id}/history", cookies={"session_id": token})
    assert res.status_code == 200
    history = res.json()
    assert len(history) >= 1
    assert history[0]["version_number"] == "1"
    assert history[0]["changelog"] == "Version 1 original"
    assert "download_url" in history[0]
    # Path safety: raw storage paths must not appear
    assert "policy_docs" not in str(history)


def test_04_verified_employee_can_access_authorized_document(db):
    """4. Verified employee can stream the document file of an active policy."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-EMP-DOC-{unique_suffix}",
        title="Document Access Policy",
        status=PolicyStatus.ACTIVE
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=2, text="RBI Circular 2026")
    v = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=p.id,
        filename="circular.pdf",
        file_bytes=pdf_bytes
    )

    res = client.get(f"/api/employee/policies/{p.id}/versions/{v.id}/file", cookies={"session_id": token})
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content == pdf_bytes


def test_05_search_works_by_code_and_title(db):
    """5. Search filters policies by policy_code or title."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p1 = Policy(
        policy_code=f"POL-SEARCH-ALPHA-{unique_suffix}",
        title="Agricultural Credit Subsidy",
        status=PolicyStatus.ACTIVE
    )
    p2 = Policy(
        policy_code=f"POL-SEARCH-BETA-{unique_suffix}",
        title="Consumer Micro Lending",
        status=PolicyStatus.ACTIVE
    )
    db.add_all([p1, p2])
    db.commit()

    res = client.get(f"/api/employee/policies?search=ALPHA-{unique_suffix}", cookies={"session_id": token})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["policy_code"] == p1.policy_code

    res_title = client.get(f"/api/employee/policies?search=Micro+Lending", cookies={"session_id": token})
    assert res_title.status_code == 200
    codes = [x["policy_code"] for x in res_title.json()["items"]]
    assert p2.policy_code in codes


def test_06_filtering_works_by_category_and_dimensions(db):
    """6. Filtering works by category, jurisdiction, and applicability dimensions."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p1 = Policy(
        policy_code=f"POL-FILT-KYC-{unique_suffix}",
        title="AML Risk Matrix",
        category="KYC",
        policy_type="STATUTORY",
        jurisdiction="IN",
        status=PolicyStatus.ACTIVE
    )
    p2 = Policy(
        policy_code=f"POL-FILT-LEND-{unique_suffix}",
        title="Commercial Credit",
        category="LENDING",
        policy_type="INTERNAL",
        jurisdiction="US",
        status=PolicyStatus.ACTIVE
    )
    db.add_all([p1, p2])
    db.commit()

    # Add applicability to p1
    app_rule = PolicyApplicability(
        policy_id=p1.id,
        loan_type="PERSONAL_LOAN",
        department="Compliance"
    )
    db.add(app_rule)
    db.commit()

    res_cat = client.get("/api/employee/policies?category=KYC", cookies={"session_id": token})
    assert res_cat.status_code == 200
    codes_cat = [x["policy_code"] for x in res_cat.json()["items"]]
    assert p1.policy_code in codes_cat
    assert p2.policy_code not in codes_cat

    res_lt = client.get("/api/employee/policies?loan_type=PERSONAL_LOAN", cookies={"session_id": token})
    assert res_lt.status_code == 200
    codes_lt = [x["policy_code"] for x in res_lt.json()["items"]]
    assert p1.policy_code in codes_lt


def test_07_pagination_limits(db):
    """7. Pagination handles page and page_size safely."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    res = client.get("/api/employee/policies?page=1&page_size=2", cookies={"session_id": token})
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


# ==============================================================================
# 8-11: Policy Visibility Constraints (ACTIVE ONLY)
# ==============================================================================

def test_08_draft_policies_excluded_from_listing(db):
    """8. Policies in DRAFT status are strictly excluded from catalog."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-DRAFT-EXCL-{unique_suffix}",
        title="Unpublished Draft Guidelines",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    res = client.get("/api/employee/policies", cookies={"session_id": token})
    assert res.status_code == 200
    codes = [x["policy_code"] for x in res.json()["items"]]
    assert p.policy_code not in codes


def test_09_published_policies_excluded_from_listing(db):
    """9. Policies in PUBLISHED status (not yet ACTIVE) are excluded."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-PUB-EXCL-{unique_suffix}",
        title="Published Awaiting Activation",
        status=PolicyStatus.PUBLISHED
    )
    db.add(p)
    db.commit()

    res = client.get("/api/employee/policies", cookies={"session_id": token})
    assert res.status_code == 200
    codes = [x["policy_code"] for x in res.json()["items"]]
    assert p.policy_code not in codes


def test_10_archived_policies_excluded_from_listing(db):
    """10. Policies in ARCHIVED status are excluded."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-ARCH-EXCL-{unique_suffix}",
        title="Old Retired Circular",
        status=PolicyStatus.ARCHIVED
    )
    db.add(p)
    db.commit()

    res = client.get("/api/employee/policies", cookies={"session_id": token})
    assert res.status_code == 200
    codes = [x["policy_code"] for x in res.json()["items"]]
    assert p.policy_code not in codes


def test_11_superseded_policies_excluded_from_listing(db):
    """11. Policies in SUPERSEDED status are excluded from primary active catalog."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-SUPER-EXCL-{unique_suffix}",
        title="Superseded Master Direction",
        status=PolicyStatus.SUPERSEDED
    )
    db.add(p)
    db.commit()

    res = client.get("/api/employee/policies", cookies={"session_id": token})
    assert res.status_code == 200
    codes = [x["policy_code"] for x in res.json()["items"]]
    assert p.policy_code not in codes


# ==============================================================================
# 12-17: Detail Responses, Applicability, and 404 Boundaries
# ==============================================================================

def test_12_applicability_returned_in_detail(db):
    """12. Applicability scope rules are returned in employee policy detail."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-APP-RET-{unique_suffix}",
        title="Applicability Demo Policy",
        status=PolicyStatus.ACTIVE
    )
    db.add(p)
    db.commit()

    app_rule = PolicyApplicability(
        policy_id=p.id,
        institution="Apex Bank",
        jurisdiction="IN",
        loan_type="AUTO_LOAN",
        department="Vehicle Finance"
    )
    db.add(app_rule)
    db.commit()

    res = client.get(f"/api/employee/policies/{p.id}", cookies={"session_id": token})
    assert res.status_code == 200
    detail = res.json()
    assert len(detail["applicabilities"]) == 1
    assert detail["applicabilities"][0]["loan_type"] == "AUTO_LOAN"
    assert detail["applicabilities"][0]["department"] == "Vehicle Finance"


def test_13_invalid_policy_id_returns_404(db):
    """13. Non-existent policy ID returns 404."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    fake_id = uuid.uuid4()
    res = client.get(f"/api/employee/policies/{fake_id}", cookies={"session_id": token})
    assert res.status_code == 404


def test_14_invalid_version_id_returns_404(db):
    """14. Non-existent version ID on document retrieval returns 404."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-V-404-{unique_suffix}",
        title="Valid Policy",
        status=PolicyStatus.ACTIVE
    )
    db.add(p)
    db.commit()

    fake_v_id = uuid.uuid4()
    res = client.get(f"/api/employee/policies/{p.id}/versions/{fake_v_id}/file", cookies={"session_id": token})
    assert res.status_code == 404


def test_15_draft_policy_id_returns_404_for_employee(db):
    """15. Direct ID lookup of a DRAFT policy returns 404 (IDOR protection)."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-DRAFT-IDOR-{unique_suffix}",
        title="Draft Confidential",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    res = client.get(f"/api/employee/policies/{p.id}", cookies={"session_id": token})
    assert res.status_code == 404


def test_16_published_policy_id_returns_404_for_employee(db):
    """16. Direct ID lookup of a PUBLISHED policy returns 404."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-PUB-IDOR-{unique_suffix}",
        title="Published Pending",
        status=PolicyStatus.PUBLISHED
    )
    db.add(p)
    db.commit()

    res = client.get(f"/api/employee/policies/{p.id}", cookies={"session_id": token})
    assert res.status_code == 404


def test_17_archived_policy_id_returns_404_for_employee(db):
    """17. Direct ID lookup of an ARCHIVED policy returns 404."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-ARCH-IDOR-{unique_suffix}",
        title="Archived Outdated",
        status=PolicyStatus.ARCHIVED
    )
    db.add(p)
    db.commit()

    res = client.get(f"/api/employee/policies/{p.id}", cookies={"session_id": token})
    assert res.status_code == 404


# ==============================================================================
# 18-22: Authorization Boundaries (Customer 403, Unverified 403, Unauth 401)
# ==============================================================================

def test_18_customer_receives_403_on_employee_policy_list(db):
    """18. Customer receives 403 Forbidden on employee policy catalog."""
    cust, token = _create_user(db, Role.CUSTOMER.value, OnboardingStatus.COMPLETED.value)
    res = client.get("/api/employee/policies", cookies={"session_id": token})
    assert res.status_code == 403


def test_19_customer_receives_403_on_employee_policy_detail(db):
    """19. Customer receives 403 on employee policy detail endpoint."""
    cust, token = _create_user(db, Role.CUSTOMER.value, OnboardingStatus.COMPLETED.value)
    fake_id = uuid.uuid4()
    res = client.get(f"/api/employee/policies/{fake_id}", cookies={"session_id": token})
    assert res.status_code == 403


def test_20_customer_receives_403_on_document_file(db):
    """20. Customer receives 403 on employee document file access."""
    cust, token = _create_user(db, Role.CUSTOMER.value, OnboardingStatus.COMPLETED.value)
    p_id = uuid.uuid4()
    v_id = uuid.uuid4()
    res = client.get(f"/api/employee/policies/{p_id}/versions/{v_id}/file", cookies={"session_id": token})
    assert res.status_code == 403


def test_21_unverified_employee_receives_403(db):
    """21. Employee with pending verification receives 403."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.PENDING_VERIFICATION.value)
    res = client.get("/api/employee/policies", cookies={"session_id": token})
    assert res.status_code == 403
    assert "pending approval" in res.text.lower() or "restricted" in res.text.lower()


def test_22_unauthenticated_request_receives_401(db):
    """22. Unauthenticated request receives 401 Unauthorized."""
    res = client.get("/api/employee/policies")
    assert res.status_code == 401


# ==============================================================================
# 23-29: Security Boundary — Employees CANNOT Mutate Policies
# ==============================================================================

def test_23_employee_cannot_create_policy(db):
    """23. Employee cannot create policy via Admin API (receives 403)."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    res = client.post("/api/admin/policies", json={"policy_code": "POL-HACK", "title": "Hack"}, cookies={"session_id": token})
    assert res.status_code == 403


def test_24_employee_cannot_modify_policy_metadata(db):
    """24. Employee cannot modify policy metadata (receives 403)."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    fake_id = uuid.uuid4()
    res = client.patch(f"/api/admin/policies/{fake_id}", json={"title": "Hacked Title"}, cookies={"session_id": token})
    assert res.status_code == 403


def test_25_employee_cannot_upload_policy_version(db):
    """25. Employee cannot upload a policy version document."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    fake_id = uuid.uuid4()
    pdf_bytes = make_test_pdf_bytes(1)
    res = client.post(
        f"/api/admin/policies/{fake_id}/versions/upload",
        files={"file": ("hack.pdf", pdf_bytes, "application/pdf")},
        cookies={"session_id": token}
    )
    assert res.status_code == 403


def test_26_employee_cannot_publish_policy(db):
    """26. Employee cannot publish policy."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    fake_id = uuid.uuid4()
    res = client.post(f"/api/admin/policies/{fake_id}/publish", cookies={"session_id": token})
    assert res.status_code == 403


def test_27_employee_cannot_activate_policy(db):
    """27. Employee cannot activate policy."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    fake_id = uuid.uuid4()
    res = client.post(f"/api/admin/policies/{fake_id}/activate", cookies={"session_id": token})
    assert res.status_code == 403


def test_28_employee_cannot_supersede_policy(db):
    """28. Employee cannot supersede policy."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    fake_id = uuid.uuid4()
    res = client.post(f"/api/admin/policies/{fake_id}/supersede?new_version_id={uuid.uuid4()}", cookies={"session_id": token})
    assert res.status_code == 403


def test_29_employee_cannot_archive_policy(db):
    """29. Employee cannot archive policy."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    fake_id = uuid.uuid4()
    res = client.post(f"/api/admin/policies/{fake_id}/archive", cookies={"session_id": token})
    assert res.status_code == 403


def test_30_raw_filesystem_paths_never_exposed(db):
    """30. Responses never leak raw local filesystem storage paths."""
    emp, token = _create_user(db, Role.EMPLOYEE.value, OnboardingStatus.COMPLETED.value)
    unique_suffix = uuid.uuid4().hex[:6].upper()

    p = Policy(
        policy_code=f"POL-PATH-SEC-{unique_suffix}",
        title="Path Security Policy",
        status=PolicyStatus.ACTIVE
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(1)
    PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=p.id,
        filename="secure.pdf",
        file_bytes=pdf_bytes
    )

    detail_res = client.get(f"/api/employee/policies/{p.id}", cookies={"session_id": token})
    assert detail_res.status_code == 200
    detail_str = detail_res.text
    assert "C:\\" not in detail_str
    assert "D:\\" not in detail_str
    assert "policy_docs" not in detail_str

    hist_res = client.get(f"/api/employee/policies/{p.id}/history", cookies={"session_id": token})
    assert hist_res.status_code == 200
    hist_str = hist_res.text
    assert "C:\\" not in hist_str
    assert "D:\\" not in hist_str
    assert "policy_docs" not in hist_str
