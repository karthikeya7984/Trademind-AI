from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.models import User, PaperTrading, EmailToken, OTPToken
from app.schemas.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
    VerifyEmailRequest, MessageResponse, OTPVerifyRequest,
)
from app.services.email_service import send_verification_email, send_password_reset_email, send_otp_email
import secrets
import random
import httpx

router = APIRouter(prefix="/auth", tags=["Authentication"])


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


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended. Contact support.")

    user.last_login_at = datetime.now(timezone.utc)
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
    if user and user.password_hash:
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


# ─── Google OAuth ─────────────────────────────────────────────────────────────

@router.get("/google")
async def google_login():
    """Redirect user to Google OAuth consent screen."""
    redirect_uri = "http://localhost:8000/api/v1/auth/google/callback"
    params = (
        f"client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        "&access_type=offline"
        "&prompt=select_account"
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/google/callback")
async def google_callback(
    code: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Exchange Google code for user info, send OTP, redirect to OTP page."""
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": "http://localhost:8000/api/v1/auth/google/callback",
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            return RedirectResponse(f"{settings.FRONTEND_URL}/login?error=google_failed")

        id_token = token_resp.json().get("id_token")
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_resp.json()['access_token']}"},
        )

    userinfo = userinfo_resp.json()
    email = userinfo.get("email")
    name = userinfo.get("name", email)
    google_id = userinfo.get("sub")
    picture = userinfo.get("picture")

    if not email:
        return RedirectResponse(f"{settings.FRONTEND_URL}/login?error=no_email")

    # Upsert user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            name=name, email=email, google_id=google_id,
            profile_image=picture, auth_provider="google", is_verified=True,
        )
        db.add(user)
        await db.flush()
        db.add(PaperTrading(user_id=user.id))
    else:
        if not user.google_id:
            user.google_id = google_id
        if picture and not user.profile_image:
            user.profile_image = picture
        user.auth_provider = "google"

    if user.is_suspended:
        await db.commit()
        return RedirectResponse(f"{settings.FRONTEND_URL}/login?error=suspended")

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    db.add(OTPToken(
        email=email,
        otp=otp,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    ))
    await db.commit()

    background_tasks.add_task(send_otp_email, email, name, otp)
    return RedirectResponse(f"{settings.FRONTEND_URL}/auth/verify-otp?email={email}")


@router.post("/google/verify-otp", response_model=TokenResponse)
async def google_verify_otp(body: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    """Verify OTP and return JWT tokens."""
    result = await db.execute(
        select(OTPToken).where(
            OTPToken.email == body.email,
            OTPToken.otp == body.otp,
            OTPToken.used == False,
        )
    )
    otp_obj = result.scalar_one_or_none()
    if not otp_obj or otp_obj.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp_obj.used = True
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


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
