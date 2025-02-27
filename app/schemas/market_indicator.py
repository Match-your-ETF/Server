from typing import List
from pydantic import BaseModel
from datetime import datetime

class MarketIndicatorResponse(BaseModel):
    market_indicator_id: int
    name: str
    interest_rate: float
    inflation_rate: float
    exchange_rate: float
    created_at: datetime
    updated_at: datetime

class MarketIndicatorsResponse(BaseModel):
    data: List[MarketIndicatorResponse]
