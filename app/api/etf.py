from fastapi import APIRouter, HTTPException, Query
from app.schemas.etf import *
from app.crud.etf import *
from app.ai.embed import query_recommend_etfs
from app.ai.mbti import fetch_etf_mbti, recommend_etfs_adjusted_for_user

router = APIRouter(
    prefix="/etfs",
    tags=["ETF API"]
)

@router.get(
    "/detail/{ticker}",
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

@router.get(
    "/recommendation",
    response_model=RecommendETFListResponse,
    summary="(자연어) 추천 ETF 리스트 조회 API"
)
def recommend_etfs_api(query: str = Query(..., description="사용자 쿼리")):
    results = query_recommend_etfs(query)
    return RecommendETFListResponse(recommendations=results)

@router.post(
    "/recommendation/initial",
    response_model=RecommendInitialETFResponse,
    summary="추천 투자종목 최초구성 API"
)
def recommend_initial_etfs_api(
        userId: str = Query(..., description="사용자 ID"),
        portfolioId: str = Query(..., description="포트폴리오 ID"),
):
    etf_data = fetch_etf_mbti()
    results = recommend_etfs_adjusted_for_user(userId, etf_data, portfolioId)
    return RecommendInitialETFResponse(etfs=results)
