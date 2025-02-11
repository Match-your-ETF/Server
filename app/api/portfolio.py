from fastapi import APIRouter, HTTPException
from app.crud.portfolio import create_portfolio_with_context
from app.crud.portfolio import get_portfolio_logs
from app.schemas.portfolio import PortfolioCreateRequest, PortfolioResponse, PortfolioLogsResponse

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
        raise HTTPException(status_code=404, detail="해당 context_id에 대한 로그가 없습니다.")

    return {"data": logs}