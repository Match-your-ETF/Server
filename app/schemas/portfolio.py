from pydantic import BaseModel
from typing import Optional
from typing import List

class PortfolioCreateRequest(BaseModel):
    user_id: int
    mbti_code: str

class PortfolioResponse(BaseModel):
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
