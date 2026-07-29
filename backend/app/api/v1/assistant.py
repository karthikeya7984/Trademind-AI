from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, AIChatHistory
from app.schemas.schemas import ChatRequest, ChatOut
from app.assistant.assistant import chat as assistant_chat

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


@router.post("/chat")
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Public chat endpoint — no JWT required for name-only login."""
    response_text = await assistant_chat(
        prompt=body.prompt,
        user_id="anonymous",
        symbol=body.symbol,
    )
    return {"response": response_text, "prompt": body.prompt}


@router.post("/chat/auth", response_model=ChatOut)
async def chat_auth(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Authenticated chat — saves history to DB."""
    response_text = await assistant_chat(
        prompt=body.prompt,
        user_id=str(user.id),
        symbol=body.symbol,
    )
    record = AIChatHistory(user_id=user.id, prompt=body.prompt, response=response_text)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/history", response_model=List[ChatOut])
async def get_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AIChatHistory)
        .where(AIChatHistory.user_id == user.id)
        .order_by(AIChatHistory.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()
