from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pathlib import Path
import uuid
import os
import re
import shutil
import mimetypes

from app.db.session import get_db
from app.core.security import get_current_user
from app.db.models import (
    User, 
    Role, 
    Document, 
    DocumentStatus, 
    Application, 
    OnboardingStatus,
    EmployeeRequest, 
    EmployeeRequestStatus
)

router = APIRouter()

# Storage directory abstraction for local filesystem storage
STORAGE_DIR = (Path(__file__).resolve().parent.parent.parent / "storage" / "documents").resolve()
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent directory traversal and special character injection."""
    base = os.path.basename(filename or "document.pdf")
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', base)
    clean = clean.lstrip('.')
    if not clean:
        clean = "document.pdf"
    return clean


def resolve_document_file_path(doc: Document) -> Optional[Path]:
    """Locate the stored document file on disk within the document's dedicated storage directory."""
    doc_folder = (STORAGE_DIR / str(doc.id)).resolve()
    
    # Path traversal protection: Ensure doc_folder is strictly inside STORAGE_DIR
    try:
        doc_folder.relative_to(STORAGE_DIR)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document storage path")
        
    if not doc_folder.exists() or not doc_folder.is_dir():
        return None
        
    files = [f for f in doc_folder.iterdir() if f.is_file()]
    if not files:
        return None
        
    # Match expected filename from file_url if possible
    if doc.file_url:
        expected_name = sanitize_filename(os.path.basename(doc.file_url))
        candidate = (doc_folder / expected_name).resolve()
        try:
            candidate.relative_to(STORAGE_DIR)
            if candidate.exists() and candidate.is_file():
                return candidate
        except ValueError:
            pass
            
    # Return the first available file in the document directory
    first_file = files[0].resolve()
    try:
        first_file.relative_to(STORAGE_DIR)
        return first_file
    except ValueError:
        return None


class DocumentResponse(BaseModel):
    id: UUID
    application_id: Optional[UUID]
    document_type: str
    file_url: str
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=List[DocumentResponse])
def get_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    
    docs = db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.created_at.desc()).all()
    
    # Return canonical authenticated endpoint URL for client consumption
    return [
        DocumentResponse(
            id=d.id,
            application_id=d.application_id,
            document_type=d.document_type,
            file_url=f"/api/documents/{d.id}/content",
            status=d.status,
            created_at=d.created_at
        )
        for d in docs
    ]


@router.post("/", response_model=DocumentResponse)
def upload_document(
    document_type: str = Form(...),
    application_id: Optional[UUID] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
        
    if application_id:
        app = db.query(Application).filter(Application.id == application_id, Application.user_id == current_user.id).first()
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found or unauthorized")

    doc_id = uuid.uuid4()
    safe_filename = sanitize_filename(file.filename or "uploaded_document.pdf")
    
    doc_dir = (STORAGE_DIR / str(doc_id)).resolve()
    doc_dir.mkdir(parents=True, exist_ok=True)
    target_path = (doc_dir / safe_filename).resolve()
    
    # Ensure path cannot escape STORAGE_DIR
    try:
        target_path.relative_to(STORAGE_DIR)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path")

    # Persist real file bytes to storage
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Relative storage key stored in database
    relative_storage_key = f"documents/{doc_id}/{safe_filename}"

    new_doc = Document(
        id=doc_id,
        user_id=current_user.id,
        application_id=application_id,
        document_type=document_type,
        file_url=relative_storage_key,
        status=DocumentStatus.UPLOADED.value
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    return DocumentResponse(
        id=new_doc.id,
        application_id=new_doc.application_id,
        document_type=new_doc.document_type,
        file_url=f"/api/documents/{new_doc.id}/content",
        status=new_doc.status,
        created_at=new_doc.created_at
    )


@router.get("/{document_id}/content")
def get_document_content(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Authenticated endpoint to view/download document content.
    Enforces RBAC and conflict-of-interest controls.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
    # --- AUTHORIZATION ---
    if current_user.role == Role.ADMIN.value:
        pass  # Admin has full administrative access
    elif current_user.role == Role.CUSTOMER.value:
        # Customer can only access documents belonging to their own account
        if str(doc.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden: You do not own this document")
    elif current_user.role == Role.EMPLOYEE.value:
        # Employee must be fully verified
        if current_user.onboarding_status != OnboardingStatus.COMPLETED.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employee onboarding incomplete")
            
        emp_req = db.query(EmployeeRequest).filter(EmployeeRequest.user_id == current_user.id).order_by(EmployeeRequest.created_at.desc()).first()
        if not emp_req or emp_req.status != EmployeeRequestStatus.APPROVED.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employee credentials unverified")
            
        # Conflict-of-interest check: Employee cannot access application/documents where they are the applicant
        if doc.application_id:
            parent_app = db.query(Application).filter(Application.id == doc.application_id).first()
            if parent_app and str(parent_app.user_id) == str(current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Access denied: Employee cannot access documents of their own application due to conflict-of-interest controls."
                )
        elif str(doc.user_id) == str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Employee cannot access own customer documents in employee role."
            )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden: Unauthorized role")

    # --- FILE LOCATING ---
    file_path = resolve_document_file_path(doc)
    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Document file content not found in storage. The file may need to be re-uploaded."
        )

    # Determine MIME type
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        media_type = "application/pdf"
    elif ext == ".png":
        media_type = "image/png"
    elif ext in [".jpg", ".jpeg"]:
        media_type = "image/jpeg"
    else:
        media_type, _ = mimetypes.guess_type(str(file_path))
        if not media_type:
            media_type = "application/octet-stream"

    # Inline disposition instructs the browser to open the PDF/image directly in tab
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{file_path.name}"'
        }
    )


@router.delete("/{doc_id}")
def delete_document(doc_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
        
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
    if doc.status in [DocumentStatus.VERIFIED.value, DocumentStatus.PROCESSING.value]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete document in this state")
        
    # Remove file on disk if exists
    doc_folder = (STORAGE_DIR / str(doc.id)).resolve()
    try:
        doc_folder.relative_to(STORAGE_DIR)
        if doc_folder.exists() and doc_folder.is_dir():
            shutil.rmtree(doc_folder, ignore_errors=True)
    except ValueError:
        pass

    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully"}
