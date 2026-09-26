"""
Employee Policy Service (M08.7)
===============================
Provides safe, read-only policy catalog discovery, applicability matching,
and controlled document retrieval for verified employees.

Enforces:
- ACTIVE status filter (DRAFT, PUBLISHED, ARCHIVED, SUPERSEDED excluded from catalog).
- Read-only projection (no admin mutation capabilities).
- Controlled file access with zero filesystem path leakage.
- Strict IDOR and role boundary enforcement.
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from uuid import UUID
from pathlib import Path
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_

from app.db.models import (
    User, Role, OnboardingStatus, Policy, PolicyVersion,
    PolicyStatus, PolicyApplicability, RegulatoryAuthority
)
from app.services.policy_metadata_service import parse_uuid
from app.services.policy_file_service import PolicyFileService
from app.services.policy_lifecycle_service import PolicyLifecycleService


class EmployeePolicyError(Exception):
    """Base exception for Employee Policy operations."""
    pass


class EmployeePolicyNotFoundError(EmployeePolicyError):
    """Raised when an active policy or requested version is not found."""
    pass


class EmployeePolicyAccessDeniedError(EmployeePolicyError):
    """Raised when an employee fails verification or access criteria."""
    pass


class EmployeePolicyService:
    """Service handling verified employee policy catalog queries."""

    @classmethod
    def list_active_policies(
        cls,
        db: Session,
        search: Optional[str] = None,
        category: Optional[str] = None,
        policy_type: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        institution: Optional[str] = None,
        regulatory_authority_id: Optional[Union[str, UUID]] = None,
        loan_type: Optional[str] = None,
        department: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Retrieves a paginated list of ACTIVE policies matching search and filter criteria.
        Excludes all non-ACTIVE policies (DRAFT, PUBLISHED, ARCHIVED, SUPERSEDED).
        """
        query = db.query(Policy).options(
            joinedload(Policy.current_version),
            joinedload(Policy.regulatory_authority),
            joinedload(Policy.applicabilities)
        ).filter(Policy.status == PolicyStatus.ACTIVE)

        if search and search.strip():
            s = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(Policy.title).like(s),
                    func.lower(Policy.policy_code).like(s),
                    func.lower(Policy.description).like(s)
                )
            )

        if category and category.strip() and category.strip().upper() != "ALL":
            query = query.filter(func.lower(Policy.category) == category.strip().lower())

        if policy_type and policy_type.strip() and policy_type.strip().upper() != "ALL":
            query = query.filter(func.lower(Policy.policy_type) == policy_type.strip().lower())

        if jurisdiction and jurisdiction.strip():
            query = query.filter(func.lower(Policy.jurisdiction) == jurisdiction.strip().lower())

        if institution and institution.strip():
            query = query.filter(func.lower(Policy.institution) == institution.strip().lower())

        if regulatory_authority_id:
            auth_id = parse_uuid(regulatory_authority_id, "regulatory_authority_id")
            query = query.filter(Policy.regulatory_authority_id == auth_id)

        # Dimension filtering via applicabilities
        if loan_type and loan_type.strip():
            lt = loan_type.strip().lower()
            query = query.filter(
                or_(
                    ~Policy.applicabilities.any(),
                    Policy.applicabilities.any(func.lower(PolicyApplicability.loan_type) == lt)
                )
            )

        if department and department.strip():
            dept = department.strip().lower()
            query = query.filter(
                or_(
                    ~Policy.applicabilities.any(),
                    Policy.applicabilities.any(func.lower(PolicyApplicability.department) == dept)
                )
            )

        total = query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        policies = query.order_by(Policy.created_at.desc(), Policy.updated_at.desc().nullslast()).offset((page - 1) * page_size).limit(page_size).all()

        items = []
        for p in policies:
            cv = p.current_version
            ra = p.regulatory_authority
            items.append({
                "id": str(p.id),
                "policy_code": p.policy_code,
                "title": p.title,
                "description": p.description,
                "category": p.category,
                "policy_type": p.policy_type,
                "institution": p.institution,
                "jurisdiction": p.jurisdiction,
                "status": p.status.value,
                "current_version_id": str(cv.id) if cv else None,
                "current_version_number": cv.version_number if cv else None,
                "effective_from": cv.effective_from if cv else None,
                "effective_to": cv.effective_to if cv else None,
                "regulatory_authority": {
                    "id": str(ra.id),
                    "name": ra.name,
                    "short_name": ra.short_name,
                    "authority_type": ra.authority_type,
                    "website_url": ra.website_url
                } if ra else None,
                "updated_at": p.updated_at or p.created_at
            })

        return items, total, total_pages

    @classmethod
    def get_active_policy_detail(
        cls,
        db: Session,
        policy_id: Union[str, UUID]
    ) -> Dict[str, Any]:
        """
        Retrieves detailed information for an ACTIVE policy.
        Returns 404-safe exception if policy does not exist or is not ACTIVE.
        """
        parsed_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).options(
            joinedload(Policy.current_version),
            joinedload(Policy.regulatory_authority),
            joinedload(Policy.applicabilities)
        ).filter(
            Policy.id == parsed_id,
            Policy.status == PolicyStatus.ACTIVE
        ).first()

        if not policy:
            raise EmployeePolicyNotFoundError(f"Active policy '{policy_id}' not found.")

        cv = policy.current_version
        ra = policy.regulatory_authority

        apps = [
            {
                "id": str(a.id),
                "institution": a.institution,
                "jurisdiction": a.jurisdiction,
                "loan_type": a.loan_type,
                "department": a.department,
                "created_at": a.created_at
            }
            for a in policy.applicabilities
        ]

        return {
            "id": str(policy.id),
            "policy_code": policy.policy_code,
            "title": policy.title,
            "description": policy.description,
            "category": policy.category,
            "policy_type": policy.policy_type,
            "institution": policy.institution,
            "jurisdiction": policy.jurisdiction,
            "status": policy.status.value,
            "current_version": {
                "id": str(cv.id),
                "version_number": cv.version_number,
                "changelog": cv.changelog,
                "page_count": cv.page_count,
                "file_size_bytes": cv.file_size_bytes,
                "file_size": cv.file_size_bytes,
                "effective_from": cv.effective_from,
                "effective_to": cv.effective_to,
                "has_file": bool(cv.file_url or cv.file_size_bytes),
                "status": policy.status.value,
                "published_at": getattr(cv, "published_at", None) or cv.created_at
            } if cv else None,
            "current_version_id": str(cv.id) if cv else None,
            "current_version_number": cv.version_number if cv else None,
            "current_version_changelog": cv.changelog if cv else None,
            "current_version_page_count": cv.page_count if cv else None,
            "current_version_file_size_bytes": cv.file_size_bytes if cv else None,
            "effective_from": cv.effective_from if cv else None,
            "effective_to": cv.effective_to if cv else None,
            "regulatory_authority": {
                "id": str(ra.id),
                "name": ra.name,
                "short_name": ra.short_name,
                "authority_type": ra.authority_type,
                "jurisdiction": ra.jurisdiction,
                "website_url": ra.website_url,
                "description": ra.description
            } if ra else None,
            "applicabilities": apps,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at or policy.created_at
        }

    @classmethod
    def get_active_policy_history(
        cls,
        db: Session,
        policy_id: Union[str, UUID]
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the version history for an ACTIVE policy.
        Filters out raw filesystem paths and internal administrative details.
        """
        parsed_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).filter(
            Policy.id == parsed_id,
            Policy.status == PolicyStatus.ACTIVE
        ).first()

        if not policy:
            raise EmployeePolicyNotFoundError(f"Active policy '{policy_id}' not found.")

        raw_history = PolicyLifecycleService.get_policy_version_history(db=db, policy_id=parsed_id)
        
        # Project employee-safe version history
        safe_history = []
        for v in raw_history:
            safe_history.append({
                "id": v["id"],
                "version_number": v["version_number"],
                "status_context": v.get("status_context"),
                "status": v.get("status_context") or policy.status.value,
                "changelog": v.get("changelog"),
                "file_size_bytes": v.get("file_size_bytes"),
                "file_size": v.get("file_size_bytes"),
                "page_count": v.get("page_count"),
                "effective_from": v.get("effective_from"),
                "effective_to": v.get("effective_to"),
                "has_file": bool(v.get("file_size_bytes") or v.get("has_file")),
                "created_at": v.get("created_at"),
                "published_at": v.get("published_at") or v.get("created_at"),
                "download_url": f"/api/employee/policies/{policy.id}/versions/{v['id']}/file"
            })

        return safe_history

    @classmethod
    def get_active_policy_version_file(
        cls,
        db: Session,
        policy_id: Union[str, UUID],
        version_id: Union[str, UUID]
    ) -> Tuple[Path, PolicyVersion]:
        """
        Validates that the policy is ACTIVE, the requested version belongs to it,
        and returns the physical file path safely via PolicyFileService.
        """
        parsed_policy_id = parse_uuid(policy_id, "policy_id")
        parsed_version_id = parse_uuid(version_id, "version_id")

        policy = db.query(Policy).filter(
            Policy.id == parsed_policy_id,
            Policy.status == PolicyStatus.ACTIVE
        ).first()

        if not policy:
            raise EmployeePolicyNotFoundError(f"Active policy '{policy_id}' not found.")

        try:
            file_path, version = PolicyFileService.get_policy_version_file(
                db=db,
                policy_id=parsed_policy_id,
                version_id=parsed_version_id
            )
            return file_path, version
        except Exception as e:
            raise EmployeePolicyNotFoundError(str(e))
