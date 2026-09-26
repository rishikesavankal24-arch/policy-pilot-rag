"""
M08 -> M09 Handoff Contract & Service
======================================
Defines the authoritative boundary and explicit data contract between:
- Module M08: Policy & Regulation Management System
- Module M09: Policy Document Parser & Hybrid Ingestion Engine (Future)

RESPONSIBILITY BOUNDARY:
------------------------
M08 Owns:
- Authoritative policy metadata and regulatory authority catalog
- Policy applicability dimensions (institution, jurisdiction, loan_type, department)
- Policy versions and lifecycle state machine (DRAFT -> PUBLISHED -> ACTIVE -> SUPERSEDED -> ARCHIVED)
- Effective dates, version lineage, and immutability guarantees
- Source document validation (MIME, magic bytes, extension, size limits)
- Cryptographic hashing (SHA-256) and physical storage isolation
- Controlled document stream retrieval

M09 Owns (Deferred to M09 Phase):
- Document parsing and structural text extraction
- OCR fallback (Tesseract/PaddleOCR) for scanned PDFs/images
- Semantic section, clause, and table chunking
- Chunk metadata enrichment (preserving policy_id, policy_version_id, applicability)
- Embedding generation (Gemini / OpenAI / HuggingFace)
- pgvector vector indexing and PostgreSQL Full-Text/BM25 indexing
- Ingestion pipeline orchestration, tracking, and error handling

M08 MUST NEVER:
- Parse policy text for RAG or chunk document content
- Generate embeddings or create vector/pgvector records
- Execute LLM calls or compliance reasoning
- Perform semantic retrieval or reranking

M09 Ingestion Eligibility Criteria:
-----------------------------------
1. Only policies with status == PolicyStatus.ACTIVE are eligible.
2. The policy must have an associated current_version (current_version_id).
3. The PolicyVersion must have a valid stored file (file_hash, file_size_bytes > 0, file_url).
4. The raw source document must exist on disk and be verified via PolicyFileService.
5. Ingestion payload must preserve policy_id, policy_version_id, effective dates, and applicability scope.
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from uuid import UUID
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Policy, PolicyVersion, PolicyStatus, PolicyApplicability, RegulatoryAuthority
)
from app.services.policy_metadata_service import parse_uuid
from app.services.policy_file_service import PolicyFileService, PolicyMetadataNotFoundError


# ==============================================================================
# Domain Exceptions
# ==============================================================================

class M09HandoffError(Exception):
    """Base exception for M09 handoff contract operations."""
    pass


class M09PolicyNotEligibleError(M09HandoffError):
    """Raised when a policy is not eligible for M09 ingestion (e.g., not ACTIVE or missing file)."""
    pass


# ==============================================================================
# M09 Handoff Data Contracts (Pydantic Schemas)
# ==============================================================================

class M09RegulatoryAuthorityContract(BaseModel):
    id: str
    name: str
    short_name: str
    jurisdiction: Optional[str] = None
    website_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class M09PolicyApplicabilityContract(BaseModel):
    id: str
    institution: Optional[str] = None
    jurisdiction: Optional[str] = None
    loan_type: Optional[str] = None
    department: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class M09PolicyContract(BaseModel):
    policy_id: str
    policy_code: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    policy_type: Optional[str] = None
    status: str = Field(..., description="Must be 'ACTIVE'")
    institution: Optional[str] = None
    jurisdiction: Optional[str] = None
    regulatory_authority: Optional[M09RegulatoryAuthorityContract] = None

    model_config = ConfigDict(from_attributes=True)


class M09PolicyVersionContract(BaseModel):
    policy_version_id: str
    policy_id: str
    version_number: str
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    file_url: Optional[str] = None
    file_hash: str
    file_size_bytes: int
    page_count: Optional[int] = None
    changelog: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class M09HandoffPayload(BaseModel):
    """
    Authoritative ingestion contract passed to M09 pipeline.
    Contains verified policy metadata, active version metadata,
    applicability dimensions, and source document status.
    """
    policy: M09PolicyContract
    version: M09PolicyVersionContract
    applicabilities: List[M09PolicyApplicabilityContract]
    is_source_document_verified: bool
    source_filename: str

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# M09 Handoff Service
# ==============================================================================

class M09HandoffService:
    """Authoritative provider for M09 ingestion handoff data."""

    @classmethod
    def get_policy_version_handoff_payload(
        cls,
        db: Session,
        policy_id: Union[str, UUID]
    ) -> M09HandoffPayload:
        """
        Builds the complete, validated M09 ingestion contract for an ACTIVE policy.

        Enforces:
        - Policy must exist and have status == PolicyStatus.ACTIVE.
        - Policy must have current_version_id pointing to an active version.
        - Selected PolicyVersion must have file_hash and file_size_bytes > 0.
        - Physical file must be verified in storage.
        """
        parsed_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).options(
            joinedload(Policy.current_version),
            joinedload(Policy.regulatory_authority),
            joinedload(Policy.applicabilities)
        ).filter(Policy.id == parsed_id).first()

        if not policy:
            raise M09PolicyNotEligibleError(f"Policy '{parsed_id}' not found.")

        # 1. Eligibility Check: Status must be ACTIVE
        if policy.status != PolicyStatus.ACTIVE:
            raise M09PolicyNotEligibleError(
                f"Policy '{policy.policy_code}' is in status '{policy.status.value}'. "
                f"Only ACTIVE policies are eligible for M09 RAG ingestion."
            )

        # 2. Eligibility Check: Must have a bound current_version
        cv: Optional[PolicyVersion] = policy.current_version
        if not cv:
            raise M09PolicyNotEligibleError(
                f"ACTIVE policy '{policy.policy_code}' has no current_version assigned."
            )

        # 3. Eligibility Check: Version must have valid file metadata
        if not cv.file_hash or not cv.file_size_bytes or cv.file_size_bytes <= 0:
            raise M09PolicyNotEligibleError(
                f"Policy version '{cv.version_number}' for policy '{policy.policy_code}' "
                f"has no valid attached document (missing file_hash or file_size_bytes)."
            )

        # 4. Verify physical storage file exists
        try:
            target_file, _ = PolicyFileService.get_policy_version_file(
                db=db,
                policy_id=policy.id,
                version_id=cv.id
            )
        except Exception as e:
            raise M09PolicyNotEligibleError(
                f"Physical document file for policy '{policy.policy_code}' v{cv.version_number} "
                f"cannot be accessed from storage: {str(e)}"
            )

        # 5. Project Contracts
        ra_contract = None
        if policy.regulatory_authority:
            ra = policy.regulatory_authority
            ra_contract = M09RegulatoryAuthorityContract(
                id=str(ra.id),
                name=ra.name,
                short_name=ra.short_name,
                jurisdiction=ra.jurisdiction,
                website_url=ra.website_url
            )

        policy_contract = M09PolicyContract(
            policy_id=str(policy.id),
            policy_code=policy.policy_code,
            title=policy.title,
            description=policy.description,
            category=policy.category,
            policy_type=policy.policy_type,
            status=policy.status.value,
            institution=policy.institution,
            jurisdiction=policy.jurisdiction,
            regulatory_authority=ra_contract
        )

        version_contract = M09PolicyVersionContract(
            policy_version_id=str(cv.id),
            policy_id=str(policy.id),
            version_number=str(cv.version_number),
            effective_from=cv.effective_from,
            effective_to=cv.effective_to,
            file_url=cv.file_url,
            file_hash=cv.file_hash,
            file_size_bytes=cv.file_size_bytes,
            page_count=cv.page_count,
            changelog=cv.changelog,
            created_at=cv.created_at
        )

        applicabilities_contract = [
            M09PolicyApplicabilityContract(
                id=str(a.id),
                institution=a.institution,
                jurisdiction=a.jurisdiction,
                loan_type=a.loan_type,
                department=a.department,
                created_at=a.created_at
            )
            for a in policy.applicabilities
        ]

        return M09HandoffPayload(
            policy=policy_contract,
            version=version_contract,
            applicabilities=applicabilities_contract,
            is_source_document_verified=True,
            source_filename=target_file.name
        )

    @classmethod
    def get_eligible_active_policies(
        cls,
        db: Session
    ) -> List[M09HandoffPayload]:
        """
        Discovers and retrieves handoff contracts for all ACTIVE policies
        that satisfy all M09 ingestion eligibility criteria.
        """
        active_policies = db.query(Policy).options(
            joinedload(Policy.current_version),
            joinedload(Policy.regulatory_authority),
            joinedload(Policy.applicabilities)
        ).filter(
            Policy.status == PolicyStatus.ACTIVE,
            Policy.current_version_id.isnot(None)
        ).all()

        eligible_payloads: List[M09HandoffPayload] = []
        for policy in active_policies:
            try:
                payload = cls.get_policy_version_handoff_payload(db=db, policy_id=policy.id)
                eligible_payloads.append(payload)
            except M09PolicyNotEligibleError:
                # Skip any policy that does not meet full document validation
                continue

        return eligible_payloads

    @classmethod
    def get_policy_version_source_file(
        cls,
        db: Session,
        policy_id: Union[str, UUID]
    ) -> Tuple[Path, PolicyVersion]:
        """
        Direct accessor for M09 parser worker to open source document stream.
        Strictly requires policy to be ACTIVE.
        """
        parsed_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).filter(
            Policy.id == parsed_id,
            Policy.status == PolicyStatus.ACTIVE
        ).first()

        if not policy or not policy.current_version_id:
            raise M09PolicyNotEligibleError(
                f"Policy '{parsed_id}' is not ACTIVE or has no current version."
            )

        return PolicyFileService.get_policy_version_file(
            db=db,
            policy_id=policy.id,
            version_id=policy.current_version_id
        )
