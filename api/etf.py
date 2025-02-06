from fastapi import APIRouter, HTTPException
from schemas.etf import ETFResponse
from crud.etf import get_etf_by_ticker

router = APIRouter(
    prefix="/etfs",
    tags=["ETF API"]  # Swagger UI에서 API 그룹 이름 설정
)

@router.get("/{ticker}",
            response_model=ETFResponse,
            summary="개별 ETF 상세 정보 조회"
)
def get_etf_api(ticker: str):
    etf = get_etf_by_ticker(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail="ETF not found")
    return etf
