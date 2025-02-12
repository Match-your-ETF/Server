from fastapi import APIRouter, HTTPException, Query
from app.schemas.etf import *
from app.crud.etf import *

router = APIRouter(
    prefix="/etfs",
    tags=["ETF API"]
)

@router.get(
    "/{ticker}",
        response_model=ETFResponse,
        summary="개별 ETF 상세 정보 조회 API"
)
def get_etf_api(ticker: str):
    etf = get_etf_by_ticker(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail="해당 ETF 데이터가 없습니다.")
    return etf

@router.get(
    "/search",
    response_model=SearchETFResponse,
    summary="ETF 검색 API"
)
def search_etfs_api(keyword: str = Query(..., description="검색할 키워드")):
    results = search_etfs(keyword)
    return {"data": results}
