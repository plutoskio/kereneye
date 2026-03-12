"""Research and company-data routes."""

from __future__ import annotations

from datetime import timedelta

import asyncer
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from crew.research_crew import run_news_analysis_crew, run_research_crew
from data.collector import DataCollector
from services.cache_service import (
    NEWS_CACHE_DIR,
    REPORTS_CACHE_DIR,
    cache_path,
    load_cached_analysis,
    save_analysis_cache,
)
from services.runtime_state import (
    company_data_cache,
    news_task_status,
    research_task_status,
)


router = APIRouter(prefix="/api", tags=["research"])


class CompanyResponse(BaseModel):
    ticker: str
    name: str
    sector: str
    industry: str
    market_cap: float
    current_price: float
    ratios: dict
    price_history: list[dict]


def _serialize_price_history(price_history) -> list[dict]:
    historical_prices = []
    if price_history is None or price_history.empty:
        return historical_prices

    df = price_history.reset_index()
    for _, row in df.iterrows():
        historical_prices.append(
            {
                "date": row["Date"].strftime("%Y-%m-%d")
                if hasattr(row["Date"], "strftime")
                else str(row["Date"]),
                "price": float(row["Close"]),
            }
        )

    return historical_prices


async def _collect_full_company_data(ticker: str):
    if ticker in company_data_cache:
        data = company_data_cache[ticker]
    else:
        collector = DataCollector()
        data = await asyncer.asyncify(collector.collect_core_data)(ticker)
        company_data_cache[ticker] = data

    collector = DataCollector()
    data = await asyncer.asyncify(collector.collect_full_data)(data)
    company_data_cache[ticker] = data
    return data


@router.get("/company/{ticker}", response_model=CompanyResponse)
async def get_company_data(ticker: str):
    """Fetch the core company data used by the stock detail page."""
    ticker = ticker.upper()
    collector = DataCollector()
    data = await asyncer.asyncify(collector.collect_core_data)(ticker)

    if not data.name or data.name == ticker:
        raise HTTPException(status_code=404, detail="Company data not found")

    company_data_cache[ticker] = data

    return CompanyResponse(
        ticker=data.ticker,
        name=data.name,
        sector=data.sector,
        industry=data.industry,
        market_cap=data.market_cap,
        current_price=data.current_price,
        ratios=data.ratios,
        price_history=_serialize_price_history(data.price_history),
    )


@router.get("/research/{ticker}")
async def get_research_report_cache(ticker: str):
    """Return a fresh cached executive dossier when one exists."""
    ticker = ticker.upper()
    report, age = load_cached_analysis(
        cache_path(REPORTS_CACHE_DIR, ticker),
        timedelta(days=30),
    )
    return {
        "report": report,
        "cached": report is not None,
        "age_days": age.days if age else 0,
    }


@router.post("/research/{ticker}")
async def generate_research_report(ticker: str):
    """Generate and persist a new executive dossier."""
    ticker = ticker.upper()
    research_task_status[ticker] = "Collecting Data"

    try:
        data = await _collect_full_company_data(ticker)
        if not data.name or data.name == ticker:
            research_task_status[ticker] = "Error: Company not found"
            raise HTTPException(status_code=404, detail="Company data not found")
    except HTTPException:
        raise
    except Exception as e:
        research_task_status[ticker] = "Error: Data collection failed"
        raise HTTPException(status_code=500, detail=str(e))

    def progress_callback(status: str):
        research_task_status[ticker] = status

    try:
        report_markdown = await asyncer.asyncify(run_research_crew)(data, progress_callback)
    except Exception as e:
        research_task_status[ticker] = "Error: Agent failed"
        raise HTTPException(status_code=500, detail=str(e))

    research_task_status[ticker] = "Complete"
    save_analysis_cache(cache_path(REPORTS_CACHE_DIR, ticker), report_markdown)
    return {"report": report_markdown}


@router.get("/research/status/{ticker}")
async def get_research_status(ticker: str):
    """Return the current report-generation status for a ticker."""
    ticker = ticker.upper()
    return {"status": research_task_status.get(ticker, "Not Started")}


@router.get("/news_analysis/{ticker}")
async def get_news_analysis_cache(ticker: str):
    """Return a fresh cached news analysis when one exists."""
    ticker = ticker.upper()
    analysis, age = load_cached_analysis(
        cache_path(NEWS_CACHE_DIR, ticker),
        timedelta(days=7),
    )
    return {
        "news_analysis": analysis,
        "cached": analysis is not None,
        "age_days": age.days if age else 0,
    }


@router.post("/news_analysis/{ticker}")
async def generate_news_analysis(ticker: str):
    """Generate and persist a stock-specific news analysis."""
    ticker = ticker.upper()
    news_task_status[ticker] = "Collecting Premium News"

    try:
        data = await _collect_full_company_data(ticker)
        if not data.name or data.name == ticker:
            news_task_status[ticker] = "Error: Company not found"
            raise HTTPException(status_code=404, detail="Company data not found")
    except HTTPException:
        raise
    except Exception as e:
        news_task_status[ticker] = "Error: Data collection failed"
        raise HTTPException(status_code=500, detail=str(e))

    def progress_callback(status: str):
        news_task_status[ticker] = status

    try:
        analysis_markdown = await asyncer.asyncify(run_news_analysis_crew)(data, progress_callback)
    except Exception as e:
        news_task_status[ticker] = "Error: Agent failed"
        raise HTTPException(status_code=500, detail=str(e))

    news_task_status[ticker] = "Complete"
    save_analysis_cache(cache_path(NEWS_CACHE_DIR, ticker), analysis_markdown)
    return {"news_analysis": analysis_markdown, "cached": False, "age_days": 0}


@router.get("/news_analysis/status/{ticker}")
async def get_news_status(ticker: str):
    """Return the current news-analysis status for a ticker."""
    ticker = ticker.upper()
    return {"status": news_task_status.get(ticker, "Not Started")}
