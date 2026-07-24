from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.models import User, PaperTrading, EmailToken, OTPToken
from app.schemas.schemas import MessageResponse, RefreshRequest, TokenResponse, ForgotPasswordRequest, ResetPasswordRequest
from app.services.email_service import send_otp_email, send_password_reset_email
from pydantic import BaseModel, EmailStr
import secrets
import random

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SignupStep1Request(BaseModel):
    name: str
    email: EmailStr

class SignupStep2Request(BaseModel):
    name: str
    email: EmailStr
    otp: str
    password: str

class SigninStep1Request(BaseModel):
    identifier: str  # username or email
    password: str

class SigninStep2Request(BaseModel):
    email: EmailStr
    otp: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user_dict(user: User) -> dict:
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "profile_image": user.profile_image, "account_type": user.account_type,
        "role": user.role, "is_verified": user.is_verified,
        "auth_provider": user.auth_provider,
    }

async def _send_otp(email: str, name: str, db: AsyncSession, background_tasks: BackgroundTasks):
    otp = str(random.randint(100000, 999999))
    db.add(OTPToken(
        email=email,
        otp=otp,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    ))
    await db.commit()
    background_tasks.add_task(send_otp_email, email, name, otp)


# ── Sign Up ───────────────────────────────────────────────────────────────────

@router.post("/signup/send-otp", response_model=MessageResponse)
async def signup_send_otp(
    body: SignupStep1Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    name_check = await db.execute(select(User).where(User.name == body.name))
    if name_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken.")

    email_check = await db.execute(select(User).where(User.email == body.email))
    if email_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered.")

    await _send_otp(body.email, body.name, db, background_tasks)
    return MessageResponse(message="OTP sent to your email. Valid for 10 minutes.")


@router.post("/signup/complete", response_model=TokenResponse)
async def signup_complete(
    body: SignupStep2Request,
    db: AsyncSession = Depends(get_db),
):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    otp_result = await db.execute(
        select(OTPToken).where(
            OTPToken.email == body.email,
            OTPToken.otp == body.otp,
            OTPToken.used == False,
        )
    )
    otp_obj = otp_result.scalar_one_or_none()
    if not otp_obj or otp_obj.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    name_check = await db.execute(select(User).where(User.name == body.name))
    if name_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken.")

    email_check = await db.execute(select(User).where(User.email == body.email))
    if email_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        is_verified=True,
        auth_provider="email",
    )
    db.add(user)
    await db.flush()
    db.add(PaperTrading(user_id=user.id))
    otp_obj.used = True
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


class MessageWithEmailResponse(BaseModel):
    message: str
    email: str


# ── Sign In ───────────────────────────────────────────────────────────────────

@router.post("/signin/send-otp", response_model=MessageWithEmailResponse)
async def signin_send_otp(
    body: SigninStep1Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            or_(User.email == body.identifier, User.name == body.identifier)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended. Contact support.")

    await _send_otp(user.email, user.name, db, background_tasks)
    return MessageWithEmailResponse(message=f"OTP sent to your email. Valid for 10 minutes.", email=user.email)


@router.post("/signin/verify-otp", response_model=TokenResponse)
async def signin_verify_otp(
    body: SigninStep2Request,
    db: AsyncSession = Depends(get_db),
):
    otp_result = await db.execute(
        select(OTPToken).where(
            OTPToken.email == body.email,
            OTPToken.otp == body.otp,
            OTPToken.used == False,
        )
    )
    otp_obj = otp_result.scalar_one_or_none()
    if not otp_obj or otp_obj.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    otp_obj.used = True
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


# ── Forgot / Reset Password ───────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user and user.password_hash:
        token = secrets.token_urlsafe(32)
        db.add(EmailToken(
            user_id=user.id, token=token,
            token_type="reset_password",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ))
        await db.commit()
        background_tasks.add_task(send_password_reset_email, user.email, user.name, token)
    return MessageResponse(message="If an account exists, a reset link has been sent.")


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
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    result = await db.execute(select(User).where(User.id == token_obj.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.password_hash = hash_password(body.new_password)
    token_obj.used = True
    await db.commit()
    return MessageResponse(message="Password reset successfully.")


# ── Refresh Token ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    result = await db.execute(select(User).where(User.id == payload.get("sub")))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.is_suspended:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )
