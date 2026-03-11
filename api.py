"""
FastAPI Backend for KerenEye Web Dashboard.
Exposes the DataCollector and ResearchCrew logic via simple REST endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import json
import asyncer
import yfinance as yf
import requests
import config

from datetime import datetime, timedelta

from data.collector import DataCollector, MarketBriefData
from crew.research_crew import run_research_crew, run_news_analysis_crew, run_market_brief_crew, run_portfolio_news_crew
from portfolio.manager import PortfolioManager
from portfolio.analytics import calculate_portfolio_performance

app = FastAPI(title="KerenEye API Dashboard")

# --- Setup Persistent Caching Directories ---
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
REPORTS_CACHE_DIR = os.path.join(CACHE_DIR, "reports")
NEWS_CACHE_DIR = os.path.join(CACHE_DIR, "news")
BRIEFS_CACHE_DIR = os.path.join(CACHE_DIR, "briefs")

os.makedirs(REPORTS_CACHE_DIR, exist_ok=True)
os.makedirs(NEWS_CACHE_DIR, exist_ok=True)
os.makedirs(BRIEFS_CACHE_DIR, exist_ok=True)

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production to match your frontend URI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CompanyResponse(BaseModel):
    ticker: str
    name: str
    sector: str
    industry: str
    market_cap: float
    current_price: float
    ratios: dict
    price_history: list[dict] # Formatted for the frontend chart

# Keep a simple in-memory session cache
_cache = {}

# Global dictionary to store the current generation status for a given ticker
_task_status = {}
_news_task_status = {}
_brief_task_status = {"status": "Not Started"}

@app.get("/api/company/{ticker}", response_model=CompanyResponse)
async def get_company_data(ticker: str):
    """
    Instantly fetch the raw core company data and price history to populate the frontend dashboard.
    """
    ticker = ticker.upper()
    collector = DataCollector()
    
    # Run ONLY the fast core logic (YFinance)
    data = await asyncer.asyncify(collector.collect_core_data)(ticker)
    
    if not data.name or data.name == ticker:
        raise HTTPException(status_code=404, detail="Company data not found")
        
    # Cache it for the research crew
    _cache[ticker] = data

    # Parse dataframe into a list of dicts for the frontend charting library
    historical_prices = []
    if data.price_history is not None and not data.price_history.empty:
        # Reset index to get 'Date' as a column
        df = data.price_history.reset_index()
        for _, row in df.iterrows():
            historical_prices.append({
                "date": row['Date'].strftime("%Y-%m-%d") if hasattr(row['Date'], 'strftime') else str(row['Date']),
                "price": float(row['Close'])
            })

    return CompanyResponse(
        ticker=data.ticker,
        name=data.name,
        sector=data.sector,
        industry=data.industry,
        market_cap=data.market_cap,
        current_price=data.current_price,
        ratios=data.ratios,
        price_history=historical_prices
    )


@app.get("/api/research/{ticker}")
async def get_research_report_cache(ticker: str):
    """
    Checks if a valid, unexpired Executive Dossier exists.
    Returns the report if < 30 days old. Otherwise returns null.
    """
    ticker = ticker.upper()
    cache_file = os.path.join(REPORTS_CACHE_DIR, f"{ticker}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
            
            timestamp = datetime.fromisoformat(cached_data["timestamp"])
            age = datetime.now() - timestamp
            
            if age < timedelta(days=30):
                return {"report": cached_data["analysis"], "cached": True, "age_days": age.days}
        except Exception as e:
            print(f"Error reading cache for {ticker}: {e}")
            
    # Explicitly return null if it's expired or doesn't exist
    return {"report": None, "cached": False, "age_days": 0}


@app.post("/api/research/{ticker}")
async def generate_research_report(ticker: str):
    """
    Triggers the deep data collection and crew AI agents to generate a new Executive Dossier.
    Saves the result to persistent cache.
    """
    ticker = ticker.upper()
    _task_status[ticker] = "Collecting Full Data"
    
    try:
        if ticker in _cache:
            data = _cache[ticker]
        else:
            collector = DataCollector()
            data = await asyncer.asyncify(collector.collect_core_data)(ticker)
        
        # Now run the heavy data fetching (Finnhub peers, FRED macro, etc)
        collector = DataCollector()
        data = await asyncer.asyncify(collector.collect_full_data)(data)

        if not data.name or data.name == ticker:
            _task_status[ticker] = "Error: Company not found"
            raise HTTPException(status_code=404, detail="Company data not found")
            
    except Exception as e:
        _task_status[ticker] = f"Error: Data collection failed"
        raise HTTPException(status_code=500, detail=str(e))

    def progress_callback(status: str):
        _task_status[ticker] = status

    try:
        report_markdown = await asyncer.asyncify(run_research_crew)(data, progress_callback)
    except Exception as e:
        _task_status[ticker] = f"Error: Agent failed"
        raise HTTPException(status_code=500, detail=str(e))
        
    _task_status[ticker] = "Complete"
    
    # Save to persistent cache
    cache_file = os.path.join(REPORTS_CACHE_DIR, f"{ticker}.json")
    with open(cache_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "analysis": report_markdown
        }, f)
        
    return {"report": report_markdown}

@app.get("/api/research/status/{ticker}")
async def get_research_status(ticker: str):
    """
    Returns the current status of the report generation for the given ticker.
    """
    ticker = ticker.upper()
    return {"status": _task_status.get(ticker, "Not Started")}


@app.get("/api/news_analysis/{ticker}")
async def get_news_analysis_cache(ticker: str):
    """
    Checks if a valid, unexpired News Analysis exists.
    Returns the analysis if < 7 days old. Otherwise returns null.
    """
    ticker = ticker.upper()
    cache_file = os.path.join(NEWS_CACHE_DIR, f"{ticker}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
            
            timestamp = datetime.fromisoformat(cached_data["timestamp"])
            age = datetime.now() - timestamp
            
            if age < timedelta(days=7):
                return {"news_analysis": cached_data["analysis"], "cached": True, "age_days": age.days}
        except Exception as e:
            print(f"Error reading news cache for {ticker}: {e}")
            
    return {"news_analysis": None, "cached": False, "age_days": 0}


@app.post("/api/news_analysis/{ticker}")
async def generate_news_analysis(ticker: str):
    """
    Triggers the deep data collection and news crew to generate a new News Analysis.
    Saves the result to persistent cache.
    """
    ticker = ticker.upper()
    _news_task_status[ticker] = "Collecting Premium News"
    
    try:
        if ticker in _cache:
            data = _cache[ticker]
        else:
            collector = DataCollector()
            data = await asyncer.asyncify(collector.collect_core_data)(ticker)
            
        # Re-collect full data to ensure premium news is fetched
        collector = DataCollector()
        data = await asyncer.asyncify(collector.collect_full_data)(data)
        
        if not data.name or data.name == ticker:
            _news_task_status[ticker] = "Error: Company not found"
            raise HTTPException(status_code=404, detail="Company data not found")
            
    except Exception as e:
        _news_task_status[ticker] = f"Error: Data collection failed"
        raise HTTPException(status_code=500, detail=str(e))

    def progress_callback(status: str):
        _news_task_status[ticker] = status

    try:
        analysis_markdown = await asyncer.asyncify(run_news_analysis_crew)(data, progress_callback)
    except Exception as e:
        _news_task_status[ticker] = f"Error: Agent failed"
        raise HTTPException(status_code=500, detail=str(e))
        
    _news_task_status[ticker] = "Complete"
    
    # Save to persistent cache
    cache_file = os.path.join(NEWS_CACHE_DIR, f"{ticker}.json")
    with open(cache_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis_markdown
        }, f)
        
    return {"news_analysis": analysis_markdown, "cached": False, "age_days": 0}

@app.get("/api/news_analysis/status/{ticker}")
async def get_news_status(ticker: str):
    """
    Returns the current status of the premium news analysis generation.
    """
    ticker = ticker.upper()
    return {"status": _news_task_status.get(ticker, "Not Started")}


@app.get("/api/market/brief")
async def get_market_brief_cache():
    """
    Checks if a valid, unexpired Daily Market Brief exists.
    Returns the brief if < 24 hours old. Otherwise returns null.
    """
    cache_file = os.path.join(BRIEFS_CACHE_DIR, "daily.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
            
            timestamp = datetime.fromisoformat(cached_data["timestamp"])
            age = datetime.now() - timestamp
            
            if age < timedelta(hours=24):
                age_hours = int(age.total_seconds() / 3600)
                return {"brief": cached_data["analysis"], "cached": True, "age_hours": age_hours}
        except Exception as e:
            print(f"Error reading brief cache: {e}")
            
    return {"brief": None, "cached": False, "age_hours": 0}


@app.post("/api/market/brief")
async def generate_market_brief():
    """
    Triggers the data collection and AI agent to generate a new Daily Market & World Brief.
    Saves the result to persistent cache.
    """
    _brief_task_status["status"] = "Collecting Market Data"
    
    try:
        collector = DataCollector()
        brief_data = await asyncer.asyncify(collector.collect_market_brief_data)()
    except Exception as e:
        _brief_task_status["status"] = f"Error: Data collection failed"
        raise HTTPException(status_code=500, detail=str(e))

    def progress_callback(status: str):
        _brief_task_status["status"] = status

    try:
        brief_markdown = await asyncer.asyncify(run_market_brief_crew)(brief_data, progress_callback)
    except Exception as e:
        _brief_task_status["status"] = f"Error: Agent failed"
        raise HTTPException(status_code=500, detail=str(e))
        
    _brief_task_status["status"] = "Complete"
    
    # Save to persistent cache
    cache_file = os.path.join(BRIEFS_CACHE_DIR, "daily.json")
    with open(cache_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "analysis": brief_markdown
        }, f)
        
    return {"brief": brief_markdown, "cached": False, "age_hours": 0}


@app.get("/api/market/brief/status")
async def get_market_brief_status():
    """
    Returns the current generation status for the daily brief.
    """
    return _brief_task_status


@app.get("/api/market/overview")
async def get_market_overview():
    """
    Fetches real-time market data for the landing page dashboard.
    Includes major international indices and top breaking market headlines.
    """
    indices = {
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "FTSE 100": "^FTSE",
        "CAC 40": "^FCHI",
        "DAX": "^GDAXI",
        "Nikkei 225": "^N225"
    }
    
    # Run the blocking yfinance calls in an async thread
    def fetch_market_data():
        result = {"indices": [], "news": []}
        
        # 1. Fetch Indices
        tickers = yf.Tickers(" ".join(indices.values()))
        for name, symbol in indices.items():
            try:
                info = tickers.tickers[symbol].info
                if info:
                    current = info.get("regularMarketPrice", info.get("previousClose", 0))
                    prev = info.get("regularMarketPreviousClose", info.get("previousClose", 1))
                    
                    if current and prev:
                        pct_change = ((current - prev) / prev) * 100
                        result["indices"].append({
                            "name": name,
                            "price": round(current, 2),
                            "change_pct": round(pct_change, 2)
                        })
            except Exception as e:
                print(f"Failed to fetch index {symbol}: {e}")
                
        # 2. Fetch Professional Market News via Finnhub
        try:
            api_key = config.FINNHUB_API_KEY
            if api_key:
                url = f"https://finnhub.io/api/v1/news?category=general&token={api_key}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    news = response.json()
                    # Finnhub returns a list of dictionaries with 'headline', 'source', 'url', 'datetime'
                    for item in news[:5]:
                        if item.get("headline"):
                            result["news"].append({
                                "title": item.get("headline", ""),
                                "publisher": item.get("source", "Market News"),
                                "link": item.get("url", "#"),
                                "timestamp": item.get("datetime", 0)
                            })
        except Exception as e:
            print(f"Failed to fetch market news from Finnhub: {e}")
            
        return result

    data = await asyncer.asyncify(fetch_market_data)()
    return data

# ===========================================================================
# PORTFOLIO ENDPOINTS
# ===========================================================================

_portfolio_manager = PortfolioManager()


class AddHoldingRequest(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    date: str | None = None  # ISO date string, e.g. "2025-06-15". Defaults to today.


class SellRequest(BaseModel):
    shares: float
    price: float


class CashRequest(BaseModel):
    amount: float


@app.get("/api/portfolio/holdings")
async def get_portfolio_holdings():
    """Get all holdings with current prices and P&L."""
    try:
        enriched = await asyncer.asyncify(_portfolio_manager.get_enriched_holdings)()
        return {
            "holdings": [h.to_dict() for h in enriched],
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/holdings")
async def add_portfolio_holding(req: AddHoldingRequest):
    """Add a new holding (or increase existing position). Deducts from cash."""
    ticker = req.ticker.upper()

    # Validate that the ticker exists
    def _validate_ticker(t):
        try:
            info = yf.Ticker(t).info or {}
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            if not price:
                return None
            return info
        except Exception:
            return None

    try:
        info = await asyncer.asyncify(_validate_ticker)(ticker)
        if info is None:
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found: {e}")

    holding = _portfolio_manager.add_holding(ticker, req.shares, req.avg_cost, req.date)
    return {"message": f"Added {req.shares} shares of {ticker}", "holding": holding.to_dict()}


@app.post("/api/portfolio/holdings/{ticker}/sell")
async def sell_portfolio_holding(ticker: str, req: SellRequest):
    """Sell shares of a holding. Adds proceeds to cash. Calculates realized P&L."""
    ticker = ticker.upper()
    try:
        result = _portfolio_manager.sell_shares(ticker, req.shares, req.price)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/portfolio/holdings/{ticker}")
async def remove_portfolio_holding(ticker: str):
    """Remove a holding entirely from the portfolio."""
    ticker = ticker.upper()
    success = await asyncer.asyncify(_portfolio_manager.remove_holding)(ticker)
    if not success:
        raise HTTPException(status_code=404, detail=f"Holding '{ticker}' not found in portfolio.")
    return {"message": f"Removed {ticker} from portfolio"}


@app.get("/api/portfolio/cash")
async def get_cash_balance():
    """Get current cash balance."""
    return {"cash_balance": _portfolio_manager.get_cash()}


@app.post("/api/portfolio/cash")
async def set_cash_balance(req: CashRequest):
    """Set cash balance to a specific amount."""
    new_balance = _portfolio_manager.set_cash(req.amount)
    return {"cash_balance": new_balance, "message": f"Cash balance set to ${new_balance:,.2f}"}


@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get full portfolio summary with P&L and sector allocation."""
    try:
        summary = await asyncer.asyncify(_portfolio_manager.get_portfolio_summary)()
        return summary.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/performance")
async def get_portfolio_performance(period: str = "1y"):
    """Get portfolio performance metrics (Sharpe, Beta, returns, benchmark comparison)."""
    valid_periods = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd"]
    if period not in valid_periods:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {valid_periods}")

    try:
        enriched = await asyncer.asyncify(_portfolio_manager.get_enriched_holdings)()
        performance = await asyncer.asyncify(calculate_portfolio_performance)(enriched, period)
        return performance
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/transactions")
async def get_portfolio_transactions():
    """Get all transaction history (newest first)."""
    transactions = _portfolio_manager.get_transactions()
    return {"transactions": transactions}


@app.get("/api/portfolio/news")
async def get_portfolio_news():
    """Aggregate recent news headlines for all portfolio holdings."""
    holdings = _portfolio_manager.get_holdings()
    if not holdings:
        return {"holdings_news": []}

    def fetch_all_news():
        results = []
        tickers_str = " ".join(h.ticker for h in holdings)
        tickers_obj = yf.Tickers(tickers_str)

        for holding in holdings:
            try:
                ticker = tickers_obj.tickers[holding.ticker]
                news_raw = ticker.news or []
                news_items = []
                for item in news_raw[:5]:
                    # Handle both old flat format and new nested 'content' format
                    content = item.get("content", item)
                    
                    title = content.get("title", "")
                    
                    # Extract publisher
                    provider = content.get("provider")
                    if isinstance(provider, dict):
                        publisher = provider.get("displayName", "")
                    else:
                        publisher = content.get("publisher", "")
                        
                    # Extract link
                    url_obj = content.get("clickThroughUrl") or content.get("canonicalUrl")
                    if isinstance(url_obj, dict):
                        link = url_obj.get("url", "")
                    else:
                        link = content.get("link", "")
                        
                    news_items.append({
                        "title": title,
                        "publisher": publisher,
                        "link": link,
                    })
                results.append({
                    "ticker": holding.ticker,
                    "news": news_items,
                })
            except Exception as e:
                print(f"  ⚠ News fetch failed for {holding.ticker}: {e}")
                results.append({"ticker": holding.ticker, "news": []})

        return results

    holdings_news = await asyncer.asyncify(fetch_all_news)()
    return {"holdings_news": holdings_news}


_portfolio_news_task_status = {"status": "Idle"}

@app.get("/api/portfolio/news/analyze/status")
async def get_portfolio_news_status():
    """Returns the current generation status for the AI impact report."""
    return _portfolio_news_task_status

@app.post("/api/portfolio/news/analyze")
async def analyze_portfolio_news():
    """Run an AI Crew to deeply reflect on the recent news for all portfolio holdings."""
    _portfolio_news_task_status["status"] = "Fetching recent news..."
    
    # 1. Fetch current news
    news_res = await get_portfolio_news()
    holdings_news = news_res.get("holdings_news", [])
    
    if not holdings_news:
        _portfolio_news_task_status["status"] = "No news found."
        return {"report": "No holdings or no recent news available to analyze."}

    # 2. Format it into an aggressive text block for the agent
    _portfolio_news_task_status["status"] = "Structuring data for analysis..."
    news_text = "PORTFOLIO NEWS DIGEST:\n\n"
    for hn in holdings_news:
        news_text += f"TICKER: {hn['ticker']}\n"
        if not hn['news']:
            news_text += "  - No material news found.\n"
        else:
            for article in hn['news']:
                news_text += f"  - [{article['publisher']}] {article['title']} ({article['link']})\n"
        news_text += "\n"

    def progress_callback(status: str):
        _portfolio_news_task_status["status"] = status

    # 3. Fire off the backend PM agent
    def run_agent():
        return run_portfolio_news_crew(news_text, progress_callback)

    try:
        _portfolio_news_task_status["status"] = "Initializing AI analysis..."
        report = await asyncer.asyncify(run_agent)()
        _portfolio_news_task_status["status"] = "Complete"
        return {"report": report}
    except Exception as e:
        _portfolio_news_task_status["status"] = "Error formatting report"
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/market-status")
async def get_market_status():
    """
    Returns open/closed status for NYSE and Euronext, with countdown to next transition.
    Pure time-based calculation (no API calls).
    """
    import pytz
    now_utc = datetime.now(pytz.utc)

    def _get_status(tz_name: str, open_hour: int, open_min: int, close_hour: int, close_min: int):
        tz = pytz.timezone(tz_name)
        now_local = now_utc.astimezone(tz)
        weekday = now_local.weekday()  # 0=Mon, 6=Sun

        open_time = now_local.replace(hour=open_hour, minute=open_min, second=0, microsecond=0)
        close_time = now_local.replace(hour=close_hour, minute=close_min, second=0, microsecond=0)

        is_weekday = weekday < 5
        is_market_hours = is_weekday and open_time <= now_local < close_time

        if is_market_hours:
            # Countdown to close
            diff = close_time - now_local
            return {
                "is_open": True,
                "countdown_label": "Closes in",
                "countdown_seconds": int(diff.total_seconds()),
            }
        else:
            # Countdown to next open
            if is_weekday and now_local < open_time:
                # Today, before open
                next_open = open_time
            else:
                # After close or weekend — find next weekday
                days_ahead = 1
                if weekday == 4 and now_local >= close_time:  # Friday after close
                    days_ahead = 3
                elif weekday == 5:  # Saturday
                    days_ahead = 2
                elif weekday == 6:  # Sunday
                    days_ahead = 1

                next_open = (now_local + timedelta(days=days_ahead)).replace(
                    hour=open_hour, minute=open_min, second=0, microsecond=0
                )

            diff = next_open - now_local
            return {
                "is_open": False,
                "countdown_label": "Opens in",
                "countdown_seconds": int(diff.total_seconds()),
            }

    # NYSE: 9:30 AM – 4:00 PM ET
    nyse = _get_status("America/New_York", 9, 30, 16, 0)
    nyse["name"] = "NYSE"

    # Euronext: 9:00 AM – 5:30 PM CET
    euronext = _get_status("Europe/Paris", 9, 0, 17, 30)
    euronext["name"] = "Euronext"

    return {"markets": [nyse, euronext]}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
