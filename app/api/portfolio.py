from fastapi import APIRouter, HTTPException
from app.crud.portfolio import create_portfolio_with_context, get_portfolio_logs, update_custom_portfolio
from app.schemas.portfolio import *

router = APIRouter(
    prefix="/portfolios",
    tags=["포트폴리오 API"]
)

@router.post(
    "/",
    response_model=PortfolioResponse,
    summary="MBTI 기반 기본 추천 정보 생성/조회 API"
)
def create_portfolio(request: PortfolioCreateRequest):
    result = create_portfolio_with_context(request.user_id, request.mbti_code)
    if result is None:
        raise HTTPException(status_code=404, detail="MBTI 코드가 존재하지 않습니다.")

    return result

@router.get(
    "/logs/{contextId}",
    response_model=PortfolioLogsResponse,
    summary="특정 context_id에 대한 포트폴리오 로그 조회"
)
def get_portfolio_logs_api(contextId: int):
    logs = get_portfolio_logs(contextId)

    if not logs:
        raise HTTPException(status_code=404, detail="해당 context_id에 대한 포트폴리오 로그데이터가 없습니다.")

    return {"data": logs}

@router.put(
    "/custom/{portfolioId}",
    response_model=CustomPortfolioResponse,
    summary="포트폴리오 사용자 커스텀 API"
)
def update_portfolio(portfolioId: int, request: CustomPortfolioRequest):
    success = update_custom_portfolio(portfolioId, request)

    if not success:
        raise HTTPException(status_code=500, detail="포트폴리오 업데이트 실패했습니다")

    return {"isSuccess": True}

@router.post(
    "/investment/{contextId}",
    response_model=DecisionInvestmentResponse,
    summary="모의 투자 결정 API"
)
def decision_investment(contextId: int):
    response = decision_investment(contextId)
    if not response:
        raise HTTPException(status_code=500, detail="Failed to create portfolio and revision")
    return response
