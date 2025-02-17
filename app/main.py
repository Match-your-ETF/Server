import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.user import router as user_router
from app.api.etf import router as etf_router
from app.api.mbti import router as mbti_router
from app.api.market_indicator import router as market_indicator_router
from app.api.portfolio import router as portfolio_router

load_dotenv()
API_URL = os.getenv("API_URL")
WEB_URL = os.getenv("WEB_URL")

app = FastAPI(
    title="Match your ETF Server API",
    description="TABA 4조",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path=""
)

origins = [
    "http://localhost:5173",
    WEB_URL,
    API_URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
@app.head("/")
def read_root():
    return {"message": "Hello, FastAPI is running!"}

# 라우터 등록
app.include_router(user_router)
app.include_router(etf_router)
app.include_router(mbti_router)
app.include_router(market_indicator_router)
app.include_router(portfolio_router)
