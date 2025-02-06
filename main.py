from fastapi import FastAPI
from api.user import router as user_router

app = FastAPI(
    title="Get your ETF Server API",
    description="TABA 4조",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 라우터 등록
app.include_router(user_router)
