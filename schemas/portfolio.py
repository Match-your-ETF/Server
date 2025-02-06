from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any

class PortfolioCreate(BaseModel):
    userId: int
    name: str
    content: Dict[str, Any]  # JSON 형식

class PortfolioResponse(BaseModel):
    portfolioId: int
    userId: int
    name: str
    content: Dict[str, Any]
    createdAt: datetime
    updatedAt: datetime

    class Config:
        alias_generator = lambda string: ''.join(
            word.capitalize() if i else word
            for i, word in enumerate(string.split('_'))
        )
        populate_by_name = True

class PortfolioListResponse(BaseModel):
    data: List[PortfolioResponse]
