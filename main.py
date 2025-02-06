from fastapi import FastAPI
from api.user import router as user_router
from api.etf import router as etf_router
from api.portfolio import router as portfolio_router

app = FastAPI(
    title="Get your ETF Server API",
    description="TABA 4조",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 라우터 등록
app.include_router(user_router)
app.include_router(etf_router)
app.include_router(portfolio_router)
