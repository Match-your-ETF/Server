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

    class Config:
        alias_generator = lambda string: ''.join(
            word.capitalize() if i else word
            for i, word in enumerate(string.split('_'))
        )
        populate_by_name = True
        orm_mode = True
