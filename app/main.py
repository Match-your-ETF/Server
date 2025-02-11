from fastapi import FastAPI
from app.api.user import router as user_router
from app.api.etf import router as etf_router
from app.api.mbti import router as mbti_router
from app.api.market_indicator import router as market_indicator_router
from app.api.portfolio import router as portfolio_router

app = FastAPI(
    title="Match your ETF Server API",
    description="TABA 4조",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 라우터 등록
app.include_router(user_router)
app.include_router(etf_router)
app.include_router(mbti_router)
app.include_router(market_indicator_router)
app.include_router(portfolio_router)
