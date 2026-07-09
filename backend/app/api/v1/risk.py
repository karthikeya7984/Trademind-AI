from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.models.models import User
from app.services.risk_service import analyze_risk

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get("/{symbol}")
async def risk_analysis(symbol: str, user: User = Depends(get_current_user)):
    return await analyze_risk(symbol.upper())
