from typing import List
from pydantic import BaseModel
from datetime import datetime

class MarketIndicator(BaseModel):
    market_indicator_id: int
    name: str
    interest_rate: float
    inflation_rate: float
    exchange_rate: float
    created_at: datetime
    updated_at: datetime

class MarketIndicatorResponse(BaseModel):
    MarketIndicator: MarketIndicator

class MarketIndicatorsResponse(BaseModel):
    data: List[MarketIndicator]
