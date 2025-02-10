from fastapi import APIRouter, HTTPException
from app.schemas.market_indicator import MarketIndicatorResponse
from app.crud.market_indicator import get_market_indicator_by_name

router = APIRouter(
    prefix="/market",
    tags=["시장 지표 API"]
)

@router.get(
    "/{name}",
    response_model=MarketIndicatorResponse,
    summary="시장 지표 조회"
)
def get_market_indicator_api(name: str):
    market_data = get_market_indicator_by_name(name)

    if not market_data:
        raise HTTPException(status_code=404, detail="Market indicator not found")

    return market_data
