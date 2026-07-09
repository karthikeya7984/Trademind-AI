from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, AIChatHistory
from app.schemas.schemas import ChatRequest, ChatOut
from app.services.ai_service import chat_with_ai

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


@router.post("/chat", response_model=ChatOut)
async def chat(body: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Fetch last 6 turns of history for conversation context
    hist_result = await db.execute(
        select(AIChatHistory)
        .where(AIChatHistory.user_id == user.id)
        .order_by(AIChatHistory.created_at.desc())
        .limit(6)
    )
    history = [
        {"prompt": h.prompt, "response": h.response}
        for h in reversed(hist_result.scalars().all())
    ]

    response_text = await chat_with_ai(
        prompt=body.prompt,
        history=history,
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
        select(AIChatHistory).where(AIChatHistory.user_id == user.id).order_by(AIChatHistory.created_at.desc()).limit(100)
    )
    return result.scalars().all()
