import secrets
import hashlib
import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timedelta, timezone
import bcrypt

from app.db.session import SessionLocal
from app.db.models import Session as SessionModel, User, OnboardingStatus, Role

# Helper to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(32)

def generate_otp() -> str:
    """Generate a 6-digit OTP securely."""
    return "".join(str(secrets.randbelow(10)) for _ in range(6))

def hash_otp(otp: str) -> str:
    """Hash the OTP using SHA256 and a global salt."""
    salt = os.getenv("AUTH_SECRET", "default_secret_salt")
    return hashlib.sha256(f"{salt}:{otp}".encode("utf-8")).hexdigest()

def verify_otp_hash(otp: str, hashed_otp: str) -> bool:
    """Verify the provided OTP against the hash."""
    return hash_otp(otp) == hashed_otp

def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False

def create_user_session(db: DBSession, user_id, expires_in_days=7) -> str:
    """Create a new session in the database and return the token."""
    token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    
    session_record = SessionModel(
        user_id=user_id,
        session_token=token,
        expires_at=expires_at
    )
    db.add(session_record)
    db.commit()
    return token

def get_current_user(request: Request, db: DBSession = Depends(get_db)):
    """
    Dependency to retrieve the currently authenticated user based on:
    1. Authorization: Bearer <session_token> (tab/portal-scoped session)
    2. X-Session-ID: <session_token>
    3. Query parameter: ?session_token=<token>
    4. Cookie: session_id=<session_token> (fallback for single-portal/admin)
    """
    session_token = None

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        session_token = auth_header.split(" ", 1)[1].strip()

    if not session_token:
        session_token = request.headers.get("X-Session-ID")

    if not session_token:
        session_token = request.query_params.get("session_token")

    if not session_token:
        session_token = request.cookies.get("session_id")

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    session_record = db.query(SessionModel).filter(SessionModel.session_token == session_token).first()
    
    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )
        
    if session_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        # Session expired, clean it up
        db.delete(session_record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired"
        )
        
    user = db.query(User).filter(User.id == session_record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    portal_scope = request.headers.get("X-Portal-Scope")
    if portal_scope:
        if portal_scope == "employee" and user.role != Role.EMPLOYEE.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Employee session required for this portal"
            )
        elif portal_scope == "customer" and user.role != Role.CUSTOMER.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Customer session required for this portal"
            )
    
    request.state.session_token = session_record.session_token
    return user

def get_fully_onboarded_user(user: User = Depends(get_current_user)):
    """Dependency to retrieve only users who have completed onboarding."""
    if user.onboarding_status in [OnboardingStatus.NEW.value, OnboardingStatus.ONBOARDING_REQUIRED.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Onboarding incomplete"
        )
    if user.onboarding_status == OnboardingStatus.PENDING_VERIFICATION.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending verification"
        )
    if user.onboarding_status != OnboardingStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    return user
