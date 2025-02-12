from fastapi import APIRouter, Query, HTTPException
from typing import List
from app.schemas.user import UserResponse, UserLog
from app.crud.user import get_user_by_id, get_user_logs

router = APIRouter(
    prefix="/users",
    tags=["회원 API"]
)

@router.get(
    "/{userId}",
    response_model=UserResponse,
    summary="사용자 정보 조회 API"
)
def get_user_api(userId: int):
    user = get_user_by_id(userId)
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자 정보가 없습니다.")
    return user

@router.get(
    "/mypage/logs",
    response_model=List[UserLog],
    summary="사용자 context 리스트 조회"
)
def read_user_logs(userId: int = Query(..., description="사용자 ID")):
    return get_user_logs(userId)
