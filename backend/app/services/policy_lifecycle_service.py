"""
M08.4 — Policy Lifecycle State Machine & Versioning Service

Manages explicit, auditable transitions through the policy lifecycle:
    DRAFT -> PUBLISHED -> ACTIVE -> SUPERSEDED -> ARCHIVED
    (and DRAFT -> ARCHIVED for draft retirement)

Guarantees version immutability, history preservation, effective date integrity,
and prevents inconsistent states.
"""

from typing import Optional, List, Dict, Any, Union, Set
from uuid import UUID
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import Policy, PolicyVersion, PolicyStatus, User
from app.services.policy_metadata_service import (
    parse_uuid,
    normalize_string
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Domain Exceptions
# ==============================================================================

class PolicyLifecycleError(Exception):
    """Base exception for policy lifecycle operations."""
    pass


class PolicyLifecycleValidationError(PolicyLifecycleError):
    """Raised when lifecycle transition or state validation fails."""
    pass


class PolicyLifecycleNotFoundError(PolicyLifecycleError):
    """Raised when a policy or policy version is not found."""
    pass


class PolicyLifecycleConflictError(PolicyLifecycleError):
    """Raised when a lifecycle conflict occurs (e.g. attempting invalid mutation)."""
    pass


# ==============================================================================
# Lifecycle State Machine & Service
# ==============================================================================

class PolicyLifecycleService:
    """
    Authoritative service governing policy lifecycle transitions,
    version history, version immutability, and state consistency.
    """

    ALLOWED_TRANSITIONS: Dict[PolicyStatus, Set[PolicyStatus]] = {
        PolicyStatus.DRAFT: {PolicyStatus.PUBLISHED, PolicyStatus.ARCHIVED},
        PolicyStatus.PUBLISHED: {PolicyStatus.ACTIVE},
        PolicyStatus.ACTIVE: {PolicyStatus.SUPERSEDED},
        PolicyStatus.SUPERSEDED: {PolicyStatus.ARCHIVED},
        PolicyStatus.ARCHIVED: set()  # Terminal state: cannot transition to any state
    }

    IMMUTABLE_VERSION_FIELDS: Set[str] = {
        "file_hash",
        "file_url",
        "file_size_bytes",
        "page_count",
        "version_number"
    }

    @classmethod
    def _log_audit_event(
        cls,
        event_type: str,
        policy_id: UUID,
        actor_id: Optional[UUID] = None,
        version_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Lightweight audit event emission for policy lifecycle operations."""
        logger.info(
            "AUDIT_EVENT: %s - policy_id=%s actor_id=%s version_id=%s details=%s",
            event_type,
            str(policy_id),
            str(actor_id) if actor_id else "SYSTEM",
            str(version_id) if version_id else "NONE",
            details or {}
        )

    @classmethod
    def _verify_transition_allowed(cls, current_status: PolicyStatus, target_status: PolicyStatus) -> None:
        """Validate whether the transition from current_status to target_status is permitted."""
        allowed = cls.ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise PolicyLifecycleValidationError(
                f"Invalid policy lifecycle transition from '{current_status.value}' to '{target_status.value}'. "
                f"Allowed transitions from '{current_status.value}': "
                f"{[s.value for s in allowed] if allowed else 'None (terminal state)'}."
            )

    @classmethod
    def publish_policy(
        cls,
        db: Session,
        policy_id: Union[str, UUID],
        actor_id: Optional[Union[str, UUID]] = None,
        version_id: Optional[Union[str, UUID]] = None
    ) -> Policy:
        """
        Transitions a policy from DRAFT to PUBLISHED.

        Rules:
        - Policy must exist and currently be DRAFT.
        - Policy must have at least one PolicyVersion.
        - Selected version must have a valid stored document (file_hash, file_url, file_size_bytes > 0).
        - Policy must have required core metadata (title, policy_code).
        - Sets Policy.status = PUBLISHED.
        - Sets PolicyVersion.published_by = actor_id.
        - Does NOT automatically activate the policy.
        """
        parsed_policy_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).filter(Policy.id == parsed_policy_id).first()
        if not policy:
            raise PolicyLifecycleNotFoundError(f"Policy '{parsed_policy_id}' not found.")

        cls._verify_transition_allowed(policy.status, PolicyStatus.PUBLISHED)

        # Core metadata validation
        if not policy.title or not policy.title.strip():
            raise PolicyLifecycleValidationError("Policy cannot be published without a title.")
        if not policy.policy_code or not policy.policy_code.strip():
            raise PolicyLifecycleValidationError("Policy cannot be published without a policy code.")

        # Find target version
        if version_id:
            parsed_version_id = parse_uuid(version_id, "version_id")
            target_version = db.query(PolicyVersion).filter(
                PolicyVersion.id == parsed_version_id,
                PolicyVersion.policy_id == policy.id
            ).first()
            if not target_version:
                raise PolicyLifecycleNotFoundError(f"PolicyVersion '{parsed_version_id}' not found for this policy.")
        else:
            # Pick latest version
            target_version = db.query(PolicyVersion).filter(
                PolicyVersion.policy_id == policy.id
            ).order_by(PolicyVersion.created_at.desc()).first()

        if not target_version:
            raise PolicyLifecycleValidationError("Cannot publish a policy without at least one PolicyVersion.")

        # Validate version document completeness
        if not target_version.file_hash or not target_version.file_url or not target_version.file_size_bytes or target_version.file_size_bytes <= 0:
            raise PolicyLifecycleValidationError(
                f"Policy version (v{target_version.version_number}) has an incomplete or missing source document. "
                "A verified document is required before publishing."
            )

        # Record publisher if actor provided
        if actor_id:
            parsed_actor_id = parse_uuid(actor_id, "actor_id")
            target_version.published_by = parsed_actor_id

        policy.status = PolicyStatus.PUBLISHED
        policy.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(policy)

        cls._log_audit_event(
            event_type="POLICY_PUBLISHED",
            policy_id=policy.id,
            actor_id=parse_uuid(actor_id, "actor_id") if actor_id else None,
            version_id=target_version.id,
            details={"version_number": target_version.version_number}
        )

        return policy

    @classmethod
    def activate_policy_version(
        cls,
        db: Session,
        policy_id: Union[str, UUID],
        version_id: Optional[Union[str, UUID]] = None,
        actor_id: Optional[Union[str, UUID]] = None
    ) -> Policy:
        """
        Activates a PUBLISHED policy.

        Rules:
        - Policy must exist and currently be in PUBLISHED status.
        - PolicyVersion must exist and have a valid source document.
        - PolicyVersion must have effective_from.
        - If effective_to is present, effective_to >= effective_from.
        - Sets Policy.status = ACTIVE.
        - Sets Policy.current_version_id = version.id.
        """
        parsed_policy_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).filter(Policy.id == parsed_policy_id).first()
        if not policy:
            raise PolicyLifecycleNotFoundError(f"Policy '{parsed_policy_id}' not found.")

        cls._verify_transition_allowed(policy.status, PolicyStatus.ACTIVE)

        # Locate candidate version
        if version_id:
            parsed_version_id = parse_uuid(version_id, "version_id")
            target_version = db.query(PolicyVersion).filter(
                PolicyVersion.id == parsed_version_id,
                PolicyVersion.policy_id == policy.id
            ).first()
            if not target_version:
                raise PolicyLifecycleNotFoundError(f"PolicyVersion '{parsed_version_id}' not found for this policy.")
        else:
            target_version = db.query(PolicyVersion).filter(
                PolicyVersion.policy_id == policy.id
            ).order_by(PolicyVersion.created_at.desc()).first()

        if not target_version:
            raise PolicyLifecycleValidationError("Cannot activate a policy without a valid PolicyVersion.")

        # Validate effective dates
        if not target_version.effective_from:
            raise PolicyLifecycleValidationError(
                "Policy version cannot be activated without an effective_from date."
            )
        if target_version.effective_to and target_version.effective_to < target_version.effective_from:
            raise PolicyLifecycleValidationError(
                "effective_to date cannot be earlier than effective_from date."
            )

        # Validate source document presence
        if not target_version.file_hash or not target_version.file_url or not target_version.file_size_bytes or target_version.file_size_bytes <= 0:
            raise PolicyLifecycleValidationError(
                "Policy version cannot be activated because its source document is invalid or missing."
            )

        policy.status = PolicyStatus.ACTIVE
        policy.current_version_id = target_version.id
        policy.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(policy)

        cls._log_audit_event(
            event_type="POLICY_ACTIVATED",
            policy_id=policy.id,
            actor_id=parse_uuid(actor_id, "actor_id") if actor_id else None,
            version_id=target_version.id,
            details={"version_number": target_version.version_number}
        )

        return policy

    @classmethod
    def supersede_policy(
        cls,
        db: Session,
        policy_id: Union[str, UUID],
        new_version_id: Optional[Union[str, UUID]] = None,
        actor_id: Optional[Union[str, UUID]] = None,
        target_status: PolicyStatus = PolicyStatus.SUPERSEDED
    ) -> Policy:
        """
        Supersedes an ACTIVE policy/version with a new valid version.

        Rules:
        - Policy must exist and currently be ACTIVE.
        - new_version_id must be provided (cannot supersede without a new version).
        - new_version must exist under this policy and differ from current_version_id.
        - new_version must have a valid document and effective_from date.
        - If new_version has effective_to, effective_to >= effective_from.
        - Preserves the previous version (never deleted).
        - Adjusts previous version's effective_to if appropriate.
        - Updates Policy.current_version_id = new_version.id.
        - Updates Policy.status to target_status (default: SUPERSEDED).
        """
        parsed_policy_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).filter(Policy.id == parsed_policy_id).first()
        if not policy:
            raise PolicyLifecycleNotFoundError(f"Policy '{parsed_policy_id}' not found.")

        cls._verify_transition_allowed(policy.status, PolicyStatus.SUPERSEDED)

        if not new_version_id:
            raise PolicyLifecycleValidationError("Superseding without new version rejected. A new version is required.")

        parsed_new_version_id = parse_uuid(new_version_id, "new_version_id")
        new_version = db.query(PolicyVersion).filter(
            PolicyVersion.id == parsed_new_version_id,
            PolicyVersion.policy_id == policy.id
        ).first()

        if not new_version:
            raise PolicyLifecycleNotFoundError(f"New PolicyVersion '{parsed_new_version_id}' not found for this policy.")

        if policy.current_version_id and policy.current_version_id == new_version.id:
            raise PolicyLifecycleConflictError("New version cannot be identical to the currently active version.")

        # Validate new version document & dates
        if not new_version.file_hash or not new_version.file_url or not new_version.file_size_bytes or new_version.file_size_bytes <= 0:
            raise PolicyLifecycleValidationError(
                "New version cannot supersede current version because its document is invalid or incomplete."
            )
        if not new_version.effective_from:
            raise PolicyLifecycleValidationError(
                "New version cannot supersede current version without an effective_from date."
            )
        if new_version.effective_to and new_version.effective_to < new_version.effective_from:
            raise PolicyLifecycleValidationError(
                "New version effective_to date cannot be earlier than effective_from date."
            )

        previous_version_id = policy.current_version_id
        if previous_version_id:
            previous_version = db.query(PolicyVersion).filter(PolicyVersion.id == previous_version_id).first()
            if previous_version:
                # Align previous version effective_to to new version effective_from if unset or later
                if not previous_version.effective_to or previous_version.effective_to > new_version.effective_from:
                    previous_version.effective_to = new_version.effective_from

        policy.current_version_id = new_version.id
        policy.status = target_status
        policy.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(policy)

        cls._log_audit_event(
            event_type="POLICY_SUPERSEDED",
            policy_id=policy.id,
            actor_id=parse_uuid(actor_id, "actor_id") if actor_id else None,
            version_id=new_version.id,
            details={
                "previous_version_id": str(previous_version_id) if previous_version_id else None,
                "new_version_number": new_version.version_number
            }
        )

        return policy

    @classmethod
    def archive_policy(
        cls,
        db: Session,
        policy_id: Union[str, UUID],
        actor_id: Optional[Union[str, UUID]] = None
    ) -> Policy:
        """
        Transitions a policy to ARCHIVED.

        Rules:
        - Allowed from SUPERSEDED (normal lifecycle) or DRAFT (administrative retirement of draft).
        - Not allowed directly from ACTIVE or PUBLISHED (must follow lifecycle paths).
        - ARCHIVED is terminal: an archived policy cannot be reactivated or published.
        - Preserves all historical versions and references.
        """
        parsed_policy_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).filter(Policy.id == parsed_policy_id).first()
        if not policy:
            raise PolicyLifecycleNotFoundError(f"Policy '{parsed_policy_id}' not found.")

        cls._verify_transition_allowed(policy.status, PolicyStatus.ARCHIVED)

        policy.status = PolicyStatus.ARCHIVED
        policy.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(policy)

        cls._log_audit_event(
            event_type="POLICY_ARCHIVED",
            policy_id=policy.id,
            actor_id=parse_uuid(actor_id, "actor_id") if actor_id else None,
            version_id=policy.current_version_id
        )

        return policy

    @classmethod
    def get_policy_version_history(
        cls,
        db: Session,
        policy_id: Union[str, UUID]
    ) -> List[Dict[str, Any]]:
        """
        Returns full version history for a policy ordered by version_number DESC.
        Includes contextual status for each version and hides raw filesystem paths.
        """
        parsed_policy_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).filter(Policy.id == parsed_policy_id).first()
        if not policy:
            raise PolicyLifecycleNotFoundError(f"Policy '{parsed_policy_id}' not found.")

        versions = db.query(PolicyVersion).filter(
            PolicyVersion.policy_id == policy.id
        ).all()

        # Sort descending by integer version if possible, else string
        def sort_key(v: PolicyVersion):
            try:
                return (0, int(v.version_number))
            except (ValueError, TypeError):
                return (1, v.version_number)

        sorted_versions = sorted(versions, key=sort_key, reverse=True)

        history = []
        for v in sorted_versions:
            # Determine contextual status of the version
            if v.id == policy.current_version_id:
                status_context = policy.status.value
            elif policy.status == PolicyStatus.DRAFT:
                status_context = "DRAFT"
            else:
                status_context = "SUPERSEDED"

            # Controlled relative file reference
            safe_file_url = v.file_url or ""
            if safe_file_url.startswith("/") or ":" in safe_file_url[:5]:
                # Sanitize if any legacy path had full filesystem reference
                safe_file_url = f"storage/policies/{policy.id}/{v.id}/document"

            history.append({
                "id": str(v.id),
                "policy_id": str(v.policy_id),
                "version_number": v.version_number,
                "status_context": status_context,
                "changelog": v.changelog,
                "file_url": safe_file_url,
                "file_hash": v.file_hash,
                "file_size_bytes": v.file_size_bytes,
                "page_count": v.page_count,
                "effective_from": v.effective_from,
                "effective_to": v.effective_to,
                "created_by": str(v.created_by) if v.created_by else None,
                "published_by": str(v.published_by) if v.published_by else None,
                "created_at": v.created_at,
                "updated_at": v.updated_at
            })

        return history

    @classmethod
    def update_policy_version_metadata(
        cls,
        db: Session,
        policy_id: Union[str, UUID],
        version_id: Union[str, UUID],
        changelog: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        effective_to: Optional[datetime] = None,
        attempted_immutable_fields: Optional[Dict[str, Any]] = None
    ) -> PolicyVersion:
        """
        Updates allowed metadata on a PolicyVersion while strictly enforcing version immutability.

        Rejects any alteration of:
        - file_hash
        - file_url
        - file_size_bytes
        - page_count
        - version_number
        once associated with published, active, superseded, or archived policies.
        """
        parsed_policy_id = parse_uuid(policy_id, "policy_id")
        parsed_version_id = parse_uuid(version_id, "version_id")

        policy = db.query(Policy).filter(Policy.id == parsed_policy_id).first()
        if not policy:
            raise PolicyLifecycleNotFoundError(f"Policy '{parsed_policy_id}' not found.")

        version = db.query(PolicyVersion).filter(
            PolicyVersion.id == parsed_version_id,
            PolicyVersion.policy_id == policy.id
        ).first()
        if not version:
            raise PolicyLifecycleNotFoundError(f"PolicyVersion '{parsed_version_id}' not found.")

        # Guard against immutable field mutation
        if attempted_immutable_fields:
            for field in cls.IMMUTABLE_VERSION_FIELDS:
                if field in attempted_immutable_fields:
                    val = attempted_immutable_fields[field]
                    current_val = getattr(version, field, None)
                    if val != current_val:
                        raise PolicyLifecycleConflictError(
                            f"Field '{field}' on PolicyVersion is strictly immutable and cannot be modified."
                        )

        # Validate effective dates if updated
        new_from = effective_from if effective_from is not None else version.effective_from
        new_to = effective_to if effective_to is not None else version.effective_to
        if new_from and new_to and new_to < new_from:
            raise PolicyLifecycleValidationError("effective_to date cannot be earlier than effective_from date.")

        if changelog is not None:
            version.changelog = normalize_string(changelog)
        if effective_from is not None:
            version.effective_from = effective_from
        if effective_to is not None:
            version.effective_to = effective_to

        version.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(version)
        return version

    @classmethod
    def validate_policy_lifecycle_state(cls, db: Session, policy_id: Union[str, UUID]) -> None:
        """
        Comprehensive consistency check for a policy's lifecycle state.
        Raises PolicyLifecycleValidationError if any anomaly or invariant violation is detected.
        """
        parsed_policy_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).filter(Policy.id == parsed_policy_id).first()
        if not policy:
            raise PolicyLifecycleNotFoundError(f"Policy '{parsed_policy_id}' not found.")

        versions = db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy.id).all()

        if policy.status == PolicyStatus.ACTIVE:
            if not policy.current_version_id:
                raise PolicyLifecycleValidationError(
                    "State inconsistency: Policy is ACTIVE but current_version_id is NULL."
                )
            current_v = next((v for v in versions if v.id == policy.current_version_id), None)
            if not current_v:
                raise PolicyLifecycleValidationError(
                    f"State inconsistency: Policy is ACTIVE but current_version_id '{policy.current_version_id}' does not exist."
                )
            if not current_v.file_hash or not current_v.file_url or not current_v.file_size_bytes or current_v.file_size_bytes <= 0:
                raise PolicyLifecycleValidationError(
                    "State inconsistency: Active version has invalid or missing source document."
                )
            if not current_v.effective_from:
                raise PolicyLifecycleValidationError(
                    "State inconsistency: Active version is missing required effective_from date."
                )

        elif policy.status == PolicyStatus.PUBLISHED:
            if not versions:
                raise PolicyLifecycleValidationError(
                    "State inconsistency: Policy is PUBLISHED but has no PolicyVersions."
                )
            valid_doc_exists = any(
                v.file_hash and v.file_url and v.file_size_bytes and v.file_size_bytes > 0
                for v in versions
            )
            if not valid_doc_exists:
                raise PolicyLifecycleValidationError(
                    "State inconsistency: Policy is PUBLISHED but has no valid document attached."
                )

        elif policy.status == PolicyStatus.SUPERSEDED:
            if policy.current_version_id:
                current_v = next((v for v in versions if v.id == policy.current_version_id), None)
                if not current_v:
                    raise PolicyLifecycleValidationError(
                        f"State inconsistency: Policy is SUPERSEDED but current_version_id '{policy.current_version_id}' does not exist."
                    )
