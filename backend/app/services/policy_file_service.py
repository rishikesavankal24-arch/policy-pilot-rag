"""
M08.3 — Policy File Ingestion & Validation Service

Handles authoritative policy source document validation, metadata extraction,
cryptographic hashing (SHA-256), atomic storage, and PolicyVersion persistence.
"""

from typing import Optional, Tuple, NamedTuple, Set, Union
from uuid import UUID
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import os
import re
import shutil
import io
import pypdf

from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.db.models import Policy, PolicyVersion, User
from app.services.policy_metadata_service import (
    PolicyMetadataValidationError,
    PolicyMetadataNotFoundError,
    PolicyMetadataConflictError,
    parse_uuid,
    normalize_string
)

# Canonical storage base for policy source documents
DEFAULT_POLICY_STORAGE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "storage" / "policies"
).resolve()

MAX_POLICY_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_POLICY_EXTENSIONS: Set[str] = {".pdf", ".png", ".jpg", ".jpeg"}

MAGIC_BYTES_PDF = b"%PDF-"
MAGIC_BYTES_PNG = b"\x89PNG\r\n\x1a\n"
MAGIC_BYTES_PNG_SHORT = b"\x89PNG"
MAGIC_BYTES_JPEG = b"\xFF\xD8\xFF"


class PolicyFileValidationResult(NamedTuple):
    safe_filename: str
    file_size_bytes: int
    mime_type: str
    file_hash: str
    page_count: Optional[int]


class PolicyFileValidator:
    """Validates policy file content, formats, signatures, size limits, and sanitizes filenames."""

    @staticmethod
    def sanitize_filename(filename: str, fallback_ext: str = ".pdf") -> str:
        """
        Sanitize uploaded filename to strictly prevent path traversal.
        Strips directory components and replaces unsafe characters.
        """
        base = os.path.basename((filename or "policy_document.pdf").replace("\\", "/"))
        # Strip all directory traversal markers
        clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', base)
        clean = clean.lstrip('.')
        if not clean or clean in (".", ".."):
            clean = f"policy_document{fallback_ext}"
        return clean

    @classmethod
    def validate_and_extract(
        cls,
        filename: str,
        file_bytes: bytes
    ) -> PolicyFileValidationResult:
        """
        Thoroughly validates policy file content:
        1. Non-empty check (> 0 bytes)
        2. Size limit check (<= 10MB)
        3. Extension whitelist check
        4. Magic-byte signature verification
        5. Structural integrity check (PDF parsing via pypdf)
        6. SHA-256 digest computation
        7. Page count extraction (PDF only; None for images)
        """
        # 1. Non-empty check
        total_bytes = len(file_bytes)
        if total_bytes == 0:
            raise PolicyMetadataValidationError("Empty files are not allowed.")

        # 2. Maximum file size check
        if total_bytes > MAX_POLICY_FILE_SIZE_BYTES:
            raise PolicyMetadataValidationError(
                f"File size ({total_bytes} bytes) exceeds the 10 MB limit."
            )

        # 3. Extension check
        raw_name = filename or "policy_document.pdf"
        _, ext = os.path.splitext(raw_name)
        ext_lower = ext.lower()
        if not ext_lower or ext_lower not in ALLOWED_POLICY_EXTENSIONS:
            raise PolicyMetadataValidationError(
                f"Unsupported file type '{ext_lower}'. Only PDF, PNG, and JPEG policy documents are allowed."
            )

        safe_name = cls.sanitize_filename(raw_name, fallback_ext=ext_lower)

        # 4 & 5. Magic-byte and structural integrity verification
        canonical_mime: str
        page_count: Optional[int] = None

        if ext_lower == ".pdf":
            if not file_bytes.startswith(MAGIC_BYTES_PDF) or total_bytes < 8:
                raise PolicyMetadataValidationError(
                    "File content does not match the declared PDF format. Invalid PDF signature."
                )
            # Structural PDF verification via pypdf
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except Exception:
                        raise PolicyMetadataValidationError(
                            "Encrypted or password-protected PDF files are not supported."
                        )
                page_count = len(reader.pages)
                if page_count < 1:
                    raise PolicyMetadataValidationError(
                        "Invalid or corrupted PDF document. The document has no readable pages."
                    )
            except PolicyMetadataValidationError:
                raise
            except Exception:
                raise PolicyMetadataValidationError(
                    "Invalid or corrupted PDF document. Could not parse document structure."
                )
            canonical_mime = "application/pdf"

        elif ext_lower == ".png":
            if not (file_bytes.startswith(MAGIC_BYTES_PNG) or file_bytes.startswith(MAGIC_BYTES_PNG_SHORT)):
                raise PolicyMetadataValidationError(
                    "File content does not match the declared PNG format. Invalid PNG signature."
                )
            canonical_mime = "image/png"
            page_count = None

        elif ext_lower in (".jpg", ".jpeg"):
            if not file_bytes.startswith(MAGIC_BYTES_JPEG):
                raise PolicyMetadataValidationError(
                    "File content does not match the declared JPEG format. Invalid JPEG signature."
                )
            canonical_mime = "image/jpeg"
            page_count = None

        else:
            raise PolicyMetadataValidationError(f"Unsupported file type: {ext_lower}")

        # 6. SHA-256 calculation
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        return PolicyFileValidationResult(
            safe_filename=safe_name,
            file_size_bytes=total_bytes,
            mime_type=canonical_mime,
            file_hash=file_hash,
            page_count=page_count
        )


class PolicyFileService:
    """Service handling policy document attachment, atomic persistence, and retrieval."""

    @classmethod
    def get_storage_base(cls, custom_dir: Optional[Union[str, Path]] = None) -> Path:
        """Resolve storage base directory."""
        if custom_dir:
            base = Path(custom_dir).resolve()
        else:
            base = DEFAULT_POLICY_STORAGE_DIR
        base.mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def calculate_next_version_number(cls, db: Session, policy_id: UUID) -> str:
        """
        Calculate next incremental version number for the policy.
        For first version: returns '1'.
        For subsequent versions: returns max(existing version numbers as int) + 1.
        """
        existing_versions = db.query(PolicyVersion.version_number).filter(
            PolicyVersion.policy_id == policy_id
        ).all()

        int_versions = []
        for (v_num,) in existing_versions:
            try:
                int_versions.append(int(v_num))
            except (ValueError, TypeError):
                # In case of semantic version string e.g. '1.0'
                try:
                    int_versions.append(int(float(v_num)))
                except (ValueError, TypeError):
                    pass

        if not int_versions:
            return "1"
        return str(max(int_versions) + 1)

    @classmethod
    def attach_policy_version_document(
        cls,
        db: Session,
        policy_id: Union[str, UUID],
        filename: str,
        file_bytes: bytes,
        changelog: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        effective_to: Optional[datetime] = None,
        created_by: Optional[Union[str, UUID]] = None,
        storage_dir: Optional[Union[str, Path]] = None
    ) -> PolicyVersion:
        """
        Attach a validated document to a new PolicyVersion:
        1. Verify target policy exists.
        2. Validate effective date boundaries (effective_to >= effective_from).
        3. Validate file content and structure (size, magic bytes, sha-256, page count).
        4. Check for duplicate SHA-256 hash within the same policy.
        5. Determine safe next version number (1, 2, ...).
        6. Atomically persist file to backend/storage/policies/{policy_id}/{version_id}/{safe_filename}.
        7. Persist PolicyVersion record in database.
        8. Rollback and cleanup file on any failure.
        """
        parsed_policy_id = parse_uuid(policy_id, "policy_id")
        policy = db.query(Policy).filter(Policy.id == parsed_policy_id).first()
        if not policy:
            raise PolicyMetadataNotFoundError(f"Policy '{parsed_policy_id}' not found.")

        # 2. Date validation
        if effective_from and effective_to:
            if effective_to < effective_from:
                raise PolicyMetadataValidationError(
                    "effective_to date cannot be earlier than effective_from date."
                )

        # 3. File validation & metadata extraction
        validation = PolicyFileValidator.validate_and_extract(filename, file_bytes)

        # 4. Duplicate SHA-256 detection within the SAME policy
        duplicate_version = db.query(PolicyVersion).filter(
            PolicyVersion.policy_id == policy.id,
            PolicyVersion.file_hash == validation.file_hash
        ).first()
        if duplicate_version:
            raise PolicyMetadataConflictError(
                f"A policy version (v{duplicate_version.version_number}) with the identical document content "
                f"(SHA-256: {validation.file_hash[:12]}...) already exists for this policy."
            )

        # 5. Version number calculation
        version_number = cls.calculate_next_version_number(db, policy.id)
        version_id = UUID(int=hashlib.sha256(f"{policy.id}-{version_number}-{validation.file_hash}".encode()).digest()[:16].hex()) if False else None
        import uuid as uuid_lib
        version_id = uuid_lib.uuid4()

        parsed_creator_id = None
        if created_by:
            parsed_creator_id = parse_uuid(created_by, "created_by")
            user = db.query(User).filter(User.id == parsed_creator_id).first()
            if not user:
                raise PolicyMetadataNotFoundError(f"User '{parsed_creator_id}' specified for created_by not found.")

        # 6. Atomic file write
        storage_base = cls.get_storage_base(storage_dir)
        version_folder = (storage_base / str(policy.id) / str(version_id)).resolve()

        # Path traversal guard
        if not str(version_folder).startswith(str(storage_base)):
            raise PolicyMetadataValidationError("Invalid storage path destination.")

        target_file = (version_folder / validation.safe_filename).resolve()
        if not str(target_file).startswith(str(version_folder)):
            raise PolicyMetadataValidationError("Path traversal detected in filename.")

        try:
            version_folder.mkdir(parents=True, exist_ok=True)
            # Write to a temporary file first for atomic commit
            temp_file = target_file.with_suffix(".tmp")
            with open(temp_file, "wb") as f:
                f.write(file_bytes)
            # Atomic replace
            temp_file.replace(target_file)
        except Exception as write_err:
            if version_folder.exists():
                shutil.rmtree(version_folder, ignore_errors=True)
            raise PolicyMetadataValidationError(f"Failed to persist policy document file: {str(write_err)}")

        # Controlled relative reference
        relative_file_url = f"storage/policies/{policy.id}/{version_id}/{validation.safe_filename}"

        # 7. Persist PolicyVersion record
        policy_version = PolicyVersion(
            id=version_id,
            policy_id=policy.id,
            version_number=version_number,
            changelog=normalize_string(changelog),
            file_url=relative_file_url,
            file_hash=validation.file_hash,
            file_size_bytes=validation.file_size_bytes,
            page_count=validation.page_count,
            effective_from=effective_from,
            effective_to=effective_to,
            created_by=parsed_creator_id
        )

        try:
            db.add(policy_version)
            db.commit()
            db.refresh(policy_version)
            return policy_version
        except Exception as db_err:
            # 8. Atomicity: Clean up persisted file if DB fails
            db.rollback()
            if version_folder.exists():
                shutil.rmtree(version_folder, ignore_errors=True)
            if isinstance(db_err, IntegrityError):
                raise PolicyMetadataConflictError(
                    f"Duplicate policy version number '{version_number}' for policy '{policy.id}'."
                )
            raise PolicyMetadataValidationError(f"Failed to record policy version: {str(db_err)}")

    @classmethod
    def get_policy_version_file(
        cls,
        db: Session,
        policy_id: Union[str, UUID],
        version_id: Union[str, UUID],
        storage_dir: Optional[Union[str, Path]] = None
    ) -> Tuple[Path, PolicyVersion]:
        """
        Locate and verify stored policy document file for an authorized request.
        Returns (resolved_file_path, policy_version).
        """
        parsed_policy_id = parse_uuid(policy_id, "policy_id")
        parsed_version_id = parse_uuid(version_id, "version_id")

        version = db.query(PolicyVersion).filter(
            PolicyVersion.id == parsed_version_id,
            PolicyVersion.policy_id == parsed_policy_id
        ).first()
        if not version:
            raise PolicyMetadataNotFoundError(
                f"PolicyVersion '{parsed_version_id}' for Policy '{parsed_policy_id}' not found."
            )

        storage_base = cls.get_storage_base(storage_dir)
        version_folder = (storage_base / str(parsed_policy_id) / str(parsed_version_id)).resolve()

        if not version_folder.exists() or not version_folder.is_dir():
            raise PolicyMetadataNotFoundError("Policy document storage folder not found on disk.")

        # Find file in the version folder (excluding any .tmp files)
        candidates = [p for p in version_folder.iterdir() if p.is_file() and not p.name.endswith(".tmp")]
        if not candidates:
            raise PolicyMetadataNotFoundError("Policy document file not found on disk.")

        target_file = candidates[0]
        return target_file, version
