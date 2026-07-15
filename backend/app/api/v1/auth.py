from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.models import User, PaperTrading, EmailToken, LoginActivity, OTPToken
from app.schemas.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    GoogleAuthRequest, ForgotPasswordRequest, ResetPasswordRequest,
    VerifyEmailRequest, MessageResponse, OTPRequest, OTPVerifyRequest, OTPRequiredResponse,
    SMSOTPRequest, SMSOTPVerifyRequest,
)
from app.services.email_service import send_verification_email, send_password_reset_email, send_otp_email
from app.core.config import settings
import secrets
import random
import time
import httpx

router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory SMS OTP store: {phone: {"otp": str, "expires_at": float}}
_sms_otp_store: dict = {}


def _user_dict(user: User) -> dict:
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "profile_image": user.profile_image, "account_type": user.account_type,
        "role": user.role, "is_verified": user.is_verified,
        "auth_provider": user.auth_provider,
    }


async def _create_email_token(db: AsyncSession, user_id: str, token_type: str, hours: int = 24) -> str:
    token = secrets.token_urlsafe(32)
    db.add(EmailToken(
        user_id=user_id,
        token=token,
        token_type=token_type,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
    ))
    return token


async def _log_activity(db: AsyncSession, user_id: str, request: Request, provider: str, success: bool):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:500]
    db.add(LoginActivity(user_id=user_id, ip_address=ip, user_agent=ua, provider=provider, success=success))


async def _generate_and_send_otp(db: AsyncSession, email: str, name: str, background_tasks: BackgroundTasks) -> str:
    """Invalidate all previous OTPs for this email, create a new one, queue send."""
    await db.execute(delete(OTPToken).where(OTPToken.email == email))
    otp = f"{random.SystemRandom().randint(0, 999999):06d}"
    db.add(OTPToken(
        email=email,
        otp=otp,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    ))
    await db.flush()
    background_tasks.add_task(send_otp_email, email, name, otp)
    return otp


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(name=body.name, email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    await db.flush()

    db.add(PaperTrading(user_id=user.id))
    verify_token = await _create_email_token(db, user.id, "verify_email", hours=24)
    await db.commit()
    await db.refresh(user)

    background_tasks.add_task(send_verification_email, user.email, user.name, verify_token)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        if user:
            await _log_activity(db, user.id, request, "email", False)
            await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended. Contact support.")

    # ── Daily OTP check: require OTP once per calendar day (resets at midnight) ──
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if user.daily_otp_verified_date != today:
        await _generate_and_send_otp(db, user.email, user.name, background_tasks)
        await db.commit()
        return OTPRequiredResponse(
            otp_required=True,
            email=user.email,
            message="Daily verification required. OTP sent to your email.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    await _log_activity(db, user.id, request, "email", True)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


@router.post("/google")
async def google_auth(
    body: GoogleAuthRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Exchange Google OAuth code, upsert user, then require OTP verification."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    # redirect_uri must exactly match what was registered in Google Cloud Console
    # and what the frontend used when initiating the OAuth flow
    redirect_uri = f"{settings.FRONTEND_URL}/auth/google/callback"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": body.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            error_detail = token_resp.json().get("error_description") or token_resp.json().get("error") or "Unknown error"
            raise HTTPException(
                status_code=400,
                detail=f"Failed to exchange Google code: {error_detail} (redirect_uri used: {redirect_uri})"
            )

        google_tokens = token_resp.json()
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {google_tokens['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Google user info")

    guser = userinfo_resp.json()
    google_id = guser.get("id")
    email = guser.get("email")
    name = guser.get("name", email)
    picture = guser.get("picture")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user:
        if not user.google_id:
            user.google_id = google_id
            user.auth_provider = "google"
        if not user.profile_image and picture:
            user.profile_image = picture
    else:
        user = User(
            name=name, email=email, google_id=google_id,
            profile_image=picture, auth_provider="google", is_verified=False,
        )
        db.add(user)
        await db.flush()
        db.add(PaperTrading(user_id=user.id))

    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended. Contact support.")

    await _generate_and_send_otp(db, email, name, background_tasks)
    await db.commit()

    return OTPRequiredResponse(
        otp_required=True,
        email=email,
        message="OTP sent to your email address",
    )


@router.post("/send-otp", response_model=MessageResponse)
async def send_otp(
    body: OTPRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Send/resend OTP to a verified Google-authenticated email."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended")

    await _generate_and_send_otp(db, body.email, user.name, background_tasks)
    await db.commit()
    return MessageResponse(message="OTP sent to your email address")


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(
    body: OTPRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Invalidate current OTP and send a fresh one."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended")

    await _generate_and_send_otp(db, body.email, user.name, background_tasks)
    await db.commit()
    return MessageResponse(message="A new OTP has been sent to your email")


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    body: OTPVerifyRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Verify OTP — on success return JWT tokens; on failure send a new OTP."""
    result = await db.execute(
        select(OTPToken).where(
            OTPToken.email == body.email,
            OTPToken.used == False,
        ).order_by(OTPToken.created_at.desc())
    )
    otp_obj = result.scalars().first()

    now = datetime.now(timezone.utc)

    def _is_expired(dt: datetime) -> bool:
        aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return aware < now

    if (
        not otp_obj
        or otp_obj.otp != body.otp.strip()
        or _is_expired(otp_obj.expires_at)
    ):
        # Invalid or expired — send a fresh OTP
        user_result = await db.execute(select(User).where(User.email == body.email))
        user = user_result.scalar_one_or_none()
        if user:
            await _generate_and_send_otp(db, body.email, user.name, background_tasks)
            await db.commit()
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP. A new OTP has been sent to your email.",
        )

    # Mark OTP used
    otp_obj.used = True

    # Mark user verified, stamp daily OTP date, log login
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    user.last_login_at = now
    user.daily_otp_verified_date = now.strftime("%Y-%m-%d")  # stamp today — valid until midnight
    provider = "email" if user.auth_provider == "email" else "google"
    await _log_activity(db, user.id, request, provider, True)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmailToken).where(
            EmailToken.token == body.token,
            EmailToken.token_type == "verify_email",
            EmailToken.used == False,
        )
    )
    token_obj = result.scalar_one_or_none()
    if not token_obj or token_obj.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    result = await db.execute(select(User).where(User.id == token_obj.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    token_obj.used = True
    await db.commit()
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user and not user.is_verified:
        token = await _create_email_token(db, user.id, "verify_email", hours=24)
        await db.commit()
        background_tasks.add_task(send_verification_email, user.email, user.name, token)
    return MessageResponse(message="If the account exists and is unverified, a new link has been sent")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user and user.password_hash:  # Only email-auth users can reset password
        token = await _create_email_token(db, user.id, "reset_password", hours=1)
        await db.commit()
        background_tasks.add_task(send_password_reset_email, user.email, user.name, token)
    return MessageResponse(message="If an account exists for this email, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmailToken).where(
            EmailToken.token == body.token,
            EmailToken.token_type == "reset_password",
            EmailToken.used == False,
        )
    )
    token_obj = result.scalar_one_or_none()
    if not token_obj or token_obj.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == token_obj.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(body.new_password)
    token_obj.used = True
    await db.commit()
    return MessageResponse(message="Password reset successfully")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == payload.get("sub")))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.is_suspended:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


@router.post("/send-sms-otp", response_model=MessageResponse)
async def send_sms_otp(body: SMSOTPRequest):
    """Send a 6-digit OTP via Twilio SMS to the given phone number."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
        raise HTTPException(status_code=501, detail="Twilio SMS not configured")

    otp = f"{random.SystemRandom().randint(0, 999999):06d}"
    _sms_otp_store[body.phone] = {"otp": otp, "expires_at": time.time() + 300}

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=f"Your TradeMind AI verification code is: {otp}. Valid for 5 minutes.",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=body.phone,
        )
    except Exception as e:
        _sms_otp_store.pop(body.phone, None)
        raise HTTPException(status_code=500, detail=f"SMS transmission failed: {str(e)}")

    return MessageResponse(message="Verification code sent to your phone.")


@router.post("/verify-sms-otp", response_model=MessageResponse)
async def verify_sms_otp(body: SMSOTPVerifyRequest):
    """Verify the 6-digit SMS OTP for the given phone number."""
    record = _sms_otp_store.get(body.phone)

    if not record:
        raise HTTPException(status_code=400, detail="No active verification session found.")
    if time.time() > record["expires_at"]:
        _sms_otp_store.pop(body.phone, None)
        raise HTTPException(status_code=400, detail="Verification code has expired.")
    if record["otp"] != body.otp.strip():
        raise HTTPException(status_code=400, detail="Incorrect verification code.")

    _sms_otp_store.pop(body.phone, None)
    return MessageResponse(message="Phone number verified successfully.")
