"""
M08.2 — Regulatory Authority & Policy Metadata Service

Provides service-layer business logic and validation for:
1. Regulatory Authorities
2. Policy Metadata
3. Policy Applicability Rules
4. Policy Source Metadata
"""

from typing import Optional, List, Dict, Any, Union, Set
from uuid import UUID
from datetime import datetime, timezone
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import (
    Policy,
    PolicyStatus,
    RegulatoryAuthority,
    PolicyApplicability,
    User
)


# ==============================================================================
# Domain Exceptions
# ==============================================================================

class PolicyMetadataError(Exception):
    """Base exception for policy metadata service errors."""
    pass


class PolicyMetadataValidationError(PolicyMetadataError):
    """Raised when metadata validation fails (e.g. missing fields, invalid formats)."""
    pass


class PolicyMetadataNotFoundError(PolicyMetadataError):
    """Raised when a requested policy or regulatory authority is not found."""
    pass


class PolicyMetadataConflictError(PolicyMetadataError):
    """Raised when a unique constraint or conflict occurs (e.g. duplicate code)."""
    pass


# ==============================================================================
# Constants & Validation Helpers
# ==============================================================================

VALID_AUTHORITY_TYPES: Set[str] = {
    "CENTRAL_BANK",
    "GOVERNMENT",
    "STATUTORY_BODY",
    "INTERNAL",
    "OTHER",
}

MAX_NAME_LENGTH = 255
MAX_SHORT_NAME_LENGTH = 50
MAX_POLICY_CODE_LENGTH = 100
MAX_TITLE_LENGTH = 255


def parse_uuid(val: Union[str, UUID], field_name: str = "id") -> UUID:
    """Validate and convert value to a UUID instance."""
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val).strip())
    except (ValueError, AttributeError, TypeError):
        raise PolicyMetadataValidationError(f"Invalid {field_name} format: must be a valid UUID.")


def normalize_string(val: Optional[str]) -> Optional[str]:
    """Strip leading/trailing whitespace and return None if string is empty."""
    if val is None:
        return None
    trimmed = str(val).strip()
    return trimmed if trimmed else None


def validate_and_normalize_url(url: Optional[str]) -> Optional[str]:
    """
    Validate that a URL is well-formed with http or https scheme.
    Does NOT make outbound network requests or check domain existence.
    """
    if not url:
        return None
    trimmed = url.strip()
    if not trimmed:
        return None

    if any(c.isspace() for c in trimmed):
        raise PolicyMetadataValidationError("Website URL domain cannot contain whitespace.")

    try:
        parsed = urlparse(trimmed)
    except Exception:
        raise PolicyMetadataValidationError(f"Malformed URL: '{url}'.")

    if parsed.scheme.lower() not in ("http", "https"):
        raise PolicyMetadataValidationError("Website URL must have an http or https protocol scheme.")
    if not parsed.netloc or not parsed.hostname:
        raise PolicyMetadataValidationError("Website URL must include a valid host / network location.")

    return trimmed


# ==============================================================================
# Regulatory Authority Service
# ==============================================================================

class RegulatoryAuthorityService:
    """Service for managing regulatory authority definitions and lifecycle."""

    @staticmethod
    def create_authority(
        db: Session,
        name: str,
        short_name: str,
        authority_type: str = "CENTRAL_BANK",
        jurisdiction: Optional[str] = None,
        website_url: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True
    ) -> RegulatoryAuthority:
        """Create a new regulatory authority with strict validation."""
        norm_name = normalize_string(name)
        if not norm_name:
            raise PolicyMetadataValidationError("Authority name is required.")
        if len(norm_name) > MAX_NAME_LENGTH:
            raise PolicyMetadataValidationError(f"Authority name must not exceed {MAX_NAME_LENGTH} characters.")

        norm_short = normalize_string(short_name)
        if not norm_short:
            raise PolicyMetadataValidationError("Authority short_name is required.")
        norm_short = norm_short.upper()
        if len(norm_short) > MAX_SHORT_NAME_LENGTH:
            raise PolicyMetadataValidationError(f"Authority short_name must not exceed {MAX_SHORT_NAME_LENGTH} characters.")

        # Check short_name uniqueness (case-insensitive)
        existing = db.query(RegulatoryAuthority).filter(
            func.lower(RegulatoryAuthority.short_name) == norm_short.lower()
        ).first()
        if existing:
            raise PolicyMetadataConflictError(f"A regulatory authority with short_name '{norm_short}' already exists.")

        norm_type = (authority_type or "CENTRAL_BANK").strip().upper()
        if norm_type not in VALID_AUTHORITY_TYPES:
            raise PolicyMetadataValidationError(
                f"Invalid authority_type '{authority_type}'. Valid types are: {', '.join(sorted(VALID_AUTHORITY_TYPES))}."
            )

        norm_jurisdiction = normalize_string(jurisdiction)
        if norm_jurisdiction:
            norm_jurisdiction = norm_jurisdiction.upper()

        norm_url = validate_and_normalize_url(website_url)
        norm_desc = normalize_string(description)

        authority = RegulatoryAuthority(
            name=norm_name,
            short_name=norm_short,
            authority_type=norm_type,
            jurisdiction=norm_jurisdiction,
            website_url=norm_url,
            description=norm_desc,
            is_active=bool(is_active)
        )
        db.add(authority)
        db.commit()
        db.refresh(authority)
        return authority

    @staticmethod
    def get_authority(db: Session, authority_id: Union[str, UUID]) -> RegulatoryAuthority:
        """Retrieve a regulatory authority by ID."""
        parsed_id = parse_uuid(authority_id, "authority_id")
        authority = db.query(RegulatoryAuthority).filter(RegulatoryAuthority.id == parsed_id).first()
        if not authority:
            raise PolicyMetadataNotFoundError(f"Regulatory authority '{parsed_id}' not found.")
        return authority

    @staticmethod
    def get_authority_by_short_name(db: Session, short_name: str) -> RegulatoryAuthority:
        """Retrieve a regulatory authority by unique short_name."""
        norm_short = normalize_string(short_name)
        if not norm_short:
            raise PolicyMetadataValidationError("Short name is required.")
        authority = db.query(RegulatoryAuthority).filter(
            func.lower(RegulatoryAuthority.short_name) == norm_short.lower()
        ).first()
        if not authority:
            raise PolicyMetadataNotFoundError(f"Regulatory authority with short name '{norm_short}' not found.")
        return authority

    @staticmethod
    def list_authorities(
        db: Session,
        is_active: Optional[bool] = None,
        authority_type: Optional[str] = None,
        jurisdiction: Optional[str] = None
    ) -> List[RegulatoryAuthority]:
        """List regulatory authorities with optional filtering."""
        query = db.query(RegulatoryAuthority)
        if is_active is not None:
            query = query.filter(RegulatoryAuthority.is_active == is_active)
        if authority_type:
            query = query.filter(RegulatoryAuthority.authority_type == authority_type.strip().upper())
        if jurisdiction:
            query = query.filter(func.lower(RegulatoryAuthority.jurisdiction) == jurisdiction.strip().lower())
        return query.order_by(RegulatoryAuthority.short_name.asc()).all()

    @staticmethod
    def update_authority(
        db: Session,
        authority_id: Union[str, UUID],
        name: Optional[str] = None,
        short_name: Optional[str] = None,
        authority_type: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        website_url: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> RegulatoryAuthority:
        """Update regulatory authority metadata."""
        authority = RegulatoryAuthorityService.get_authority(db, authority_id)

        if name is not None:
            norm_name = normalize_string(name)
            if not norm_name:
                raise PolicyMetadataValidationError("Authority name cannot be empty.")
            if len(norm_name) > MAX_NAME_LENGTH:
                raise PolicyMetadataValidationError(f"Authority name must not exceed {MAX_NAME_LENGTH} characters.")
            authority.name = norm_name

        if short_name is not None:
            norm_short = normalize_string(short_name)
            if not norm_short:
                raise PolicyMetadataValidationError("Authority short_name cannot be empty.")
            norm_short = norm_short.upper()
            if len(norm_short) > MAX_SHORT_NAME_LENGTH:
                raise PolicyMetadataValidationError(f"Authority short_name must not exceed {MAX_SHORT_NAME_LENGTH} characters.")
            # Check uniqueness against other authorities
            existing = db.query(RegulatoryAuthority).filter(
                func.lower(RegulatoryAuthority.short_name) == norm_short.lower(),
                RegulatoryAuthority.id != authority.id
            ).first()
            if existing:
                raise PolicyMetadataConflictError(f"Another regulatory authority with short_name '{norm_short}' already exists.")
            authority.short_name = norm_short

        if authority_type is not None:
            norm_type = authority_type.strip().upper()
            if norm_type not in VALID_AUTHORITY_TYPES:
                raise PolicyMetadataValidationError(
                    f"Invalid authority_type '{authority_type}'. Valid types are: {', '.join(sorted(VALID_AUTHORITY_TYPES))}."
                )
            authority.authority_type = norm_type

        if jurisdiction is not None:
            norm_jur = normalize_string(jurisdiction)
            authority.jurisdiction = norm_jur.upper() if norm_jur else None

        if website_url is not None:
            authority.website_url = validate_and_normalize_url(website_url)

        if description is not None:
            authority.description = normalize_string(description)

        if is_active is not None:
            authority.is_active = bool(is_active)

        db.commit()
        db.refresh(authority)
        return authority

    @staticmethod
    def deactivate_authority(db: Session, authority_id: Union[str, UUID]) -> RegulatoryAuthority:
        """Soft-deactivate a regulatory authority."""
        authority = RegulatoryAuthorityService.get_authority(db, authority_id)
        authority.is_active = False
        db.commit()
        db.refresh(authority)
        return authority


# ==============================================================================
# Policy Metadata Service
# ==============================================================================

class PolicyMetadataService:
    """Service for managing core Policy metadata and applicability dimensions."""

    @staticmethod
    def create_policy_metadata(
        db: Session,
        policy_code: str,
        title: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        policy_type: Optional[str] = None,
        institution: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        regulatory_authority_id: Optional[Union[str, UUID]] = None,
        created_by: Optional[Union[str, UUID]] = None
    ) -> Policy:
        """
        Create a new policy record in DRAFT status with validated metadata.
        Does not activate or publish the policy (lifecycle transitions belong to M08.4).
        """
        norm_code = normalize_string(policy_code)
        if not norm_code:
            raise PolicyMetadataValidationError("Policy code is required.")
        norm_code = norm_code.upper()
        if len(norm_code) > MAX_POLICY_CODE_LENGTH:
            raise PolicyMetadataValidationError(f"Policy code must not exceed {MAX_POLICY_CODE_LENGTH} characters.")

        # Check unique constraint
        existing = db.query(Policy).filter(
            func.lower(Policy.policy_code) == norm_code.lower()
        ).first()
        if existing:
            raise PolicyMetadataConflictError(f"A policy with code '{norm_code}' already exists.")

        norm_title = normalize_string(title)
        if not norm_title:
            raise PolicyMetadataValidationError("Policy title is required.")
        if len(norm_title) > MAX_TITLE_LENGTH:
            raise PolicyMetadataValidationError(f"Policy title must not exceed {MAX_TITLE_LENGTH} characters.")

        norm_category = normalize_string(category)
        if norm_category:
            norm_category = norm_category.upper()

        norm_type = normalize_string(policy_type)
        if norm_type:
            norm_type = norm_type.upper()

        norm_inst = normalize_string(institution)
        norm_jur = normalize_string(jurisdiction)
        if norm_jur:
            norm_jur = norm_jur.upper()

        parsed_auth_id = None
        if regulatory_authority_id:
            parsed_auth_id = parse_uuid(regulatory_authority_id, "regulatory_authority_id")
            authority = db.query(RegulatoryAuthority).filter(RegulatoryAuthority.id == parsed_auth_id).first()
            if not authority:
                raise PolicyMetadataNotFoundError(f"Regulatory authority '{parsed_auth_id}' not found.")
            if not authority.is_active:
                raise PolicyMetadataValidationError(
                    f"Cannot associate policy with inactive regulatory authority '{authority.short_name}'."
                )

        parsed_creator_id = None
        if created_by:
            parsed_creator_id = parse_uuid(created_by, "created_by")
            user = db.query(User).filter(User.id == parsed_creator_id).first()
            if not user:
                raise PolicyMetadataNotFoundError(f"User '{parsed_creator_id}' specified for created_by not found.")

        policy = Policy(
            policy_code=norm_code,
            title=norm_title,
            description=normalize_string(description),
            category=norm_category,
            policy_type=norm_type,
            status=PolicyStatus.DRAFT,
            institution=norm_inst,
            jurisdiction=norm_jur,
            regulatory_authority_id=parsed_auth_id,
            created_by=parsed_creator_id
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def get_policy(db: Session, policy_id: Union[str, UUID]) -> Policy:
        """Retrieve a policy by UUID."""
        parsed_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).filter(Policy.id == parsed_id).first()
        if not policy:
            raise PolicyMetadataNotFoundError(f"Policy '{parsed_id}' not found.")
        return policy

    @staticmethod
    def get_policy_by_code(db: Session, policy_code: str) -> Policy:
        """Retrieve a policy by its unique policy_code."""
        norm_code = normalize_string(policy_code)
        if not norm_code:
            raise PolicyMetadataValidationError("Policy code is required.")
        policy = db.query(Policy).filter(
            func.lower(Policy.policy_code) == norm_code.lower()
        ).first()
        if not policy:
            raise PolicyMetadataNotFoundError(f"Policy with code '{norm_code}' not found.")
        return policy

    @staticmethod
    def list_policies(
        db: Session,
        status: Optional[PolicyStatus] = None,
        category: Optional[str] = None,
        policy_type: Optional[str] = None,
        institution: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        regulatory_authority_id: Optional[Union[str, UUID]] = None
    ) -> List[Policy]:
        """List policies with optional filtering."""
        query = db.query(Policy)
        if status:
            query = query.filter(Policy.status == status)
        if category:
            query = query.filter(func.lower(Policy.category) == category.strip().lower())
        if policy_type:
            query = query.filter(func.lower(Policy.policy_type) == policy_type.strip().lower())
        if institution:
            query = query.filter(func.lower(Policy.institution) == institution.strip().lower())
        if jurisdiction:
            query = query.filter(func.lower(Policy.jurisdiction) == jurisdiction.strip().lower())
        if regulatory_authority_id:
            auth_id = parse_uuid(regulatory_authority_id, "regulatory_authority_id")
            query = query.filter(Policy.regulatory_authority_id == auth_id)

        return query.order_by(Policy.created_at.desc()).all()

    @staticmethod
    def update_policy_metadata(
        db: Session,
        policy_id: Union[str, UUID],
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        policy_type: Optional[str] = None,
        institution: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        regulatory_authority_id: Optional[Union[str, UUID]] = None
    ) -> Policy:
        """
        Update mutable metadata on a policy.
        Enforces that metadata is only editable while in DRAFT status.
        """
        policy = PolicyMetadataService.get_policy(db, policy_id)

        # Enforce lifecycle boundary: metadata updates permitted only in DRAFT status
        if policy.status != PolicyStatus.DRAFT:
            raise PolicyMetadataValidationError(
                f"Policy metadata can only be modified while in DRAFT status. Current status is {policy.status.value}."
            )

        if title is not None:
            norm_title = normalize_string(title)
            if not norm_title:
                raise PolicyMetadataValidationError("Policy title cannot be empty.")
            if len(norm_title) > MAX_TITLE_LENGTH:
                raise PolicyMetadataValidationError(f"Policy title must not exceed {MAX_TITLE_LENGTH} characters.")
            policy.title = norm_title

        if description is not None:
            policy.description = normalize_string(description)

        if category is not None:
            norm_cat = normalize_string(category)
            policy.category = norm_cat.upper() if norm_cat else None

        if policy_type is not None:
            norm_type = normalize_string(policy_type)
            policy.policy_type = norm_type.upper() if norm_type else None

        if institution is not None:
            policy.institution = normalize_string(institution)

        if jurisdiction is not None:
            norm_jur = normalize_string(jurisdiction)
            policy.jurisdiction = norm_jur.upper() if norm_jur else None

        if regulatory_authority_id is not None:
            if regulatory_authority_id == "" or regulatory_authority_id is None:
                policy.regulatory_authority_id = None
            else:
                auth_id = parse_uuid(regulatory_authority_id, "regulatory_authority_id")
                authority = db.query(RegulatoryAuthority).filter(RegulatoryAuthority.id == auth_id).first()
                if not authority:
                    raise PolicyMetadataNotFoundError(f"Regulatory authority '{auth_id}' not found.")
                if not authority.is_active:
                    raise PolicyMetadataValidationError(
                        f"Cannot associate policy with inactive regulatory authority '{authority.short_name}'."
                    )
                policy.regulatory_authority_id = auth_id

        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def get_policy_source_metadata(db: Session, policy_id: Union[str, UUID]) -> Dict[str, Any]:
        """
        Extract authoritative source metadata from a policy and its linked RegulatoryAuthority.
        """
        policy = PolicyMetadataService.get_policy(db, policy_id)
        authority = policy.regulatory_authority

        return {
            "policy_id": str(policy.id),
            "policy_code": policy.policy_code,
            "title": policy.title,
            "category": policy.category,
            "policy_type": policy.policy_type,
            "institution": policy.institution,
            "jurisdiction": policy.jurisdiction or (authority.jurisdiction if authority else None),
            "has_regulatory_authority": authority is not None,
            "regulatory_authority_id": str(authority.id) if authority else None,
            "issuing_authority": authority.name if authority else None,
            "authority_short_name": authority.short_name if authority else None,
            "authority_type": authority.authority_type if authority else None,
            "authority_website_url": authority.website_url if authority else None,
            "authority_is_active": authority.is_active if authority else None
        }


# ==============================================================================
# Policy Applicability Service
# ==============================================================================

class PolicyApplicabilityService:
    """Service for managing applicability scopes for policies."""

    @staticmethod
    def add_applicability(
        db: Session,
        policy_id: Union[str, UUID],
        institution: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        loan_type: Optional[str] = None,
        department: Optional[str] = None
    ) -> PolicyApplicability:
        """
        Attach an applicability dimension rule to a policy.
        Requires at least one dimension to be provided.
        Prevents duplicate applicability entries for the same policy.
        """
        # Validate that policy exists
        policy = PolicyMetadataService.get_policy(db, policy_id)

        norm_inst = normalize_string(institution)
        norm_jur = normalize_string(jurisdiction)
        if norm_jur:
            norm_jur = norm_jur.upper()

        norm_loan = normalize_string(loan_type)
        if norm_loan:
            norm_loan = norm_loan.upper()

        norm_dept = normalize_string(department)

        # Requirement: At least one applicability dimension must be supplied
        if not any([norm_inst, norm_jur, norm_loan, norm_dept]):
            raise PolicyMetadataValidationError(
                "At least one applicability dimension (institution, jurisdiction, loan_type, department) must be supplied."
            )

        # Prevent duplicate applicability rows for this policy
        duplicate_check = db.query(PolicyApplicability).filter(
            PolicyApplicability.policy_id == policy.id,
            PolicyApplicability.institution == norm_inst,
            PolicyApplicability.jurisdiction == norm_jur,
            PolicyApplicability.loan_type == norm_loan,
            PolicyApplicability.department == norm_dept
        ).first()

        if duplicate_check:
            raise PolicyMetadataConflictError(
                "An identical applicability rule already exists for this policy."
            )

        applicability = PolicyApplicability(
            policy_id=policy.id,
            institution=norm_inst,
            jurisdiction=norm_jur,
            loan_type=norm_loan,
            department=norm_dept
        )
        db.add(applicability)
        db.commit()
        db.refresh(applicability)
        return applicability

    @staticmethod
    def list_applicabilities(db: Session, policy_id: Union[str, UUID]) -> List[PolicyApplicability]:
        """List all applicability dimensions defined for a policy."""
        policy = PolicyMetadataService.get_policy(db, policy_id)
        return db.query(PolicyApplicability).filter(
            PolicyApplicability.policy_id == policy.id
        ).order_by(PolicyApplicability.created_at.asc()).all()

    @staticmethod
    def remove_applicability(db: Session, applicability_id: Union[str, UUID]) -> None:
        """Remove a specific applicability rule."""
        parsed_id = parse_uuid(applicability_id, "applicability_id")
        applicability = db.query(PolicyApplicability).filter(PolicyApplicability.id == parsed_id).first()
        if not applicability:
            raise PolicyMetadataNotFoundError(f"Policy applicability rule '{parsed_id}' not found.")

        db.delete(applicability)
        db.commit()
