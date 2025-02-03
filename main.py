from fastapi import FastAPI
from api.etf import router as etf_router

app = FastAPI()

app.include_router(etf_router)
