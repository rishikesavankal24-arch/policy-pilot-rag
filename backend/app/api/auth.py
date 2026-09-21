import os
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.db.session import SessionLocal
from app.db.models import User, OnboardingStatus, Role, OTPRecord
from app.core.security import create_user_session, get_current_user, get_db, generate_otp, hash_otp, verify_otp_hash
from app.services.sms import sms_service
from pydantic import BaseModel
import re
from typing import Optional
from app.core.security import get_password_hash, verify_password

router = APIRouter()

@router.get("/google/login")
def google_login(state: Optional[str] = None):
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    REDIRECT_URI = f"{BACKEND_URL}/auth/google/callback"
    
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={REDIRECT_URI}"
        f"&scope=openid%20email%20profile&access_type=offline"
    )
    if state:
        auth_url += f"&state={state}"
    return RedirectResponse(auth_url)

@router.get("/google/callback")
async def google_callback(
    code: str, 
    request: Request, 
    response: Response, 
    state: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:3000")
    ADMIN_FRONTEND_URL = os.getenv("ADMIN_FRONTEND_URL", "http://127.0.0.1:3001")
    REDIRECT_URI = f"{BACKEND_URL}/auth/google/callback"

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=data)
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve token from Google")
        
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        
        # Get user info
        user_info_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if user_info_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve user info")
        
        user_info = user_info_res.json()
        email = user_info.get("email")
        google_id = user_info.get("id")
        name = user_info.get("name")
        picture = user_info.get("picture")

    if not email or not google_id:
        raise HTTPException(status_code=400, detail="Invalid user info returned from Google")

    # Find or create user
    user = db.query(User).filter(
        (User.provider_subject_id == google_id) | (User.email == email)
    ).first()
    if not user:
        user = User(
            email=email,
            full_name=name,
            profile_image_url=picture,
            authentication_provider="google",
            provider_subject_id=google_id,
            onboarding_status=OnboardingStatus.NEW.value,
            role=Role.UNASSIGNED.value,
            requested_role=Role.UNASSIGNED.value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.last_login_at = datetime.now(timezone.utc)
        if not user.provider_subject_id:
            user.provider_subject_id = google_id
        if picture and not user.profile_image_url:
            user.profile_image_url = picture
        db.commit()

    # Admin Portal Authorization Enforcement
    if state == "admin":
        if user.role != Role.ADMIN.value:
            # Deny Admin Portal access: Do not create session, redirect back with error
            return RedirectResponse(f"{ADMIN_FRONTEND_URL}/login?error=access_denied")
        
        # Authorized Administrator: Create session and redirect to admin dashboard
        session_token = create_user_session(db, user.id)
        res = RedirectResponse(f"{ADMIN_FRONTEND_URL}/dashboard")
        res.set_cookie(
            key="session_id",
            value=session_token,
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=7 * 24 * 3600,
            path="/"
        )
        return res

    # Create session
    session_token = create_user_session(db, user.id)
    
    # Redirect back to frontend
    redirect_target = f"{FRONTEND_URL}/dashboard"
    if user.onboarding_status in [OnboardingStatus.NEW.value, OnboardingStatus.ONBOARDING_REQUIRED.value]:
        redirect_target = f"{FRONTEND_URL}/onboarding"
    elif user.onboarding_status == OnboardingStatus.PENDING_VERIFICATION.value:
        redirect_target = f"{FRONTEND_URL}/pending"
    elif user.role == Role.EMPLOYEE.value:
        redirect_target = f"{FRONTEND_URL}/employee/dashboard"

    res = RedirectResponse(redirect_target)
    res.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in prod
        max_age=7 * 24 * 3600,
        path="/"
    )
    return res

@router.get("/me")
def get_me(request: Request, current_user: User = Depends(get_current_user)):
    session_token = getattr(request.state, "session_token", None) or request.cookies.get("session_id")
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "profile_image_url": current_user.profile_image_url,
        "onboarding_status": current_user.onboarding_status,
        "role": current_user.role,
        "requested_role": current_user.requested_role,
        "language": current_user.language,
        "phone_number": current_user.phone_number,
        "authentication_provider": current_user.authentication_provider,
        "session_token": session_token
    }

class SendOTPRequest(BaseModel):
    phone_number: str

class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp: str

def normalize_phone(phone: str) -> str:
    cleaned = re.sub(r'\D', '', phone)
    if len(cleaned) == 10:
        return f"+91{cleaned}"
    if len(cleaned) == 12 and cleaned.startswith("91"):
        return f"+{cleaned}"
    raise ValueError("Invalid Indian mobile number format")

@router.post("/mobile/send-otp")
def send_otp(req: SendOTPRequest, db: Session = Depends(get_db)):
    try:
        phone = normalize_phone(req.phone_number)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mobile number")
        
    OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
    OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))
    
    now = datetime.now(timezone.utc)
    
    # Check rate limit
    recent_otp = db.query(OTPRecord).filter(
        OTPRecord.phone_number == phone
    ).order_by(OTPRecord.created_at.desc()).first()
    
    if recent_otp:
        if recent_otp.created_at.tzinfo is None:
            created_at_utc = recent_otp.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at_utc = recent_otp.created_at.astimezone(timezone.utc)
            
        elapsed_seconds = (now - created_at_utc).total_seconds()
        
        # Handle stale/future records from previous broken tests (e.g. clock drift)
        if elapsed_seconds < 0:
            elapsed_seconds = OTP_RESEND_COOLDOWN_SECONDS
            
        if elapsed_seconds < OTP_RESEND_COOLDOWN_SECONDS:
            remaining_seconds = max(0, int(OTP_RESEND_COOLDOWN_SECONDS - elapsed_seconds))
            if remaining_seconds > 0:
                raise HTTPException(
                    status_code=429, 
                    detail={
                        "message": "Please wait before requesting a new OTP",
                        "retry_after_seconds": remaining_seconds
                    },
                    headers={"Retry-After": str(remaining_seconds)}
                )
        
    otp = generate_otp()
    hashed_otp = hash_otp(otp)
    
    expires_at = now + timedelta(seconds=OTP_EXPIRY_SECONDS)
    
    record = OTPRecord(
        phone_number=phone,
        otp_hash=hashed_otp,
        expires_at=expires_at,
        created_at=now
    )
    db.add(record)
    db.commit()
    
    sms_service.send_otp(phone, otp)
    
    return {"message": "OTP sent successfully"}

@router.post("/mobile/verify-otp")
def verify_otp(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    try:
        phone = normalize_phone(req.phone_number)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mobile number")
        
    OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:3000")
    
    record = db.query(OTPRecord).filter(
        OTPRecord.phone_number == phone,
        OTPRecord.verified_at.is_(None)
    ).order_by(OTPRecord.created_at.desc()).first()
    
    if not record:
        raise HTTPException(status_code=400, detail="No active OTP found")
        
    if record.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Maximum attempts exceeded. Request a new OTP.")
        
    if record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP expired")
        
    if not verify_otp_hash(req.otp, record.otp_hash):
        record.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Incorrect OTP")
        
    record.verified_at = datetime.now(timezone.utc)
    db.commit()
    
    # Find or create user
    user = db.query(User).filter(
        (User.phone_number == phone) | (User.provider_subject_id == phone)
    ).first()
    if not user:
        user = User(
            email=f"{phone.strip('+')}@mobile.policypilot.internal",
            full_name="Mobile User",
            authentication_provider="mobile",
            provider_subject_id=phone,
            phone_number=phone,
            onboarding_status=OnboardingStatus.NEW.value,
            role=Role.UNASSIGNED.value,
            requested_role=Role.UNASSIGNED.value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        
    # Create session
    session_token = create_user_session(db, user.id)
    
    # Redirect logic
    redirect_target = "/dashboard"
    if user.onboarding_status in [OnboardingStatus.NEW.value, OnboardingStatus.ONBOARDING_REQUIRED.value]:
        redirect_target = "/register"

    elif user.onboarding_status == OnboardingStatus.PENDING_VERIFICATION.value:
        redirect_target = "/pending"
    elif user.role == Role.EMPLOYEE.value:
        redirect_target = "/employee/dashboard"
        
    response_data = {
        "redirect": redirect_target,
        "session_token": session_token,
        "role": user.role
    }
    response = Response(status_code=200, content=json.dumps(response_data), media_type="application/json")
    response.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 3600,
        path="/"
    )
    return response

class LocalRegisterRequest(BaseModel):
    email: str
    password: str
    role: str
    full_name: str
    phone_number: str
    language: str = "en"
    consent_accepted: bool
    # Employee fields
    organization: Optional[str] = None
    department: Optional[str] = None
    employee_id: Optional[str] = None
    designation: Optional[str] = None
    work_email: Optional[str] = None

class LocalLoginRequest(BaseModel):
    identifier: str
    password: str

@router.post("/local/register")
def local_register(req: LocalRegisterRequest, request: Request, db: Session = Depends(get_db)):
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
        
    if not req.consent_accepted:
        raise HTTPException(status_code=400, detail="Consent is required")
        
    session_token = request.cookies.get("session_id")
    current_user = None
    if session_token:
        from app.db.models import Session as SessionModel
        session_record = db.query(SessionModel).filter(SessionModel.session_token == session_token).first()
        if session_record:
            current_user = session_record.user
            
    existing = db.query(User).filter(User.email == req.email).first()
    
    hashed_password = get_password_hash(req.password)
    
    if req.role == Role.EMPLOYEE.value:
        onboarding_status = OnboardingStatus.PENDING_VERIFICATION.value
        assigned_role = Role.CUSTOMER.value # Pending employees get customer privileges
    else:
        onboarding_status = OnboardingStatus.COMPLETED.value
        assigned_role = Role.CUSTOMER.value

    # If the user is logged in as a stub (e.g. Mobile OTP) and is registering
    if current_user and current_user.onboarding_status == OnboardingStatus.NEW.value:
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already registered")
            
        current_user.email = req.email
        current_user.full_name = req.full_name
        # Keep their verified phone_number if it exists and wasn't changed (frontend locks it anyway)
        if req.phone_number:
            current_user.phone_number = req.phone_number
        current_user.language = req.language
        current_user.consent_accepted = req.consent_accepted
        current_user.hashed_password = hashed_password
        current_user.onboarding_status = onboarding_status
        current_user.role = assigned_role
        current_user.requested_role = req.role
        
        user = current_user
        
    else:
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
            
        user = User(
            email=req.email,
            full_name=req.full_name,
            phone_number=req.phone_number,
            language=req.language,
            consent_accepted=req.consent_accepted,
            authentication_provider="local",
            provider_subject_id=req.email,
            hashed_password=hashed_password,
            onboarding_status=onboarding_status,
            role=assigned_role,
            requested_role=req.role
        )
        db.add(user)
        db.flush()
    
    if req.role == Role.EMPLOYEE.value:
        from app.db.models import EmployeeRequest, EmployeeRequestStatus
        
        is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"
        auto_approve = os.getenv("EMPLOYEE_AUTO_APPROVE", "false").lower() == "true"
        
        req_status = EmployeeRequestStatus.PENDING.value
        if is_dev and auto_approve:
            req_status = EmployeeRequestStatus.APPROVED.value
            user.role = Role.EMPLOYEE.value
            user.onboarding_status = OnboardingStatus.COMPLETED.value
            
        employee_req = EmployeeRequest(
            user_id=user.id,
            organization=req.organization,
            department=req.department,
            employee_id=req.employee_id,
            designation=req.designation,
            work_email=req.work_email,
            status=req_status
        )
        if is_dev and auto_approve:
            employee_req.admin_note = "SYSTEM_DEVELOPMENT_AUTO_APPROVAL"
            employee_req.reviewed_at = datetime.now(timezone.utc)
            
        db.add(employee_req)
        
    db.commit()
    return {"message": "Account created/upgraded successfully"}

@router.post("/local/login")
def local_login(req: LocalLoginRequest, db: Session = Depends(get_db)):
    # Try finding by email or phone
    user = db.query(User).filter(
        (User.email == req.identifier) | (User.phone_number == req.identifier)
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not user.hashed_password:
        raise HTTPException(status_code=401, detail="Please login with your original authentication provider")
        
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    
    # Create session
    session_token = create_user_session(db, user.id)
    
    # Redirect logic
    redirect_target = "/dashboard"
    if user.onboarding_status in [OnboardingStatus.NEW.value, OnboardingStatus.ONBOARDING_REQUIRED.value]:
        redirect_target = "/onboarding"
    elif user.onboarding_status == OnboardingStatus.PENDING_VERIFICATION.value:
        redirect_target = "/pending"
    elif user.role == Role.EMPLOYEE.value:
        redirect_target = "/employee/dashboard"
        
    response_data = {
        "redirect": redirect_target,
        "session_token": session_token,
        "role": user.role
    }
    response = Response(status_code=200, content=json.dumps(response_data), media_type="application/json")
    response.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 3600,
        path="/"
    )
    return response

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    session_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        session_token = auth_header[7:].strip()
    if not session_token:
        session_token = request.headers.get("X-Session-ID")
    if not session_token:
        session_token = request.query_params.get("session_token")
    if not session_token:
        session_token = request.cookies.get("session_id")

    if session_token:
        # Delete from DB
        from app.db.models import Session as SessionModel
        session_record = db.query(SessionModel).filter(SessionModel.session_token == session_token).first()
        if session_record:
            db.delete(session_record)
            db.commit()
            
    response = Response(status_code=200)
    response.delete_cookie("session_id", path="/")
    return response

class ForgotPasswordRequest(BaseModel):
    identifier: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/local/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    import uuid
    user = db.query(User).filter(
        (User.email == req.identifier) | (User.phone_number == req.identifier)
    ).first()
    
    if not user:
        # Prevent user enumeration by returning success regardless
        return {"message": "If that account exists, a password reset link has been generated."}
        
    reset_token = str(uuid.uuid4())
    user.reset_token = reset_token
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()
    
    # In a real app, send an email. For local dev, print to console.
    print(f"==================================================")
    print(f"PASSWORD RESET TOKEN FOR {user.email or user.phone_number}:")
    print(f"{reset_token}")
    print(f"==================================================")
    
    return {"message": "If that account exists, a password reset link has been generated."}

@router.post("/local/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
        
    user = db.query(User).filter(
        User.reset_token == req.token,
        User.reset_token_expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
    user.hashed_password = get_password_hash(req.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()
    
    return {"message": "Password successfully reset"}

