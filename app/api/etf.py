from fastapi import APIRouter, HTTPException
from app.schemas.etf import ETFResponse
from app.crud.etf import get_etf_by_ticker

router = APIRouter(
    prefix="/etfs",
    tags=["ETF API"]
)

@router.get(
    "/{ticker}",
        response_model=ETFResponse,
        summary="개별 ETF 상세 정보 조회"
)
def get_etf_api(ticker: str):
    etf = get_etf_by_ticker(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail="해당 ETF 데이터가 없습니다.")
    return etf
