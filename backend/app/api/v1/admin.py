from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.security import hash_password
from app.models.models import User, TradeHistory, PredictionHistory, AIChatHistory, LoginActivity, Announcement, PaperTrading
from app.schemas.schemas import (
    AdminUserOut, AdminStatsOut, SuspendUserRequest, AdminResetPasswordRequest,
    UpdateRoleRequest, AnnouncementCreate, AnnouncementOut, LoginActivityOut, MessageResponse,
)
from app.services.email_service import send_announcement_email
from typing import Optional

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=AdminStatsOut)
async def admin_stats(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True, User.is_suspended == False))).scalar()
    suspended_users = (await db.execute(select(func.count(User.id)).where(User.is_suspended == True))).scalar()
    total_trades = (await db.execute(select(func.count(TradeHistory.id)))).scalar()
    total_predictions = (await db.execute(select(func.count(PredictionHistory.id)))).scalar()
    total_ai_chats = (await db.execute(select(func.count(AIChatHistory.id)))).scalar()
    google_users = (await db.execute(select(func.count(User.id)).where(User.auth_provider == "google"))).scalar()
    verified_users = (await db.execute(select(func.count(User.id)).where(User.is_verified == True))).scalar()

    return AdminStatsOut(
        total_users=total_users,
        active_users=active_users,
        suspended_users=suspended_users,
        total_trades=total_trades,
        total_predictions=total_predictions,
        total_ai_chats=total_ai_chats,
        google_users=google_users,
        verified_users=verified_users,
    )


@router.get("/users")
async def list_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_suspended: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    q = select(User).order_by(desc(User.created_at))
    if search:
        q = q.where((User.name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")))
    if role:
        q = q.where(User.role == role)
    if is_suspended is not None:
        q = q.where(User.is_suspended == is_suspended)
    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    users = result.scalars().all()
    return [AdminUserOut.model_validate(u) for u in users]


@router.get("/users/{user_id}", response_model=AdminUserOut)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return AdminUserOut.model_validate(user)


@router.get("/users/{user_id}/portfolio")
async def get_user_portfolio(user_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from app.models.models import Portfolio
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user_id))
    items = result.scalars().all()
    return [{"id": p.id, "stock_symbol": p.stock_symbol, "quantity": p.quantity,
             "average_buy_price": p.average_buy_price, "allocation_percentage": p.allocation_percentage} for p in items]


@router.get("/users/{user_id}/trades")
async def get_user_trades(user_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(
        select(TradeHistory).where(TradeHistory.user_id == user_id).order_by(desc(TradeHistory.timestamp)).limit(100)
    )
    trades = result.scalars().all()
    return [{"id": t.id, "stock_symbol": t.stock_symbol, "trade_type": t.trade_type,
             "quantity": t.quantity, "amount": t.amount, "timestamp": t.timestamp.isoformat()} for t in trades]


@router.get("/users/{user_id}/predictions")
async def get_user_predictions(user_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(
        select(PredictionHistory).where(PredictionHistory.user_id == user_id).order_by(desc(PredictionHistory.created_at)).limit(100)
    )
    preds = result.scalars().all()
    return [{"id": p.id, "stock_symbol": p.stock_symbol, "prediction": p.prediction,
             "confidence_score": p.confidence_score, "created_at": p.created_at.isoformat()} for p in preds]


@router.post("/users/{user_id}/suspend", response_model=MessageResponse)
async def suspend_user(
    user_id: str,
    body: SuspendUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot suspend yourself")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot suspend another admin")
    user.is_suspended = True
    user.is_active = False
    await db.commit()
    return MessageResponse(message=f"User {user.email} suspended")


@router.post("/users/{user_id}/reactivate", response_model=MessageResponse)
async def reactivate_user(user_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_suspended = False
    user.is_active = True
    await db.commit()
    return MessageResponse(message=f"User {user.email} reactivated")


@router.post("/users/{user_id}/reset-password", response_model=MessageResponse)
async def admin_reset_password(
    user_id: str,
    body: AdminResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return MessageResponse(message="Password reset successfully")


@router.patch("/users/{user_id}/role", response_model=MessageResponse)
async def update_user_role(
    user_id: str,
    body: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if body.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = body.role
    await db.commit()
    return MessageResponse(message=f"Role updated to {body.role}")


@router.get("/login-activity")
async def get_login_activity(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(
        select(LoginActivity).order_by(desc(LoginActivity.created_at)).offset(skip).limit(limit)
    )
    logs = result.scalars().all()
    return [LoginActivityOut.model_validate(l) for l in logs]


@router.post("/announcements", response_model=AnnouncementOut)
async def create_announcement(
    body: AnnouncementCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    ann = Announcement(title=body.title, message=body.message, created_by=admin.id)
    db.add(ann)
    await db.commit()
    await db.refresh(ann)

    # Send to all active users in background
    result = await db.execute(select(User).where(User.is_active == True, User.is_suspended == False))
    users = result.scalars().all()
    for user in users:
        background_tasks.add_task(send_announcement_email, user.email, user.name, body.title, body.message)

    return AnnouncementOut.model_validate(ann)


@router.get("/announcements")
async def list_announcements(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Announcement).order_by(desc(Announcement.created_at)).limit(50))
    anns = result.scalars().all()
    return [AnnouncementOut.model_validate(a) for a in anns]
