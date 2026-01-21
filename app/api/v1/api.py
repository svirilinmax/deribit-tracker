from fastapi import APIRouter

from app.api.v1.endpoints import prices, workers

api_router = APIRouter()

api_router.include_router(prices.router)
api_router.include_router(workers.router)
