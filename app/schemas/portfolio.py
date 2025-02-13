from pydantic import BaseModel
from datetime import datetime
from pydantic.types import Json
from typing import Optional, List, Dict, Any

class PortfolioCreateRequest(BaseModel):
    user_id: int
    mbti_code: str

class PortfolioResponse(BaseModel):
    context_id: int
    portfolio_id: int
    revision_id: int
    etf1: Optional[str] = None
    allocation1: Optional[int] = None
    etf2: Optional[str] = None
    allocation2: Optional[int] = None
    etf3: Optional[str] = None
    allocation3: Optional[int] = None
    etf4: Optional[str] = None
    allocation4: Optional[int] = None
    etf5: Optional[str] = None
    allocation5: Optional[int] = None

class PortfolioLog(BaseModel):
    portfolio_id: int
    revision_id: int
    etfs: dict
    market_indicators: dict
    user_indicators: dict
    ai_feedback: dict

class PortfolioLogsResponse(BaseModel):
    data: List[PortfolioLog]

class CustomPortfolioRequest(BaseModel):
    user_id: int
    etfs: Dict[str, Any]  # JSON 데이터
    market_indicator_name: Optional[str] = None
    investment_period: Optional[int] = None
    investment_goal: Optional[str] = None
    investment_amount: Optional[int] = None
    rebalancing_frequency: Optional[int] = None

class CustomPortfolioResponse(BaseModel):
    is_success: bool

class DecisionInvestmentResponse(BaseModel):
    portfolio_id: int
    revision_id: int

class DecisionPortfolioRequest(BaseModel):
    name: str

class DecisionPortfolioResponse(BaseModel):
    context_id: int
    name: str
    user_id: int
    created_at: datetime
    updated_at: datetime
