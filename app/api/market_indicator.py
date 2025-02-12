from fastapi import APIRouter, HTTPException
from app.schemas.market_indicator import MarketIndicatorResponse, MarketIndicatorsResponse
from app.crud.market_indicator import get_market_indicator_by_name, get_market_indicators

router = APIRouter(
    prefix="/markets",
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
        raise HTTPException(status_code=404, detail="해당 시장 지표 데이터가 없습니다.")

    return market_data

@router.get(
    "/",
    response_model=MarketIndicatorsResponse,
    summary="시장 지표 전체 조회")
def get_markets_api():
    market_data = get_market_indicators()

    if not market_data:
        raise HTTPException(status_code=404, detail="시장 지표 데이터가 없습니다.")

    return {"data": market_data}
