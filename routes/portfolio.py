"""Portfolio, holdings news, and market-status routes."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

import asyncer
import pandas as pd
import pytz
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from crew.research_crew import run_portfolio_news_crew
from portfolio.analytics import calculate_portfolio_performance
from services.market_data_service import (
    download_close_prices,
    get_batch_premium_ticker_news,
    get_ticker_info,
)
from services.runtime_state import (
    portfolio_manager,
    portfolio_news_task_status,
)


router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

PORTFOLIO_NEWS_LOOKBACK_DAYS = 7
PORTFOLIO_NEWS_LIMIT_PER_TICKER = 5
PORTFOLIO_NEWS_PRICE_PERIOD = "1mo"


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
    action: Literal["snapshot", "deposit", "withdraw"] = "snapshot"


def _normalize_close_prices(price_data, symbols: list[str]) -> pd.DataFrame:
    if isinstance(price_data, pd.Series):
        price_data = price_data.to_frame(name=symbols[0])

    if not isinstance(price_data, pd.DataFrame) or price_data.empty:
        return pd.DataFrame()

    normalized = price_data.copy()
    normalized.index = pd.to_datetime(normalized.index)
    if getattr(normalized.index, "tz", None) is not None:
        normalized.index = normalized.index.tz_localize(None)
    normalized.index = normalized.index.normalize()
    normalized = normalized.sort_index().ffill().dropna(how="all")

    if len(symbols) == 1 and list(normalized.columns) != [symbols[0]]:
        normalized.columns = [symbols[0]]

    return normalized


def _parse_published_timestamp(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None

    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None

    try:
        parsed = parsed.tz_localize(None)
    except TypeError:
        pass
    return parsed


def _pct_change(current_value: float | None, baseline_value: float | None) -> float | None:
    if current_value is None or baseline_value in (None, 0):
        return None
    return round(((current_value / baseline_value) - 1) * 100, 2)


def _get_close_before_publication(price_series: pd.Series, published_at: pd.Timestamp) -> tuple[pd.Timestamp | None, float | None]:
    valid = price_series.dropna()
    if valid.empty:
        return None, None

    published_day = published_at.normalize()
    earlier = valid[valid.index < published_day]
    if not earlier.empty:
        return earlier.index[-1], float(earlier.iloc[-1])

    same_or_earlier = valid[valid.index <= published_day]
    if not same_or_earlier.empty:
        return same_or_earlier.index[-1], float(same_or_earlier.iloc[-1])

    return valid.index[0], float(valid.iloc[0])


def _build_price_context(ticker: str, price_frame: pd.DataFrame, articles: list[dict]) -> dict:
    if price_frame.empty or ticker not in price_frame.columns:
        return {
            "last_close": None,
            "last_close_date": None,
            "one_day_change_pct": None,
            "five_day_change_pct": None,
            "since_first_article_change_pct": None,
            "since_first_article_label": None,
            "since_first_article_base_date": None,
        }

    series = price_frame[ticker].dropna()
    if series.empty:
        return {
            "last_close": None,
            "last_close_date": None,
            "one_day_change_pct": None,
            "five_day_change_pct": None,
            "since_first_article_change_pct": None,
            "since_first_article_label": None,
            "since_first_article_base_date": None,
        }

    last_close = float(series.iloc[-1])
    last_close_date = series.index[-1].strftime("%Y-%m-%d")
    one_day_change_pct = _pct_change(last_close, float(series.iloc[-2])) if len(series) >= 2 else None
    five_day_change_pct = _pct_change(last_close, float(series.iloc[-6])) if len(series) >= 6 else None

    published_dates = [
        parsed for parsed in (_parse_published_timestamp(article.get("published")) for article in articles)
        if parsed is not None
    ]
    earliest_article = min(published_dates) if published_dates else None
    base_date, base_close = _get_close_before_publication(series, earliest_article) if earliest_article is not None else (None, None)
    since_first_article_change_pct = _pct_change(last_close, base_close)

    return {
        "last_close": round(last_close, 2),
        "last_close_date": last_close_date,
        "one_day_change_pct": one_day_change_pct,
        "five_day_change_pct": five_day_change_pct,
        "since_first_article_change_pct": since_first_article_change_pct,
        "since_first_article_label": earliest_article.strftime("%Y-%m-%d") if earliest_article is not None else None,
        "since_first_article_base_date": base_date.strftime("%Y-%m-%d") if base_date is not None else None,
    }


def _fetch_holdings_news(holdings) -> list[dict]:
    symbols = [holding.ticker for holding in holdings]
    results = []
    news_by_ticker = get_batch_premium_ticker_news(
        symbols,
        limit=PORTFOLIO_NEWS_LIMIT_PER_TICKER,
        days=PORTFOLIO_NEWS_LOOKBACK_DAYS,
    )

    try:
        raw_prices = download_close_prices(symbols, period=PORTFOLIO_NEWS_PRICE_PERIOD)
        price_frame = _normalize_close_prices(raw_prices, symbols)
    except Exception:
        price_frame = pd.DataFrame()

    for holding in holdings:
        try:
            news_raw = news_by_ticker.get(holding.ticker, [])
            news_items = []
            for item in news_raw[:PORTFOLIO_NEWS_LIMIT_PER_TICKER]:
                news_items.append(
                    {
                        "title": item.get("title", ""),
                        "publisher": item.get("publisher", ""),
                        "link": item.get("link", ""),
                        "published": item.get("published", ""),
                        "teaser": item.get("teaser", ""),
                    }
                )

            latest_published = max((article.get("published", "") for article in news_items), default="")
            results.append(
                {
                    "ticker": holding.ticker,
                    "news": news_items,
                    "news_count": len(news_items),
                    "latest_published": latest_published,
                    "price_context": _build_price_context(holding.ticker, price_frame, news_items),
                }
            )
        except Exception as e:
            print(f"  ⚠ News fetch failed for {holding.ticker}: {e}")
            results.append(
                {
                    "ticker": holding.ticker,
                    "news": [],
                    "news_count": 0,
                    "latest_published": "",
                    "price_context": _build_price_context(holding.ticker, price_frame, []),
                }
            )

    return sorted(results, key=lambda item: item.get("latest_published", ""), reverse=True)


def _build_portfolio_news_digest(holdings_news: list[dict]) -> str:
    lines = ["PORTFOLIO NEWS DIGEST:", ""]
    for holding_news in holdings_news:
        lines.append(f"TICKER: {holding_news['ticker']}")
        price_context = holding_news.get("price_context") or {}
        price_bits = []
        if price_context.get("last_close") is not None:
            price_bits.append(
                f"Last close: ${price_context['last_close']:.2f} on {price_context['last_close_date']}"
            )
        if price_context.get("one_day_change_pct") is not None:
            price_bits.append(f"1D: {price_context['one_day_change_pct']:+.2f}%")
        if price_context.get("five_day_change_pct") is not None:
            price_bits.append(f"5D: {price_context['five_day_change_pct']:+.2f}%")
        if price_context.get("since_first_article_change_pct") is not None:
            since_label = price_context.get("since_first_article_label") or "first article"
            price_bits.append(
                f"Since first article ({since_label}): {price_context['since_first_article_change_pct']:+.2f}%"
            )
        if price_bits:
            lines.append(f"  Price Reaction: {' | '.join(price_bits)}")

        if not holding_news["news"]:
            lines.append("  - No material news found.")
        else:
            for article in holding_news["news"]:
                published = article.get("published")
                teaser = article.get("teaser")
                lines.append(
                    f"  - [{article['publisher']}] {article['title']}"
                )
                if published:
                    lines.append(f"    Published: {published}")
                if teaser:
                    lines.append(f"    Summary: {teaser[:300]}")
                if article.get("link"):
                    lines.append(f"    Link: {article['link']}")
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
    """Apply a cash snapshot, deposit, or withdrawal."""
    try:
        if req.action == "deposit":
            new_balance = portfolio_manager.deposit_cash(req.amount, req.date)
            message = f"Recorded cash deposit of ${req.amount:,.2f}"
        elif req.action == "withdraw":
            new_balance = portfolio_manager.withdraw_cash(req.amount, req.date)
            message = f"Recorded cash withdrawal of ${req.amount:,.2f}"
        else:
            new_balance = portfolio_manager.set_cash(req.amount, req.date)
            message = f"Recorded cash snapshot of ${req.amount:,.2f}"

        return {"cash_balance": new_balance, "message": message}
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
    """Aggregate recent premium news for all portfolio holdings."""
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
    portfolio_news_task_status["status"] = "Fetching premium news..."
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
