"""FastAPI application entry point for the KerenEye backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routes.market import router as market_router
from routes.portfolio import router as portfolio_router
from routes.research import router as research_router
from services.cache_service import ensure_cache_dirs


ensure_cache_dirs()

app = FastAPI(title="KerenEye API Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)
app.include_router(market_router)
app.include_router(portfolio_router)


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
