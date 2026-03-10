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

from data.collector import DataCollector
from crew.research_crew import run_research_crew, run_news_analysis_crew

app = FastAPI(title="KerenEye API Dashboard")

# --- Setup Persistent Caching Directories ---
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
REPORTS_CACHE_DIR = os.path.join(CACHE_DIR, "reports")
NEWS_CACHE_DIR = os.path.join(CACHE_DIR, "news")

os.makedirs(REPORTS_CACHE_DIR, exist_ok=True)
os.makedirs(NEWS_CACHE_DIR, exist_ok=True)

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

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
