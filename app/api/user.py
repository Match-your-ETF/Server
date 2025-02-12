from fastapi import APIRouter, HTTPException
from app.schemas.user import UserResponse
from app.crud.user import get_user_by_id

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
