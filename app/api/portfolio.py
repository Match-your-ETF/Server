from fastapi import APIRouter, HTTPException, Query
from app.schemas.portfolio import PortfolioCreate, PortfolioResponse, PortfolioListResponse
from app.crud.portfolio import create_portfolio, get_portfolio_by_id, get_portfolios_by_user

router = APIRouter(
    prefix="/portfolios",
    tags=["포트폴리오 API"]
)

@router.post(
    "/",
    response_model=PortfolioResponse,
    summary="사용자 포트폴리오 등록 API"
)
def create_portfolio_api(portfolio: PortfolioCreate):
    portfolio_id = create_portfolio(portfolio)
    if not portfolio_id:
        raise HTTPException(status_code=500, detail="Failed to create portfolio")
    created_portfolio = get_portfolio_by_id(portfolio_id)
    return created_portfolio

@router.get(
    "/{portfolioId}",
    response_model=PortfolioResponse,
    summary="사용자 개별 포트폴리오 조회 API"
)
def get_portfolio_api(portfolioId: int):
    portfolio = get_portfolio_by_id(portfolioId)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@router.get(
    "/",
    response_model=PortfolioListResponse,
    summary="사용자 포트폴리오 전체 조회 API"
)
def get_portfolios_api(userId: int = Query(..., description="User ID to filter portfolios")):
    portfolios = get_portfolios_by_user(userId)
    return {"data": portfolios}
