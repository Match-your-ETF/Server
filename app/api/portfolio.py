from fastapi import APIRouter, HTTPException
from app.crud.portfolio import *
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
def create_portfolio_api(request: PortfolioCreateRequest):
    result = create_portfolio_with_context(request.user_id, request.mbti_code)

    if result is None:
        raise HTTPException(status_code=404, detail="MBTI 코드가 존재하지 않습니다.")

    return result

@router.get(
    "/{contextId}/logs",
    response_model=PortfolioLogsResponse,
    summary="특정 context_id에 대한 포트폴리오 로그 조회 API"
)
def get_portfolio_logs_api(contextId: int):
    logs = get_portfolio_logs(contextId)

    if not logs:
        raise HTTPException(status_code=404, detail="해당 context_id에 대한 포트폴리오 로그 데이터가 없습니다.")

    return {"data": logs}

@router.put(
    "/{portfolioId}/custom",
    response_model=CustomPortfolioResponse,
    summary="포트폴리오 사용자 커스텀 API"
)
def update_portfolio_api(portfolioId: int, request: CustomPortfolioRequest):
    success = update_custom_portfolio(portfolioId, request)

    if not success:
        raise HTTPException(status_code=500, detail="포트폴리오 업데이트 실패했습니다")

    return {"is_success": True}

@router.post(
    "/{contextId}",
    response_model=DecisionInvestmentResponse,
    summary="새 포트폴리오 생성 API"
)
def decision_investment_api(contextId: int):
    response = decision_investment(contextId)

    if response is None:
        raise HTTPException(status_code=500, detail="모의 투자 결정 실패")

    return response

@router.put(
    "/{contextId}/decision",
    response_model=DecisionPortfolioResponse,
    summary="최종 결정 API"
)
def decision_portfolio_api(contextId: int, request: DecisionPortfolioRequest):
    response = decision_portfolio(contextId, request)

    if response is None:
        raise HTTPException(status_code=404, detail="해당 context_id가 존재하지 않습니다.")

    return response
