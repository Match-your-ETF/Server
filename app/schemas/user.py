from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserResponse(BaseModel):
    user_id: int
    name: str
    age: int
    investment_period: Optional[int] = None
    investment_goal: Optional[str] = None
    investment_amount: Optional[int] = None
    rebalancing_frequency: Optional[int] = None
    mbti_code: str
    mbti_vector: str
    created_at: datetime
    updated_at: datetime

class UserLog(BaseModel):
    context_id: int
    name: str
    user_id: int
    created_at: datetime
    updated_at: datetime
