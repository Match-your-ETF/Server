from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    name: str
    age: int
    mbti_code: str
    mbti_vector: str

class UserResponse(BaseModel):
    user_id: int
    name: str
    age: int
    target_investment_period: Optional[int] = None
    investment_goal: Optional[str] = None
    rebalancing_frequency: Optional[int] = None
    mbti_code: str
    mbti_vector: str
    created_at: datetime
    updated_at: datetime
