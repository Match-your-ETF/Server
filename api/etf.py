from fastapi import APIRouter, HTTPException
from crud.etf import get_all_etfs, get_etf_by_id

router = APIRouter()

@router.get("/etfs", summary="전체 ETF 조회")
def read_all_etfs():
    etfs = get_all_etfs()
    if not etfs:
        raise HTTPException(status_code=404, detail="ETF 데이터가 없습니다.")
    return etfs

@router.get("/etfs/{etf_id}", summary="ETF 상세 조회")
def read_etf(etf_id: int):
    etf = get_etf_by_id(etf_id)
    if not etf:
        raise HTTPException(status_code=404, detail="해당 ETF를 찾을 수 없습니다.")
    return etf
