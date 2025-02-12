from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ETFResponse(BaseModel):
    ticker: str
    long_business_summary: Optional[str] = None
    category: str
    trailing_pe: Optional[float] = None
    trailing_annual_dividend_yield: Optional[float] = None
    beta_3year: Optional[float] = None
    total_assets: Optional[int] = None
    three_year_average_return: Optional[float] = None
    five_year_average_return: Optional[float] = None
    nav_price: Optional[float] = None
    text_vector: Optional[str] = None
    mbti_vector: Optional[str] = None
    mbti_code: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ETFItem(BaseModel):
    ticker: str

class SearchETFResponse(BaseModel):
    data: List[ETFItem]
