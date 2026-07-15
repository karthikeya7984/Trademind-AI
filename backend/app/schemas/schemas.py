from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator


# ─── Auth ─────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[dict] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class MessageResponse(BaseModel):
    message: str


# ─── User ─────────────────────────────────────────────────────
class UserOut(BaseModel):
    id: str
    name: str
    email: str
    profile_image: Optional[str] = None
    account_type: str
    is_verified: bool
    is_suspended: bool
    role: str
    auth_provider: str
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    profile_image: Optional[str] = None


# ─── Admin ────────────────────────────────────────────────────
class AdminUserOut(BaseModel):
    id: str
    name: str
    email: str
    profile_image: Optional[str] = None
    account_type: str
    role: str
    is_verified: bool
    is_active: bool
    is_suspended: bool
    auth_provider: str
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminStatsOut(BaseModel):
    total_users: int
    active_users: int
    suspended_users: int
    total_trades: int
    total_predictions: int
    total_ai_chats: int
    google_users: int
    verified_users: int


class SuspendUserRequest(BaseModel):
    reason: Optional[str] = None


class AdminResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UpdateRoleRequest(BaseModel):
    role: str  # user | admin


class AnnouncementCreate(BaseModel):
    title: str
    message: str


class AnnouncementOut(BaseModel):
    id: str
    title: str
    message: str
    created_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginActivityOut(BaseModel):
    id: str
    user_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    provider: str
    success: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Portfolio ────────────────────────────────────────────────
class PortfolioItem(BaseModel):
    stock_symbol: str
    allocation_percentage: float
    average_buy_price: float
    quantity: float
    expected_return: float
    risk_score: float


class PortfolioOut(PortfolioItem):
    id: str
    user_id: str
    model_config = {"from_attributes": True}


# ─── Watchlist ────────────────────────────────────────────────
class WatchlistAdd(BaseModel):
    stock_symbol: str


class WatchlistOut(BaseModel):
    id: str
    stock_symbol: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Trade ────────────────────────────────────────────────────
class TradeCreate(BaseModel):
    stock_symbol: str
    trade_type: str
    quantity: float
    amount: float


class TradeOut(TradeCreate):
    id: str
    timestamp: datetime
    model_config = {"from_attributes": True}


# ─── Prediction ───────────────────────────────────────────────
class PredictionOut(BaseModel):
    id: str
    stock_symbol: str
    prediction: str
    confidence_score: float
    predicted_price: float
    signal: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Chat ─────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    prompt: str
    symbol: Optional[str] = None


class ChatOut(BaseModel):
    id: str
    prompt: str
    response: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Notification ─────────────────────────────────────────────
class NotificationOut(BaseModel):
    id: str
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Paper Trading ────────────────────────────────────────────
class PaperTradingOut(BaseModel):
    id: str
    balance: float
    profit_loss: float
    created_at: datetime
    model_config = {"from_attributes": True}
