from fastapi import APIRouter
from app.services.risk_service import analyze_risk

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get("/{symbol}")
async def risk_analysis(symbol: str):
    return await analyze_risk(symbol.upper())
