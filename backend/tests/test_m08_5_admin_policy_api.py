"""
M08.5 Test Suite — Admin Management APIs & RBAC for Policy & Regulation Management

Covers:
- Regulatory Authority APIs (1-5)
- Policy Metadata APIs (6-9)
- Policy Applicability APIs (10-12)
- Policy Version / File Ingestion APIs (13-15)
- Policy Lifecycle APIs (16-19)
- Invalid Lifecycle Transition (20)
- RBAC Enforcement (21-25)
- Invalid Entity IDs (26-28)
- Duplicate Constraints (29-30)
- File Upload Validation (31-32)
- Filtering and Pagination (33-35)
- Version Metadata Immutability (36-37)
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
    Policy, PolicyVersion, PolicyStatus, RegulatoryAuthority, PolicyApplicability
)
from app.core.security import create_user_session
import app.api.deps as api_deps
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
        # Clean up test policies, versions, and applicability
        test_policies = session.query(Policy).filter(Policy.policy_code.like("POL-API-%")).all()
        for p in test_policies:
            p.current_version_id = None
        session.commit()

        for p in test_policies:
            session.query(PolicyVersion).filter(PolicyVersion.policy_id == p.id).delete(synchronize_session=False)
            session.query(PolicyApplicability).filter(PolicyApplicability.policy_id == p.id).delete(synchronize_session=False)
            session.delete(p)

        session.query(RegulatoryAuthority).filter(RegulatoryAuthority.short_name.like("TEST_API_%")).delete(synchronize_session=False)

        test_users = session.query(User).filter(User.email.like("test_m08_5_%@example.com")).all()
        for u in test_users:
            session.query(DBSession).filter(DBSession.user_id == u.id).delete(synchronize_session=False)
            session.delete(u)

        session.commit()
        session.close()


def _create_user(db, role: str) -> tuple[User, str]:
    uid = uuid.uuid4()
    email = f"test_m08_5_{role.lower()}_{uid.hex[:6]}@example.com"
    user = User(
        id=uid,
        email=email,
        full_name=f"M08.5 {role} User",
        role=role,
        requested_role=role,
        onboarding_status=OnboardingStatus.COMPLETED.value,
        authentication_provider="local",
        provider_subject_id=email
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_user_session(db, user.id)
    return user, token


# ==============================================================================
# 1-5: Regulatory Authority APIs
# ==============================================================================

def test_01_admin_authority_creation(db):
    """1. Admin can create a new regulatory authority (201 Created)."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()
    payload = {
        "name": f"Reserve Bank of India Test {unique_suffix}",
        "short_name": f"TEST_API_RBI_{unique_suffix}",
        "authority_type": "CENTRAL_BANK",
        "jurisdiction": "IN",
        "website_url": "https://www.rbi.org.in",
        "description": "Central banking authority",
        "is_active": True
    }

    res = client.post("/api/admin/regulatory-authorities", json=payload, cookies={"session_id": token})
    assert res.status_code == 201
    data = res.json()
    assert data["short_name"] == f"TEST_API_RBI_{unique_suffix}"
    assert data["authority_type"] == "CENTRAL_BANK"
    assert data["is_active"] is True
    assert "id" in data


def test_02_admin_authority_listing(db):
    """2. Admin can list regulatory authorities with optional filtering."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    auth1 = RegulatoryAuthority(
        name=f"Auth 1 {unique_suffix}",
        short_name=f"TEST_API_A1_{unique_suffix}",
        authority_type="CENTRAL_BANK",
        jurisdiction="IN",
        is_active=True
    )
    auth2 = RegulatoryAuthority(
        name=f"Auth 2 {unique_suffix}",
        short_name=f"TEST_API_A2_{unique_suffix}",
        authority_type="GOVERNMENT",
        jurisdiction="US",
        is_active=False
    )
    db.add_all([auth1, auth2])
    db.commit()

    res = client.get("/api/admin/regulatory-authorities", cookies={"session_id": token})
    assert res.status_code == 200
    items = res.json()
    assert any(a["short_name"] == f"TEST_API_A1_{unique_suffix}" for a in items)
    assert any(a["short_name"] == f"TEST_API_A2_{unique_suffix}" for a in items)

    # Filter by is_active=true
    res_active = client.get("/api/admin/regulatory-authorities?is_active=true", cookies={"session_id": token})
    assert res_active.status_code == 200
    active_items = res_active.json()
    assert any(a["short_name"] == f"TEST_API_A1_{unique_suffix}" for a in active_items)
    assert not any(a["short_name"] == f"TEST_API_A2_{unique_suffix}" for a in active_items)


def test_03_admin_authority_retrieval(db):
    """3. Admin can retrieve a specific regulatory authority by ID."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    auth = RegulatoryAuthority(
        name=f"Auth Retrieval {unique_suffix}",
        short_name=f"TEST_API_RET_{unique_suffix}",
        authority_type="STATUTORY_BODY",
        is_active=True
    )
    db.add(auth)
    db.commit()

    res = client.get(f"/api/admin/regulatory-authorities/{auth.id}", cookies={"session_id": token})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(auth.id)
    assert data["short_name"] == f"TEST_API_RET_{unique_suffix}"


def test_04_admin_authority_update(db):
    """4. Admin can update authority metadata via PATCH."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    auth = RegulatoryAuthority(
        name=f"Auth PreUpdate {unique_suffix}",
        short_name=f"TEST_API_UPD_{unique_suffix}",
        authority_type="CENTRAL_BANK",
        is_active=True
    )
    db.add(auth)
    db.commit()

    patch_payload = {
        "name": f"Auth PostUpdate {unique_suffix}",
        "website_url": "https://updated-domain.example.com",
        "description": "Updated authority description"
    }

    res = client.patch(f"/api/admin/regulatory-authorities/{auth.id}", json=patch_payload, cookies={"session_id": token})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == f"Auth PostUpdate {unique_suffix}"
    assert data["website_url"] == "https://updated-domain.example.com"
    assert data["description"] == "Updated authority description"


def test_05_admin_authority_deactivation(db):
    """5. Admin can deactivate a regulatory authority."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    auth = RegulatoryAuthority(
        name=f"Auth Deactivate {unique_suffix}",
        short_name=f"TEST_API_DEACT_{unique_suffix}",
        is_active=True
    )
    db.add(auth)
    db.commit()

    res = client.post(f"/api/admin/regulatory-authorities/{auth.id}/deactivate", cookies={"session_id": token})
    assert res.status_code == 200
    assert res.json()["is_active"] is False


# ==============================================================================
# 6-9: Policy Metadata APIs
# ==============================================================================

def test_06_admin_policy_creation(db):
    """6. Admin can create a new policy in DRAFT status."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()
    payload = {
        "policy_code": f"POL-API-CREATE-{unique_suffix}",
        "title": "Digital Lending Master Policy",
        "description": "Comprehensive guidelines for digital lending operations",
        "category": "LENDING",
        "policy_type": "REGULATORY",
        "institution": "Apex Bank",
        "jurisdiction": "IN"
    }

    res = client.post("/api/admin/policies", json=payload, cookies={"session_id": token})
    assert res.status_code == 201
    data = res.json()
    assert data["policy_code"] == f"POL-API-CREATE-{unique_suffix}"
    assert data["status"] == "DRAFT"
    assert data["created_by"] == str(admin.id)
    assert data["current_version_id"] is None


def test_07_admin_policy_listing(db):
    """7. Admin can list policies with pagination."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-LIST-{unique_suffix}",
        title="Listing Test Policy",
        category="RETAIL",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    res = client.get("/api/admin/policies?page=1&page_size=10", cookies={"session_id": token})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert any(item["policy_code"] == f"POL-API-LIST-{unique_suffix}" for item in data["items"])


def test_08_admin_policy_retrieval(db):
    """8. Admin can retrieve a specific policy by ID."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-RET-{unique_suffix}",
        title="Retrieval Test Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    res = client.get(f"/api/admin/policies/{p.id}", cookies={"session_id": token})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(p.id)
    assert data["title"] == "Retrieval Test Policy"


def test_09_admin_policy_metadata_update(db):
    """9. Admin can update draft policy metadata via PATCH."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-UPD-{unique_suffix}",
        title="Old Policy Title",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    patch_payload = {
        "title": "New Updated Policy Title",
        "description": "Updated policy description via admin API",
        "category": "MORTGAGE"
    }

    res = client.patch(f"/api/admin/policies/{p.id}", json=patch_payload, cookies={"session_id": token})
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "New Updated Policy Title"
    assert data["category"] == "MORTGAGE"


# ==============================================================================
# 10-12: Policy Applicability APIs
# ==============================================================================

def test_10_admin_applicability_creation(db):
    """10. Admin can attach an applicability rule to a policy."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-APP-{unique_suffix}",
        title="Applicability Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    payload = {
        "institution": "Apex Bank",
        "jurisdiction": "IN",
        "loan_type": "HOME_LOAN",
        "department": "Credit Risk"
    }

    res = client.post(f"/api/admin/policies/{p.id}/applicability", json=payload, cookies={"session_id": token})
    assert res.status_code == 201
    data = res.json()
    assert data["policy_id"] == str(p.id)
    assert data["loan_type"] == "HOME_LOAN"


def test_11_admin_applicability_listing(db):
    """11. Admin can list all applicability rules for a policy."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-APPLIST-{unique_suffix}",
        title="Applicability Listing Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    app_rule = PolicyApplicability(
        policy_id=p.id,
        institution="Bank of India",
        jurisdiction="IN",
        loan_type="PERSONAL_LOAN"
    )
    db.add(app_rule)
    db.commit()

    res = client.get(f"/api/admin/policies/{p.id}/applicability", cookies={"session_id": token})
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["loan_type"] == "PERSONAL_LOAN"


def test_12_admin_applicability_deletion(db):
    """12. Admin can delete an applicability rule."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-APPDEL-{unique_suffix}",
        title="Applicability Deletion Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    app_rule = PolicyApplicability(
        policy_id=p.id,
        institution="Commercial Bank",
        loan_type="AUTO_LOAN"
    )
    db.add(app_rule)
    db.commit()

    res = client.delete(f"/api/admin/policies/{p.id}/applicability/{app_rule.id}", cookies={"session_id": token})
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"

    # Verify deleted from DB
    remaining = db.query(PolicyApplicability).filter(PolicyApplicability.id == app_rule.id).first()
    assert remaining is None


# ==============================================================================
# 13-15: Policy Version / File Ingestion APIs
# ==============================================================================

def test_13_policy_version_upload(db):
    """13. Admin can upload a policy source document via API."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-UPDOC-{unique_suffix}",
        title="Upload Test Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=2, text="RBI Circular 2026")
    res = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("rbi_circular.pdf", pdf_bytes, "application/pdf")},
        data={"changelog": "Initial upload of regulatory circular"},
        cookies={"session_id": token}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["policy_id"] == str(p.id)
    assert data["version_number"] == "1"
    assert data["page_count"] == 2
    assert not data["file_url"].startswith("C:")
    assert not data["file_url"].startswith("/")


def test_14_policy_version_retrieval(db):
    """14. Admin can retrieve the stored policy document file."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-GETDOC-{unique_suffix}",
        title="Document Retrieval Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=1, text="Test Document File")
    upload_res = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        cookies={"session_id": token}
    )
    version_id = upload_res.json()["id"]

    get_res = client.get(
        f"/api/admin/policies/{p.id}/versions/{version_id}/file",
        cookies={"session_id": token}
    )
    assert get_res.status_code == 200
    assert get_res.content == pdf_bytes
    assert get_res.headers["content-type"] == "application/pdf"


def test_15_policy_version_history(db):
    """15. Admin can retrieve version history ordered descending."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-HIST-{unique_suffix}",
        title="History Test Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    pdf1 = make_test_pdf_bytes(page_count=1, text="V1")
    pdf2 = make_test_pdf_bytes(page_count=2, text="V2")

    client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("v1.pdf", pdf1, "application/pdf")},
        cookies={"session_id": token}
    )
    client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("v2.pdf", pdf2, "application/pdf")},
        cookies={"session_id": token}
    )

    res = client.get(f"/api/admin/policies/{p.id}/history", cookies={"session_id": token})
    assert res.status_code == 200
    history = res.json()
    assert len(history) == 2
    assert history[0]["version_number"] == "2"
    assert history[1]["version_number"] == "1"


# ==============================================================================
# 16-20: Policy Lifecycle APIs
# ==============================================================================

def test_16_publish_endpoint(db):
    """16. Admin can publish a draft policy (DRAFT -> PUBLISHED)."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-PUB-{unique_suffix}",
        title="Publishing API Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=1)
    client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        cookies={"session_id": token}
    )

    res = client.post(f"/api/admin/policies/{p.id}/publish", cookies={"session_id": token})
    assert res.status_code == 200
    assert res.json()["status"] == "PUBLISHED"


def test_17_activate_endpoint(db):
    """17. Admin can activate a published policy version (PUBLISHED -> ACTIVE)."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-ACT-{unique_suffix}",
        title="Activation API Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=1)
    up_res = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        data={"effective_from": datetime.now(timezone.utc).isoformat()},
        cookies={"session_id": token}
    )
    v_id = up_res.json()["id"]

    client.post(f"/api/admin/policies/{p.id}/publish", cookies={"session_id": token})

    res = client.post(f"/api/admin/policies/{p.id}/activate?version_id={v_id}", cookies={"session_id": token})
    assert res.status_code == 200
    assert res.json()["status"] == "ACTIVE"
    assert res.json()["current_version_id"] == v_id


def test_18_supersede_endpoint(db):
    """18. Admin can supersede an active policy with a new version (ACTIVE -> SUPERSEDED)."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-SUP-{unique_suffix}",
        title="Supersede API Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    now = datetime.now(timezone.utc)
    pdf1 = make_test_pdf_bytes(page_count=1, text="V1")
    pdf2 = make_test_pdf_bytes(page_count=2, text="V2")

    up1 = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("v1.pdf", pdf1, "application/pdf")},
        data={"effective_from": now.isoformat()},
        cookies={"session_id": token}
    )
    v1_id = up1.json()["id"]

    client.post(f"/api/admin/policies/{p.id}/publish", cookies={"session_id": token})
    client.post(f"/api/admin/policies/{p.id}/activate?version_id={v1_id}", cookies={"session_id": token})

    up2 = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("v2.pdf", pdf2, "application/pdf")},
        data={"effective_from": (now + timedelta(days=30)).isoformat()},
        cookies={"session_id": token}
    )
    v2_id = up2.json()["id"]

    res = client.post(f"/api/admin/policies/{p.id}/supersede?new_version_id={v2_id}", cookies={"session_id": token})
    assert res.status_code == 200
    assert res.json()["status"] == "SUPERSEDED"
    assert res.json()["current_version_id"] == v2_id


def test_19_archive_endpoint(db):
    """19. Admin can archive a policy (SUPERSEDED -> ARCHIVED)."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-ARCH-{unique_suffix}",
        title="Archive API Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    # Draft archival
    res = client.post(f"/api/admin/policies/{p.id}/archive", cookies={"session_id": token})
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


def test_20_invalid_lifecycle_transition(db):
    """20. Invalid lifecycle transition (e.g. DRAFT -> ACTIVE without publish) is rejected (400)."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-INVLC-{unique_suffix}",
        title="Invalid Transition Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=1)
    up_res = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        data={"effective_from": datetime.now(timezone.utc).isoformat()},
        cookies={"session_id": token}
    )
    v_id = up_res.json()["id"]

    # Directly activate draft without publish -> 400 Bad Request
    res = client.post(f"/api/admin/policies/{p.id}/activate?version_id={v_id}", cookies={"session_id": token})
    assert res.status_code == 400
    assert "Invalid policy lifecycle transition" in res.json()["detail"]


# ==============================================================================
# 21-25: RBAC Enforcement
# ==============================================================================

def test_21_customer_receives_403(db):
    """21. Authenticated customer receives 403 Forbidden."""
    customer, token = _create_user(db, Role.CUSTOMER.value)

    res = client.get("/api/admin/policies", cookies={"session_id": token})
    assert res.status_code == 403

    res_auth = client.get("/api/admin/regulatory-authorities", cookies={"session_id": token})
    assert res_auth.status_code == 403


def test_22_employee_receives_403(db):
    """22. Authenticated employee receives 403 Forbidden."""
    employee, token = _create_user(db, Role.EMPLOYEE.value)

    res = client.get("/api/admin/policies", cookies={"session_id": token})
    assert res.status_code == 403

    res_auth = client.post(
        "/api/admin/regulatory-authorities",
        json={"name": "Test", "short_name": "TEST"},
        cookies={"session_id": token}
    )
    assert res_auth.status_code == 403


def test_23_unauthenticated_receives_401(db):
    """23. Unauthenticated request receives 401 Unauthorized."""
    res = client.get("/api/admin/policies")
    assert res.status_code == 401

    res_auth = client.get("/api/admin/regulatory-authorities")
    assert res_auth.status_code == 401


def test_24_admin_without_permission_receives_403(db, monkeypatch):
    """24. User without ADMIN_POLICY_MANAGEMENT permission receives 403 Forbidden."""
    admin, token = _create_user(db, Role.ADMIN.value)

    # Monkeypatch ROLE_PERMISSIONS to temporarily revoke ADMIN_POLICY_MANAGEMENT
    original_perms = api_deps.ROLE_PERMISSIONS.copy()
    tampered_perms = original_perms.copy()
    tampered_perms[Role.ADMIN.value] = {"ADMIN_USER_MANAGEMENT"}
    monkeypatch.setattr(api_deps, "ROLE_PERMISSIONS", tampered_perms)

    res = client.get("/api/admin/policies", cookies={"session_id": token})
    assert res.status_code == 403


def test_25_authorized_admin_succeeds(db):
    """25. Authorized Admin with ADMIN_POLICY_MANAGEMENT succeeds."""
    admin, token = _create_user(db, Role.ADMIN.value)

    res = client.get("/api/admin/policies", cookies={"session_id": token})
    assert res.status_code == 200


# ==============================================================================
# 26-28: Entity ID Handling
# ==============================================================================

def test_26_invalid_policy_id_returns_404(db):
    """26. Non-existent policy ID returns 404 Not Found."""
    admin, token = _create_user(db, Role.ADMIN.value)
    non_existent = uuid.uuid4()

    res = client.get(f"/api/admin/policies/{non_existent}", cookies={"session_id": token})
    assert res.status_code == 404


def test_27_invalid_authority_id_returns_404(db):
    """27. Non-existent regulatory authority ID returns 404 Not Found."""
    admin, token = _create_user(db, Role.ADMIN.value)
    non_existent = uuid.uuid4()

    res = client.get(f"/api/admin/regulatory-authorities/{non_existent}", cookies={"session_id": token})
    assert res.status_code == 404


def test_28_invalid_version_id_returns_404(db):
    """28. Non-existent version ID returns 404 Not Found."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-NOVER-{unique_suffix}",
        title="No Version Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    non_existent = uuid.uuid4()
    res = client.get(f"/api/admin/policies/{p.id}/versions/{non_existent}/file", cookies={"session_id": token})
    assert res.status_code == 404


# ==============================================================================
# 29-30: Duplicate Constraints
# ==============================================================================

def test_29_duplicate_policy_code_rejected(db):
    """29. Duplicate policy code returns 409 Conflict."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()
    code = f"POL-API-DUP-{unique_suffix}"

    payload = {"policy_code": code, "title": "First Policy"}
    res1 = client.post("/api/admin/policies", json=payload, cookies={"session_id": token})
    assert res1.status_code == 201

    payload_dup = {"policy_code": code, "title": "Duplicate Policy Code"}
    res2 = client.post("/api/admin/policies", json=payload_dup, cookies={"session_id": token})
    assert res2.status_code == 409


def test_30_duplicate_policy_version_hash_rejected(db):
    """30. Duplicate policy version document hash within same policy returns 409 Conflict."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-DUPHASH-{unique_suffix}",
        title="Duplicate Hash Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=1, text="Identical Document Stream")
    res1 = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("v1.pdf", pdf_bytes, "application/pdf")},
        cookies={"session_id": token}
    )
    assert res1.status_code == 201

    # Upload exact same bytes again to the same policy
    res2 = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("v2.pdf", pdf_bytes, "application/pdf")},
        cookies={"session_id": token}
    )
    assert res2.status_code == 409


# ==============================================================================
# 31-32: File Upload & Retrieval Security
# ==============================================================================

def test_31_invalid_file_upload_rejected(db):
    """31. Invalid file upload (e.g. empty or unsupported extension) returns 400 Bad Request."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-INVDOC-{unique_suffix}",
        title="Invalid File Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    # Empty file
    res_empty = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        cookies={"session_id": token}
    )
    assert res_empty.status_code == 400

    # Unsupported extension
    res_ext = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("script.exe", b"executable code", "application/octet-stream")},
        cookies={"session_id": token}
    )
    assert res_ext.status_code == 400


def test_32_unauthorized_file_retrieval(db):
    """32. Customer and employee cannot retrieve policy document files (403 Forbidden)."""
    admin, admin_token = _create_user(db, Role.ADMIN.value)
    customer, cust_token = _create_user(db, Role.CUSTOMER.value)
    employee, emp_token = _create_user(db, Role.EMPLOYEE.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-FILESEC-{unique_suffix}",
        title="File Security Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=1)
    up = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        cookies={"session_id": admin_token}
    )
    v_id = up.json()["id"]

    # Customer forbidden
    res_c = client.get(f"/api/admin/policies/{p.id}/versions/{v_id}/file", cookies={"session_id": cust_token})
    assert res_c.status_code == 403

    # Employee forbidden
    res_e = client.get(f"/api/admin/policies/{p.id}/versions/{v_id}/file", cookies={"session_id": emp_token})
    assert res_e.status_code == 403

    # Unauthenticated unauthorized
    res_anon = client.get(f"/api/admin/policies/{p.id}/versions/{v_id}/file")
    assert res_anon.status_code == 401


# ==============================================================================
# 33-35: Filtering, Pagination, and Search
# ==============================================================================

def test_33_policy_filtering_by_status_and_category(db):
    """33. Policy list filtering by status and category."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p1 = Policy(policy_code=f"POL-API-F1-{unique_suffix}", title="Lending Draft", category="LENDING", status=PolicyStatus.DRAFT)
    p2 = Policy(policy_code=f"POL-API-F2-{unique_suffix}", title="Risk Published", category="RISK", status=PolicyStatus.PUBLISHED)
    db.add_all([p1, p2])
    db.commit()

    res = client.get("/api/admin/policies?status=DRAFT&category=LENDING", cookies={"session_id": token})
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(p["policy_code"] == f"POL-API-F1-{unique_suffix}" for p in items)
    assert not any(p["policy_code"] == f"POL-API-F2-{unique_suffix}" for p in items)


def test_34_policy_search_by_code_and_title(db):
    """34. Policy list search by title keyword or policy code."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p1 = Policy(policy_code=f"POL-API-SRCH1-{unique_suffix}", title="Anti Money Laundering Directive", status=PolicyStatus.DRAFT)
    p2 = Policy(policy_code=f"POL-API-SRCH2-{unique_suffix}", title="Credit Card Issuance Rules", status=PolicyStatus.DRAFT)
    db.add_all([p1, p2])
    db.commit()

    res = client.get("/api/admin/policies?search=Laundering", cookies={"session_id": token})
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(p["policy_code"] == f"POL-API-SRCH1-{unique_suffix}" for p in items)
    assert not any(p["policy_code"] == f"POL-API-SRCH2-{unique_suffix}" for p in items)


def test_35_policy_pagination_limits(db):
    """35. Pagination handles page and page_size limits safely."""
    admin, token = _create_user(db, Role.ADMIN.value)

    res = client.get("/api/admin/policies?page=1&page_size=2", cookies={"session_id": token})
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


# ==============================================================================
# 36-37: Version Metadata Updates & Immutability Enforcement
# ==============================================================================

def test_36_version_metadata_update_allowed_fields(db):
    """36. Version changelog and effective dates can be updated via PATCH."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-VMETA-{unique_suffix}",
        title="Version Update Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=1)
    up = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        cookies={"session_id": token}
    )
    v_id = up.json()["id"]

    new_from = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    new_to = (datetime.now(timezone.utc) + timedelta(days=200)).isoformat()
    patch_res = client.patch(
        f"/api/admin/policies/{p.id}/versions/{v_id}",
        json={"changelog": "Updated changelog note", "effective_from": new_from, "effective_to": new_to},
        cookies={"session_id": token}
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["changelog"] == "Updated changelog note"


def test_37_version_immutable_fields_rejected(db):
    """37. Attempts to alter immutable fields (file_hash, file_url, etc.) on version are rejected (409)."""
    admin, token = _create_user(db, Role.ADMIN.value)
    unique_suffix = uuid.uuid4().hex[:4].upper()

    p = Policy(
        policy_code=f"POL-API-IMMUT-{unique_suffix}",
        title="Immutability Policy",
        status=PolicyStatus.DRAFT
    )
    db.add(p)
    db.commit()

    pdf_bytes = make_test_pdf_bytes(page_count=1)
    up = client.post(
        f"/api/admin/policies/{p.id}/versions/upload",
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        cookies={"session_id": token}
    )
    v_id = up.json()["id"]

    # Attempt to modify file_hash
    res = client.patch(
        f"/api/admin/policies/{p.id}/versions/{v_id}",
        json={"file_hash": "tampered_fake_hash"},
        cookies={"session_id": token}
    )
    assert res.status_code == 409
    assert "strictly immutable" in res.json()["detail"]
