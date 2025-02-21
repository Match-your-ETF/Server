from fastapi import APIRouter, HTTPException, Query
from app.ai.ai import generate_feedback
from app.crud.portfolio import *
from app.schemas.portfolio import *
from typing import List, Optional

router = APIRouter(
    prefix="/portfolios",
    tags=["포트폴리오 API"]
)

@router.post(
    "",
    response_model=PortfolioResponse,
    summary="MBTI 기반 기본 추천 정보 생성/조회 API"
)
def create_portfolio_api(request: PortfolioCreateRequest):
    result = create_portfolio_with_context(request.user_id, request.mbti_code, request.mbti_vector)

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

    if logs.name is None and not logs.data:
        raise HTTPException(status_code=404, detail="해당 context_id에 대한 포트폴리오 로그 데이터가 없습니다.")

    return logs

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
def create_feedback_api(
        portfolioId: int,
        user_id: int = Query(..., alias="userId", description="사용자 ID"),
        market_data: Optional[dict] = Query(None, alias="marketData", description="시장 지표 데이터 (선택 사항)")
):
    """
    사용자 포트폴리오 피드백을 생성하는 API.
    - `portfolioId`: 포트폴리오 ID
    - `userId`: 사용자 ID
    - `marketData`: 선택한 시장 지표 (없으면 "default" 사용)
    """

    # ✅ 기본값 처리: 사용자가 "선택안함"을 선택하면 "default"로 설정
    market_conditions = market_data if market_data else "default"

    feedback, ai_etfs = generate_feedback(portfolioId, user_id, market_conditions)

    if feedback is None:
        raise HTTPException(status_code=404, detail="해당 feedback이 존재하지 않습니다.")

    return FeedbackPortfolioResponse(feedback=feedback, ai_etfs=ai_etfs)