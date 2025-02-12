from fastapi import APIRouter, HTTPException
from app.crud.portfolio import create_portfolio_with_context, get_portfolio_logs, update_custom_portfolio
from app.schemas.portfolio import PortfolioCreateRequest, PortfolioResponse, PortfolioLogsResponse, CustomPortfolioRequest, CustomPortfolioResponse

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
    "/logs/{context_id}",
    response_model=PortfolioLogsResponse,
    summary="특정 context_id에 대한 포트폴리오 로그 조회"
)
def get_portfolio_logs_api(context_id: int):
    logs = get_portfolio_logs(context_id)

    if not logs:
        raise HTTPException(status_code=404, detail="해당 context_id에 대한 포트폴리오 로그데이터가 없습니다.")

    return {"data": logs}

@router.post(
    "/custom/{portfolio_id}",
    response_model=CustomPortfolioResponse,
    summary="사용자 커스텀 포트폴리오 생성 API"
)
def update_portfolio(portfolio_id: int, request: CustomPortfolioRequest):
    success = update_custom_portfolio(portfolio_id, request)

    if not success:
        raise HTTPException(status_code=500, detail="포트폴리오 업데이트 실패했습니다")

    return {"isSuccess": True}
