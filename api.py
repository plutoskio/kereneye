"""
FastAPI Backend for KerenEye Web Dashboard.
Exposes the DataCollector and ResearchCrew logic via simple REST endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncer
import yfinance as yf
import requests
import config

from data.collector import DataCollector
from crew.research_crew import run_research_crew

app = FastAPI(title="KerenEye API Dashboard")

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

# Keep a simple in-memory cache to avoid re-fetching identical data
# in the time between the frontend hitting /company and then /research
_cache = {}

@app.get("/api/company/{ticker}", response_model=CompanyResponse)
async def get_company_data(ticker: str):
    """
    Instantly fetch the raw company data and price history to populate the frontend dashboard.
    """
    ticker = ticker.upper()
    collector = DataCollector()
    
    # Run the synchronous collector logic in an async worker thread
    data = await asyncer.asyncify(collector.collect)(ticker)
    
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
async def get_research_report(ticker: str):
    """
    Triggers the CrewAI agent orchestration to generate the equity research report.
    Returns the final markdown. Always re-runs the agents to ensure fresh analysis if 
    the user queries it again.
    """
    ticker = ticker.upper()
    
    # Check if we already have the raw data cached from the /company endpoint
    # to save time calling YFinance again.
    if ticker in _cache:
        data = _cache[ticker]
    else:
        collector = DataCollector()
        data = await asyncer.asyncify(collector.collect)(ticker)
        
        if not data.name or data.name == ticker:
            raise HTTPException(status_code=404, detail="Company data not found")

    # Run the heavy CrewAI logic in a background async worker
    # We never cache the final report string, so querying twice gives a fresh generation.
    report_markdown = await asyncer.asyncify(run_research_crew)(data)
    
    return {"report": report_markdown}

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
