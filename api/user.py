from fastapi import APIRouter, HTTPException
from schemas.user import UserCreate, UserResponse
from crud.user import create_user, get_user_by_id

router = APIRouter(
    prefix="/users",
    tags=["회원 API"]
)

@router.post(
    "/users",
    response_model=UserResponse,
    summary="사용자 회원가입 API"
)
def create_user_api(user: UserCreate):
    user_id = create_user(user)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")
    created_user = get_user_by_id(user_id)
    return created_user

@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="사용자 정보 조회 API"
)
def get_user_api(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
