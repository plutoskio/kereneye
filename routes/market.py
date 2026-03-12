"""Market brief and overview routes."""

from __future__ import annotations

from datetime import timedelta

import asyncer
import requests
import yfinance as yf
from fastapi import APIRouter, HTTPException

import config
from crew.research_crew import run_market_brief_crew
from data.collector import DataCollector
from services.cache_service import (
    BRIEFS_CACHE_DIR,
    cache_path,
    load_cached_analysis,
    save_analysis_cache,
)
from services.runtime_state import brief_task_status


router = APIRouter(prefix="/api/market", tags=["market"])


def _fetch_market_overview() -> dict:
    indices = {
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "FTSE 100": "^FTSE",
        "CAC 40": "^FCHI",
        "DAX": "^GDAXI",
        "Nikkei 225": "^N225",
    }
    result = {"indices": [], "news": []}

    tickers = yf.Tickers(" ".join(indices.values()))
    for name, symbol in indices.items():
        try:
            info = tickers.tickers[symbol].info
            if info:
                current = info.get("regularMarketPrice", info.get("previousClose", 0))
                prev = info.get("regularMarketPreviousClose", info.get("previousClose", 1))
                if current and prev:
                    pct_change = ((current - prev) / prev) * 100
                    result["indices"].append(
                        {
                            "name": name,
                            "price": round(current, 2),
                            "change_pct": round(pct_change, 2),
                        }
                    )
        except Exception as e:
            print(f"Failed to fetch index {symbol}: {e}")

    try:
        api_key = config.FINNHUB_API_KEY
        if api_key:
            url = f"https://finnhub.io/api/v1/news?category=general&token={api_key}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                for item in response.json()[:5]:
                    if item.get("headline"):
                        result["news"].append(
                            {
                                "title": item.get("headline", ""),
                                "publisher": item.get("source", "Market News"),
                                "link": item.get("url", "#"),
                                "timestamp": item.get("datetime", 0),
                            }
                        )
    except Exception as e:
        print(f"Failed to fetch market news from Finnhub: {e}")

    return result


@router.get("/brief")
async def get_market_brief_cache():
    """Return the cached daily market brief when it is still fresh."""
    brief, age = load_cached_analysis(
        cache_path(BRIEFS_CACHE_DIR, "daily"),
        timedelta(hours=24),
    )
    return {
        "brief": brief,
        "cached": brief is not None,
        "age_hours": int(age.total_seconds() / 3600) if age else 0,
    }


@router.post("/brief")
async def generate_market_brief():
    """Generate and persist a fresh daily market brief."""
    brief_task_status["status"] = "Collecting Market Data"

    try:
        collector = DataCollector()
        brief_data = await asyncer.asyncify(collector.collect_market_brief_data)()
    except Exception as e:
        brief_task_status["status"] = "Error: Data collection failed"
        raise HTTPException(status_code=500, detail=str(e))

    def progress_callback(status: str):
        brief_task_status["status"] = status

    try:
        brief_markdown = await asyncer.asyncify(run_market_brief_crew)(brief_data, progress_callback)
    except Exception as e:
        brief_task_status["status"] = "Error: Agent failed"
        raise HTTPException(status_code=500, detail=str(e))

    brief_task_status["status"] = "Complete"
    save_analysis_cache(cache_path(BRIEFS_CACHE_DIR, "daily"), brief_markdown)
    return {"brief": brief_markdown, "cached": False, "age_hours": 0}


@router.get("/brief/status")
async def get_market_brief_status():
    """Return the current status for daily brief generation."""
    return brief_task_status


@router.get("/overview")
async def get_market_overview():
    """Fetch major index moves and current market headlines."""
    return await asyncer.asyncify(_fetch_market_overview)()
