from fastapi import UploadFile, HTTPException, status
from typing import NamedTuple, Optional, Set
import hashlib
import os

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
CHUNK_SIZE = 64 * 1024  # 64 KB chunk size for memory-safe streaming

# Canonical controlled document types
PRIMARY_DOCUMENT_TYPES: Set[str] = {
    "IDENTITY_PROOF",
    "ADDRESS_PROOF",
    "INCOME_PROOF",
    "BANK_STATEMENT",
    "EMPLOYMENT_PROOF",
    "COLLATERAL_DOCUMENT",
    "OTHER",
}

# Recognized legacy / workflow document types for M04-M06 backward compatibility
LEGACY_ALLOWED_DOCUMENT_TYPES: Set[str] = {
    "ID_PROOF",
    "ID",
    "IDENTITY",
    "PAN_CARD",
    "AADHAAR_CARD",
    "PHOTO",
    "SALARY_SLIP",
    "TAX_RETURN",
    "FINANCIAL_STATEMENT",
    "REGISTRATION_CERTIFICATE",
    "INCORPORATION_CERTIFICATE",
    "GST_CERTIFICATE",
    "AUDITED_BALANCE_SHEET",
    "ADMISSION_LETTER",
    "ADDITIONAL_DOCUMENT",
}

ALL_ALLOWED_DOCUMENT_TYPES: Set[str] = PRIMARY_DOCUMENT_TYPES | LEGACY_ALLOWED_DOCUMENT_TYPES

# Allowed file extensions (case-insensitive)
ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".png", ".jpg", ".jpeg"}

# Magic byte signatures
MAGIC_BYTES_PDF = b"%PDF-"
MAGIC_BYTES_PNG = b"\x89PNG\r\n\x1a\n"
MAGIC_BYTES_PNG_SHORT = b"\x89PNG"
MAGIC_BYTES_JPEG = b"\xFF\xD8\xFF"


class ValidationResult(NamedTuple):
    original_filename: str
    file_size_bytes: int
    mime_type: str
    file_hash: str
    document_type: str


class DocumentValidator:
    """
    Centralized validation component for M07 document management and security hardening.
    Validates file extensions, size limits, magic bytes, MIME compatibility, and computes SHA-256 digests.
    """

    @classmethod
    def validate_document_type(cls, document_type: str) -> str:
        """Validate that document type conforms to controlled types and return normalized uppercase."""
        if not document_type or not document_type.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document type is required."
            )
        clean_type = document_type.strip().upper()
        if clean_type not in ALL_ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type. Allowed types are: {', '.join(sorted(PRIMARY_DOCUMENT_TYPES))}."
            )
        return clean_type

    @classmethod
    def validate(cls, file: UploadFile, document_type: str) -> ValidationResult:
        """
        Validates an uploaded file thoroughly:
        1. Document type whitelist.
        2. File extension whitelist (case-insensitive).
        3. Size validation (> 0 bytes, <= 10MB) via chunked read.
        4. Magic-byte signature verification.
        5. Client MIME compatibility check against content.
        6. SHA-256 hash calculation.
        7. Stream pointer reset to 0.
        """
        # 1. Validate controlled document type
        validated_doc_type = cls.validate_document_type(document_type)

        # 2. Extract and sanitize filename metadata
        raw_filename = file.filename or "uploaded_document.pdf"
        base_filename = os.path.basename(raw_filename.replace("\\", "/"))
        if not base_filename or base_filename.strip() in [".", ".."]:
            base_filename = "uploaded_document.pdf"

        # 3. Validate extension
        _, ext = os.path.splitext(base_filename)
        ext_lower = ext.lower()
        if not ext_lower or ext_lower not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Only PDF, PNG, and JPEG documents are allowed."
            )

        # 4. Stream and validate file size & compute SHA-256
        sha256_hasher = hashlib.sha256()
        total_bytes = 0
        header_bytes = bytearray()

        try:
            file.file.seek(0)
            while True:
                chunk = file.file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File size exceeds the 10 MB limit."
                    )
                sha256_hasher.update(chunk)
                if len(header_bytes) < 32:
                    header_bytes.extend(chunk[: 32 - len(header_bytes)])
        finally:
            # Ensure stream pointer is always rewound
            file.file.seek(0)

        # 5. Minimum size check (no 0-byte files)
        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty files are not allowed."
            )

        # 6. Magic byte & content integrity verification
        header = bytes(header_bytes)
        canonical_mime: str

        if ext_lower == ".pdf":
            if not header.startswith(MAGIC_BYTES_PDF) or total_bytes < 8:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File content does not match the declared file type. Expected valid PDF format."
                )
            canonical_mime = "application/pdf"

        elif ext_lower == ".png":
            if not (header.startswith(MAGIC_BYTES_PNG) or header.startswith(MAGIC_BYTES_PNG_SHORT)) or total_bytes < 8:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File content does not match the declared file type. Expected valid PNG format."
                )
            canonical_mime = "image/png"

        elif ext_lower in [".jpg", ".jpeg"]:
            if not header.startswith(MAGIC_BYTES_JPEG) or total_bytes < 4:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File content does not match the declared file type. Expected valid JPEG format."
                )
            canonical_mime = "image/jpeg"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type."
            )

        # 7. Declared MIME compatibility check
        # If client explicitly declared a conflicting media type, reject it
        declared_mime = (file.content_type or "").strip().lower()
        if declared_mime:
            if ext_lower == ".pdf" and declared_mime.startswith("image/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Declared content type does not match PDF file extension."
                )
            if ext_lower in [".jpg", ".jpeg", ".png"] and declared_mime == "application/pdf":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Declared content type does not match image file extension."
                )

        calculated_hash = sha256_hasher.hexdigest()

        return ValidationResult(
            original_filename=base_filename,
            file_size_bytes=total_bytes,
            mime_type=canonical_mime,
            file_hash=calculated_hash,
            document_type=validated_doc_type
        )
