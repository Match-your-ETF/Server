from pydantic import BaseModel
from typing import Optional

class MbtiResponse(BaseModel):
    etf1: Optional[str]
    allocation1: Optional[int]
    etf2: Optional[str]
    allocation2: Optional[int]
    etf3: Optional[str]
    allocation3: Optional[int]
    etf4: Optional[str]
    allocation4: Optional[int]
    etf5: Optional[str]
    allocation5: Optional[int]
