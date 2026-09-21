"""
Migration script for existing development documents.
Copies actual uploaded files from Downloads into backend/storage/documents/<doc_id>/
and updates file_url references in the PostgreSQL database.
"""
import os
import shutil
import re
from pathlib import Path
from app.db.session import SessionLocal
from app.db.models import Document

STORAGE_DIR = (Path(__file__).resolve().parent.parent / "storage" / "documents").resolve()
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS_DIR = Path(r"C:\Users\imris\Downloads")

def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "document.pdf")
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', base)
    clean = clean.lstrip('.')
    if not clean:
        clean = "document.pdf"
    return clean

def migrate():
    db = SessionLocal()
    try:
        docs = db.query(Document).all()
        print(f"Found {len(docs)} document records in database.")
        
        migrated_count = 0
        missing_count = 0
        
        for doc in docs:
            doc_folder = (STORAGE_DIR / str(doc.id)).resolve()
            doc_folder.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists in doc_folder
            existing_files = [f for f in doc_folder.iterdir() if f.is_file()]
            if existing_files:
                print(f"[EXISTS] Document {doc.id} already has file on disk: {existing_files[0].name}")
                continue
                
            # Extract raw filename from file_url (e.g. mock://storage/docs/<uuid>/Registration Certificate.pdf)
            raw_filename = os.path.basename(doc.file_url)
            safe_name = sanitize_filename(raw_filename)
            target_path = doc_folder / safe_name
            
            # Check if source file exists in user's Downloads
            source_candidate = DOWNLOADS_DIR / raw_filename
            if not source_candidate.exists():
                # Check without special URL decoding or with variants
                alt_name = raw_filename.replace("%20", " ")
                source_candidate = DOWNLOADS_DIR / alt_name
                
            if source_candidate.exists() and source_candidate.is_file():
                shutil.copy2(str(source_candidate), str(target_path))
                print(f"[MIGRATED] Copied {source_candidate.name} ({source_candidate.stat().st_size} bytes) -> {target_path}")
                doc.file_url = f"documents/{doc.id}/{safe_name}"
                migrated_count += 1
            else:
                print(f"[MISSING BYTES] Document {doc.id} ({raw_filename}): No physical file found on disk. Record preserved as-is.")
                missing_count += 1
                
        db.commit()
        print(f"\nMigration complete: {migrated_count} migrated, {missing_count} without original disk bytes.")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
