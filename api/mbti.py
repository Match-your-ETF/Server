from fastapi import APIRouter, HTTPException
from schemas.mbti import MbtiResponse
from crud.mbti import get_mbti_etfs

router = APIRouter(
    prefix="/mbti",
    tags=["MBTI API"]
)

@router.get(
    "/{mbtiCode}",
    response_model=MbtiResponse,
    summary="MBTI 별 추천 ETF 조회"
)
def get_mbti_etfs_api(mbtiCode: str):
    mbti = get_mbti_etfs(mbtiCode)
    if not mbti:
        raise HTTPException(status_code=404, detail="MBTI not found")
    return mbti
