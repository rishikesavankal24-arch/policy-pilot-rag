from pathlib import Path
from typing import Optional, Union, Dict, Any, BinaryIO
from fastapi import HTTPException, status
import io
import pypdf
from pypdf.errors import PdfReadError


class DocumentProcessor:
    """
    Centralized document processing and metadata extraction service for M07 Phase 4.
    Extracts structural metadata such as page counts for PDFs and dimension information for images.
    """

    @classmethod
    def process_pdf(cls, file_source: Union[str, Path, BinaryIO, bytes]) -> Dict[str, Any]:
        """
        Safely opens and parses a PDF document to extract the actual page count.
        Rejects structurally corrupted, unreadable, or empty PDFs with a controlled HTTP 400.
        """
        try:
            if isinstance(file_source, (str, Path)):
                reader = pypdf.PdfReader(str(file_source))
            elif isinstance(file_source, bytes):
                reader = pypdf.PdfReader(io.BytesIO(file_source))
            else:
                reader = pypdf.PdfReader(file_source)

            if reader.is_encrypted:
                try:
                    # Attempt empty password decryption in case of empty standard encryption
                    reader.decrypt("")
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Encrypted or password-protected PDF files are not supported."
                    )

            page_count = len(reader.pages)
            if page_count < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or corrupted PDF document. The document has no readable pages."
                )

            return {
                "page_count": page_count
            }
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted PDF document."
            )

    @classmethod
    def process_image(cls, file_source: Union[str, Path, BinaryIO, bytes], mime_type: str) -> Dict[str, Any]:
        """
        Extracts basic image dimensions for PNG/JPEG files.
        page_count is strictly returned as None for images to avoid fake metadata.
        """
        width: Optional[int] = None
        height: Optional[int] = None
        try:
            if isinstance(file_source, (str, Path)):
                with open(file_source, "rb") as f:
                    data = f.read(4096)
            elif isinstance(file_source, bytes):
                data = file_source[:4096]
            else:
                pos = file_source.tell() if hasattr(file_source, "tell") else 0
                data = file_source.read(4096)
                if hasattr(file_source, "seek"):
                    file_source.seek(pos)

            if mime_type == "image/png":
                if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
                    width = int.from_bytes(data[16:20], byteorder="big")
                    height = int.from_bytes(data[20:24], byteorder="big")
            elif mime_type == "image/jpeg":
                idx = 2
                while idx < len(data) - 8:
                    if data[idx] == 0xFF:
                        marker = data[idx + 1]
                        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                            height = int.from_bytes(data[idx + 5:idx + 7], byteorder="big")
                            width = int.from_bytes(data[idx + 7:idx + 9], byteorder="big")
                            break
                        elif marker not in (0x00, 0xFF):
                            seg_len = int.from_bytes(data[idx + 2:idx + 4], byteorder="big")
                            idx += 2 + seg_len
                            continue
                    idx += 1
        except Exception:
            pass

        return {
            "page_count": None,
            "width": width,
            "height": height
        }

    @classmethod
    def process_document(cls, file_source: Union[str, Path, BinaryIO, bytes], mime_type: str) -> Dict[str, Any]:
        """
        Main entrypoint for document processing.
        Routes to format-specific extractors and returns structured metadata.
        """
        if mime_type == "application/pdf":
            return cls.process_pdf(file_source)
        elif mime_type in ("image/png", "image/jpeg"):
            return cls.process_image(file_source, mime_type)
        else:
            return {
                "page_count": None
            }
