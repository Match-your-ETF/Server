from pydantic import BaseModel
from typing import Optional

class ETFResponse(BaseModel):
    etfId: int
    ticker: str
    sector: str
    name: str
    mbtiCode: str
    description: Optional[str] = None
    mbtiVector: Optional[str] = None

    class Config:
        alias_generator = lambda string: ''.join(
            word.capitalize() if i else word
            for i, word in enumerate(string.split('_'))
        )
        populate_by_name = True
