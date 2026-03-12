"""Portfolio, holdings news, and market-status routes."""

from __future__ import annotations

from datetime import datetime, timedelta

import asyncer
import pytz
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from crew.research_crew import run_portfolio_news_crew
from portfolio.analytics import calculate_portfolio_performance
from services.market_data_service import get_batch_ticker_news, get_ticker_info
from services.runtime_state import (
    portfolio_manager,
    portfolio_news_task_status,
)


router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class AddHoldingRequest(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    date: str | None = None


class SellRequest(BaseModel):
    shares: float
    price: float
    date: str | None = None


class CashRequest(BaseModel):
    amount: float
    date: str | None = None


def _fetch_holdings_news(holdings) -> list[dict]:
    results = []
    news_by_ticker = get_batch_ticker_news((holding.ticker for holding in holdings), limit=5)

    for holding in holdings:
        try:
            news_raw = news_by_ticker.get(holding.ticker, [])
            news_items = []
            for item in news_raw[:5]:
                content = item.get("content", item)
                title = content.get("title", "")

                provider = content.get("provider")
                if isinstance(provider, dict):
                    publisher = provider.get("displayName", "")
                else:
                    publisher = content.get("publisher", "")

                url_obj = content.get("clickThroughUrl") or content.get("canonicalUrl")
                if isinstance(url_obj, dict):
                    link = url_obj.get("url", "")
                else:
                    link = content.get("link", "")

                news_items.append(
                    {
                        "title": title,
                        "publisher": publisher,
                        "link": link,
                    }
                )

            results.append({"ticker": holding.ticker, "news": news_items})
        except Exception as e:
            print(f"  ⚠ News fetch failed for {holding.ticker}: {e}")
            results.append({"ticker": holding.ticker, "news": []})

    return results


def _build_portfolio_news_digest(holdings_news: list[dict]) -> str:
    lines = ["PORTFOLIO NEWS DIGEST:", ""]
    for holding_news in holdings_news:
        lines.append(f"TICKER: {holding_news['ticker']}")
        if not holding_news["news"]:
            lines.append("  - No material news found.")
        else:
            for article in holding_news["news"]:
                lines.append(
                    f"  - [{article['publisher']}] {article['title']} ({article['link']})"
                )
        lines.append("")
    return "\n".join(lines)


def _get_market_status_snapshot() -> dict:
    now_utc = datetime.now(pytz.utc)

    def _get_status(tz_name: str, open_hour: int, open_min: int, close_hour: int, close_min: int):
        tz = pytz.timezone(tz_name)
        now_local = now_utc.astimezone(tz)
        weekday = now_local.weekday()

        open_time = now_local.replace(hour=open_hour, minute=open_min, second=0, microsecond=0)
        close_time = now_local.replace(hour=close_hour, minute=close_min, second=0, microsecond=0)

        is_weekday = weekday < 5
        is_market_hours = is_weekday and open_time <= now_local < close_time

        if is_market_hours:
            diff = close_time - now_local
            return {
                "is_open": True,
                "countdown_label": "Closes in",
                "countdown_seconds": int(diff.total_seconds()),
            }

        if is_weekday and now_local < open_time:
            next_open = open_time
        else:
            days_ahead = 1
            if weekday == 4 and now_local >= close_time:
                days_ahead = 3
            elif weekday == 5:
                days_ahead = 2
            elif weekday == 6:
                days_ahead = 1

            next_open = (now_local + timedelta(days=days_ahead)).replace(
                hour=open_hour,
                minute=open_min,
                second=0,
                microsecond=0,
            )

        diff = next_open - now_local
        return {
            "is_open": False,
            "countdown_label": "Opens in",
            "countdown_seconds": int(diff.total_seconds()),
        }

    nyse = _get_status("America/New_York", 9, 30, 16, 0)
    nyse["name"] = "NYSE"

    euronext = _get_status("Europe/Paris", 9, 0, 17, 30)
    euronext["name"] = "Euronext"

    return {"markets": [nyse, euronext]}


@router.get("/holdings")
async def get_portfolio_holdings():
    """Get all holdings with current prices and P&L."""
    try:
        enriched = await asyncer.asyncify(portfolio_manager.get_enriched_holdings)()
        return {
            "holdings": [h.to_dict() for h in enriched],
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/holdings")
async def add_portfolio_holding(req: AddHoldingRequest):
    """Add a new holding or increase an existing position."""
    ticker = req.ticker.upper()

    try:
        info = await asyncer.asyncify(get_ticker_info)(ticker)
        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
        )
        if not price:
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found: {e}")

    try:
        holding = portfolio_manager.add_holding(ticker, req.shares, req.avg_cost, req.date)
        return {"message": f"Added {req.shares} shares of {ticker}", "holding": holding.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/holdings/{ticker}/sell")
async def sell_portfolio_holding(ticker: str, req: SellRequest):
    """Sell shares of a holding and realize P&L."""
    ticker = ticker.upper()
    try:
        return portfolio_manager.sell_shares(ticker, req.shares, req.price, req.date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/holdings/{ticker}")
async def remove_portfolio_holding(ticker: str):
    """Remove a holding entirely from the portfolio."""
    ticker = ticker.upper()
    success = await asyncer.asyncify(portfolio_manager.remove_holding)(ticker)
    if not success:
        raise HTTPException(status_code=404, detail=f"Holding '{ticker}' not found in portfolio.")
    return {"message": f"Removed {ticker} from portfolio"}


@router.get("/cash")
async def get_cash_balance():
    """Get current cash balance."""
    return {"cash_balance": portfolio_manager.get_cash()}


@router.post("/cash")
async def set_cash_balance(req: CashRequest):
    """Set cash balance to a specific amount."""
    try:
        new_balance = portfolio_manager.set_cash(req.amount, req.date)
        return {"cash_balance": new_balance, "message": f"Cash balance set to ${new_balance:,.2f}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/summary")
async def get_portfolio_summary():
    """Get portfolio summary, allocation, and realized/unrealized P&L."""
    try:
        summary = await asyncer.asyncify(portfolio_manager.get_portfolio_summary)()
        return summary.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_portfolio_performance(period: str = "1y"):
    """Get portfolio performance metrics and benchmark history."""
    valid_periods = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd"]
    if period not in valid_periods:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {valid_periods}")

    try:
        enriched = await asyncer.asyncify(portfolio_manager.get_enriched_holdings)()
        transactions = portfolio_manager.get_transaction_models()
        cash_balance = portfolio_manager.get_cash()
        return await asyncer.asyncify(calculate_portfolio_performance)(enriched, transactions, period, cash_balance)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions")
async def get_portfolio_transactions():
    """Get transaction history in reverse chronological order."""
    return {"transactions": portfolio_manager.get_transactions()}


@router.get("/news")
async def get_portfolio_news():
    """Aggregate recent news headlines for all portfolio holdings."""
    holdings = portfolio_manager.get_holdings()
    if not holdings:
        return {"holdings_news": []}

    holdings_news = await asyncer.asyncify(_fetch_holdings_news)(holdings)
    return {"holdings_news": holdings_news}


@router.get("/news/analyze/status")
async def get_portfolio_news_status():
    """Return the current status for the portfolio impact report."""
    return portfolio_news_task_status


@router.post("/news/analyze")
async def analyze_portfolio_news():
    """Generate an AI-written portfolio-wide news impact report."""
    portfolio_news_task_status["status"] = "Fetching recent news..."
    holdings = portfolio_manager.get_holdings()
    if not holdings:
        portfolio_news_task_status["status"] = "No news found."
        return {"report": "No holdings or no recent news available to analyze."}

    holdings_news = await asyncer.asyncify(_fetch_holdings_news)(holdings)
    portfolio_news_task_status["status"] = "Structuring data for analysis..."
    news_text = _build_portfolio_news_digest(holdings_news)

    def progress_callback(status: str):
        portfolio_news_task_status["status"] = status

    try:
        portfolio_news_task_status["status"] = "Initializing AI analysis..."
        report = await asyncer.asyncify(run_portfolio_news_crew)(news_text, progress_callback)
    except Exception as e:
        portfolio_news_task_status["status"] = "Error formatting report"
        raise HTTPException(status_code=500, detail=str(e))

    portfolio_news_task_status["status"] = "Complete"
    return {"report": report}


@router.get("/market-status")
async def get_market_status():
    """Return open/closed status for NYSE and Euronext with countdowns."""
    return _get_market_status_snapshot()
