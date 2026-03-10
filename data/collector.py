"""
Data Collector — The Orchestrator's Data Engine

Fetches ALL raw data for a given ticker from three sources:
  1. yfinance — financials, prices, ratios, news, analyst data
  2. Finnhub  — peer/competitor tickers
  3. FRED     — macroeconomic indicators

Returns a structured CompanyData dataclass that gets distributed to agents.
"""

import warnings
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from config import (
    FINNHUB_API_KEY,
    FRED_API_KEY,
    FRED_SERIES,
    MAX_PEERS,
    PRICE_HISTORY_PERIOD,
    BENZINGA_API_KEY,
    MASSIVE_API_KEY,
)

import requests
from datetime import datetime, timedelta

warnings.filterwarnings("ignore", category=FutureWarning)


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------

@dataclass
class CompanyData:
    """Structured container for all data collected about a company."""

    # Identifiers
    ticker: str = ""
    name: str = ""
    sector: str = ""
    industry: str = ""
    description: str = ""
    market_cap: float = 0.0
    currency: str = "USD"
    website: str = ""
    employees: int = 0

    # Financial statements (DataFrames)
    income_statement: Optional[pd.DataFrame] = None
    balance_sheet: Optional[pd.DataFrame] = None
    cash_flow: Optional[pd.DataFrame] = None

    # Key ratios (dict)
    ratios: dict = field(default_factory=dict)

    # Price data
    price_history: Optional[pd.DataFrame] = None
    current_price: float = 0.0

    # Analyst data
    analyst_targets: dict = field(default_factory=dict)
    recommendations: Optional[pd.DataFrame] = None

    # News
    news: list = field(default_factory=list)

    # Peers
    peer_tickers: list = field(default_factory=list)
    peer_ratios: list = field(default_factory=list)  # list of dicts

    # Macro
    macro_data: dict = field(default_factory=dict)

    # Premium News
    recent_news: list = field(default_factory=list)

    # Metadata
    errors: list = field(default_factory=list)


@dataclass
class MarketBriefData:
    """Structured container for the daily market & world brief."""
    indices: list = field(default_factory=list)        # [{name, price, change_pct}]
    market_headlines: list = field(default_factory=list)  # Finnhub headlines
    macro_snapshot: dict = field(default_factory=dict)   # FRED latest values
    world_headlines: list = field(default_factory=list)   # GDELT headlines
    errors: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

class DataCollector:
    """
    Orchestrator data engine. Collects all data for a ticker in one pass.

    Usage:
        collector = DataCollector()
        data = collector.collect("AAPL")
    """
    def collect_core_data(self, ticker_symbol: str) -> CompanyData:
        """Collect ONLY the core data needed for initial UI rendering (charts, metrics)."""
        print(f"\n{'='*60}")
        print(f"  Collecting CORE data for: {ticker_symbol.upper()}")
        print(f"{'='*60}\n")

        data = CompanyData(ticker=ticker_symbol.upper())

        # Step 1: yfinance — primary data source (prices, financials, ratios)
        self._fetch_yfinance_data(data)

        print(f"\n{'='*60}")
        print(f"  Core data collection complete for {data.name or data.ticker}")
        if data.errors:
            print(f"  ⚠ {len(data.errors)} non-critical error(s) occurred")
        print(f"{'='*60}\n")

        return data

    def collect_full_data(self, data: CompanyData) -> CompanyData:
        """Collect the remaining heavy data needed for AI agents."""
        print(f"\n{'='*60}")
        print(f"  Collecting FULL data for: {data.ticker}")
        print(f"{'='*60}\n")

        # Skip Step 1 since it was already done in collect_core_data

        # Step 2: Finnhub — peer discovery
        self._fetch_peers(data)

        # Step 3: yfinance — peer ratios (using peers from Step 2)
        self._fetch_peer_ratios(data)

        # Step 4: FRED — macro context
        self._fetch_macro_data(data)
        
        # Step 5: Premium News (Benzinga / Polygon)
        self._fetch_premium_news(data)

        print(f"\n{'='*60}")
        print(f"  Data collection complete for {data.name or data.ticker}")
        if data.errors:
            print(f"  ⚠ {len(data.errors)} non-critical error(s) occurred")
        print(f"{'='*60}\n")

        return data

    def collect_market_brief_data(self) -> MarketBriefData:
        """Collect broad market data for the Daily Market & World Brief (no ticker needed)."""
        import time

        print(f"\n{'='*60}")
        print(f"  Collecting MARKET BRIEF data")
        print(f"{'='*60}\n")

        brief = MarketBriefData()

        # 1. yfinance — Major indices
        print("📡 Fetching index performance...")
        index_map = {
            "S&P 500": "^GSPC",
            "Nasdaq": "^IXIC",
            "FTSE 100": "^FTSE",
            "CAC 40": "^FCHI",
            "DAX": "^GDAXI",
            "Nikkei 225": "^N225"
        }
        try:
            tickers = yf.Tickers(" ".join(index_map.values()))
            for name, symbol in index_map.items():
                try:
                    info = tickers.tickers[symbol].info
                    if info:
                        current = info.get("regularMarketPrice", info.get("previousClose", 0))
                        prev = info.get("regularMarketPreviousClose", info.get("previousClose", 1))
                        if current and prev:
                            pct_change = ((current - prev) / prev) * 100
                            brief.indices.append({
                                "name": name,
                                "price": round(current, 2),
                                "change_pct": round(pct_change, 2)
                            })
                            print(f"  ✅ {name}: {current:.2f} ({pct_change:+.2f}%)")
                except Exception as e:
                    brief.errors.append(f"Index {symbol} failed: {e}")
        except Exception as e:
            brief.errors.append(f"yfinance indices failed: {e}")
            print(f"  ⚠ Failed to fetch indices: {e}")

        # 2. Finnhub — Top 20 market headlines
        print("📡 Fetching Finnhub market headlines...")
        if FINNHUB_API_KEY and FINNHUB_API_KEY != "your_finnhub_api_key_here":
            try:
                url = f"https://finnhub.io/api/v1/news?category=general&token={FINNHUB_API_KEY}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    news = response.json()
                    for item in news[:20]:
                        if item.get("headline"):
                            brief.market_headlines.append({
                                "headline": item.get("headline", ""),
                                "source": item.get("source", "Unknown"),
                                "summary": item.get("summary", "")[:300],
                                "url": item.get("url", ""),
                            })
                    print(f"  ✅ {len(brief.market_headlines)} market headlines collected")
                else:
                    print(f"  ⚠ Finnhub returned status {response.status_code}")
            except Exception as e:
                brief.errors.append(f"Finnhub news failed: {e}")
                print(f"  ⚠ Finnhub failed: {e}")
        else:
            print("  ⚠ Finnhub: Skipped (no API key)")

        # 3. FRED — Macro snapshot
        print("📡 Fetching FRED macro snapshot...")
        if FRED_API_KEY and FRED_API_KEY != "your_fred_api_key_here":
            try:
                from fredapi import Fred
                fred = Fred(api_key=FRED_API_KEY)
                for label, series_id in FRED_SERIES.items():
                    try:
                        series = fred.get_series(series_id)
                        latest = series.dropna().iloc[-1]
                        brief.macro_snapshot[label] = {
                            "value": float(latest),
                            "date": str(series.dropna().index[-1].date()),
                        }
                        print(f"  ✅ {label}: {latest:.2f}")
                    except Exception as e:
                        brief.errors.append(f"FRED {label} failed: {e}")
            except ImportError:
                brief.errors.append("fredapi not installed")
                print("  ⚠ fredapi not installed")
        else:
            print("  ⚠ FRED: Skipped (no API key)")

        # 4. GDELT — World/geopolitical headlines (free, no API key)
        print("📡 Fetching GDELT world headlines...")
        try:
            # GDELT DOC API — search for broad geopolitical/economic themes
            gdelt_url = (
                "https://api.gdeltproject.org/api/v2/doc/doc"
                "?query=economy OR markets OR geopolitical OR trade OR war OR election"
                "&mode=ArtList"
                "&maxrecords=15"
                "&timespan=1d"
                "&format=json"
                "&sort=HybridRel"
            )
            response = requests.get(gdelt_url, timeout=10)
            if response.status_code == 200:
                data_json = response.json()
                articles = data_json.get("articles", [])
                for article in articles:
                    brief.world_headlines.append({
                        "title": article.get("title", ""),
                        "source": article.get("domain", "Unknown"),
                        "url": article.get("url", ""),
                        "seendate": article.get("seendate", ""),
                    })
                print(f"  ✅ {len(brief.world_headlines)} GDELT world headlines collected")
            else:
                print(f"  ⚠ GDELT returned status {response.status_code}")
        except Exception as e:
            brief.errors.append(f"GDELT failed: {e}")
            print(f"  ⚠ GDELT failed: {e}")

        print(f"\n{'='*60}")
        print(f"  Market brief data collection complete")
        if brief.errors:
            print(f"  ⚠ {len(brief.errors)} non-critical error(s) occurred")
        print(f"{'='*60}\n")

        return brief

    # --- Step 1: yfinance ---------------------------------------------------

    def _fetch_yfinance_data(self, data: CompanyData) -> None:
        """Fetch all data from yfinance for the ticker."""
        print("📡 Fetching data from yfinance...")

        try:
            ticker = yf.Ticker(data.ticker)
            info = ticker.info or {}
        except Exception as e:
            data.errors.append(f"yfinance info failed: {e}")
            print(f"  ❌ Failed to fetch ticker info: {e}")
            return

        # --- Company profile ---
        data.name = info.get("longName", info.get("shortName", data.ticker))
        data.sector = info.get("sector", "Unknown")
        data.industry = info.get("industry", "Unknown")
        data.description = info.get("longBusinessSummary", "")
        data.market_cap = info.get("marketCap", 0)
        data.currency = info.get("currency", "USD")
        data.website = info.get("website", "")
        data.employees = info.get("fullTimeEmployees", 0)
        data.current_price = info.get(
            "currentPrice", info.get("regularMarketPrice", 0)
        )
        print(f"  ✅ Company: {data.name} | {data.sector} | {data.industry}")

        # --- Key ratios ---
        ratio_keys = [
            "trailingPE", "forwardPE", "priceToBook", "enterpriseToEbitda",
            "enterpriseToRevenue", "profitMargins", "operatingMargins",
            "grossMargins", "returnOnEquity", "returnOnAssets",
            "debtToEquity", "currentRatio", "quickRatio",
            "beta", "dividendYield", "payoutRatio",
            "revenueGrowth", "earningsGrowth", "freeCashflow",
            "enterpriseValue", "totalRevenue", "ebitda",
        ]
        data.ratios = {k: info.get(k) for k in ratio_keys if info.get(k) is not None}
        print(f"  ✅ Ratios: {len(data.ratios)} metrics collected")

        # --- Financial statements ---
        try:
            data.income_statement = ticker.income_stmt
            if data.income_statement is not None and not data.income_statement.empty:
                print(
                    f"  ✅ Income statement: "
                    f"{data.income_statement.shape[1]} periods"
                )
            else:
                data.errors.append("Income statement is empty")
                print("  ⚠ Income statement is empty")
        except Exception as e:
            data.errors.append(f"Income statement failed: {e}")
            print(f"  ⚠ Income statement failed: {e}")

        try:
            data.balance_sheet = ticker.balance_sheet
            if data.balance_sheet is not None and not data.balance_sheet.empty:
                print(
                    f"  ✅ Balance sheet: "
                    f"{data.balance_sheet.shape[1]} periods"
                )
            else:
                data.errors.append("Balance sheet is empty")
        except Exception as e:
            data.errors.append(f"Balance sheet failed: {e}")
            print(f"  ⚠ Balance sheet failed: {e}")

        try:
            data.cash_flow = ticker.cashflow
            if data.cash_flow is not None and not data.cash_flow.empty:
                print(f"  ✅ Cash flow: {data.cash_flow.shape[1]} periods")
            else:
                data.errors.append("Cash flow is empty")
        except Exception as e:
            data.errors.append(f"Cash flow failed: {e}")
            print(f"  ⚠ Cash flow failed: {e}")

        # --- Price history ---
        try:
            data.price_history = ticker.history(period=PRICE_HISTORY_PERIOD)
            if data.price_history is not None and not data.price_history.empty:
                print(
                    f"  ✅ Price history: "
                    f"{len(data.price_history)} trading days"
                )
            else:
                data.errors.append("Price history is empty")
        except Exception as e:
            data.errors.append(f"Price history failed: {e}")
            print(f"  ⚠ Price history failed: {e}")

        # --- Analyst data ---
        try:
            targets = ticker.analyst_price_targets
            if targets is not None:
                if isinstance(targets, pd.DataFrame):
                    data.analyst_targets = targets.to_dict()
                else:
                    data.analyst_targets = (
                        targets if isinstance(targets, dict) else {}
                    )
                print(f"  ✅ Analyst price targets loaded")
            else:
                data.analyst_targets = {}
        except Exception as e:
            data.errors.append(f"Analyst targets failed: {e}")
            data.analyst_targets = {}

        try:
            data.recommendations = ticker.recommendations
            if data.recommendations is not None and not data.recommendations.empty:
                print(
                    f"  ✅ Recommendations: "
                    f"{len(data.recommendations)} entries"
                )
        except Exception as e:
            data.errors.append(f"Recommendations failed: {e}")

        # --- News ---
        try:
            news_raw = ticker.news or []
            data.news = []
            for item in news_raw[:10]:  # Limit to 10 articles
                data.news.append({
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher", ""),
                    "link": item.get("link", ""),
                    "published": item.get("providerPublishTime", ""),
                })
            print(f"  ✅ News: {len(data.news)} articles")
        except Exception as e:
            data.errors.append(f"News failed: {e}")
            print(f"  ⚠ News failed: {e}")

    # --- Step 2: Finnhub peers ----------------------------------------------

    def _fetch_peers(self, data: CompanyData) -> None:
        """Fetch peer/competitor tickers from Finnhub."""
        if not FINNHUB_API_KEY or FINNHUB_API_KEY == "your_finnhub_api_key_here":
            print("📡 Finnhub: Skipped (no API key set)")
            # Fallback: use yfinance sector to suggest known peers
            data.peer_tickers = []
            data.errors.append("Finnhub API key not configured — no peers fetched")
            return

        print("📡 Fetching peers from Finnhub...")
        try:
            import finnhub

            client = finnhub.Client(api_key=FINNHUB_API_KEY)
            peers = client.company_peers(data.ticker)

            # Remove the company itself from peers, limit count
            peers = [p for p in peers if p != data.ticker][:MAX_PEERS]
            data.peer_tickers = peers
            print(f"  ✅ Peers: {peers}")
        except Exception as e:
            data.errors.append(f"Finnhub peers failed: {e}")
            print(f"  ⚠ Finnhub peers failed: {e}")
            data.peer_tickers = []

    # --- Step 3: Peer ratios via yfinance ------------------------------------

    def _fetch_peer_ratios(self, data: CompanyData) -> None:
        """Fetch key ratios for each peer using yfinance."""
        if not data.peer_tickers:
            print("📡 Peer ratios: Skipped (no peers available)")
            return

        print(f"📡 Fetching peer ratios for {len(data.peer_tickers)} peers...")
        for peer_symbol in data.peer_tickers:
            try:
                peer_ticker = yf.Ticker(peer_symbol)
                peer_info = peer_ticker.info or {}
                peer_data = {
                    "ticker": peer_symbol,
                    "name": peer_info.get(
                        "longName", peer_info.get("shortName", peer_symbol)
                    ),
                    "marketCap": peer_info.get("marketCap", 0),
                    "trailingPE": peer_info.get("trailingPE"),
                    "forwardPE": peer_info.get("forwardPE"),
                    "priceToBook": peer_info.get("priceToBook"),
                    "enterpriseToEbitda": peer_info.get("enterpriseToEbitda"),
                    "profitMargins": peer_info.get("profitMargins"),
                    "returnOnEquity": peer_info.get("returnOnEquity"),
                    "revenueGrowth": peer_info.get("revenueGrowth"),
                    "debtToEquity": peer_info.get("debtToEquity"),
                }
                data.peer_ratios.append(peer_data)
                print(f"  ✅ {peer_symbol}: {peer_data['name']}")
            except Exception as e:
                data.errors.append(f"Peer {peer_symbol} failed: {e}")
                print(f"  ⚠ {peer_symbol} failed: {e}")

    # --- Step 4: FRED macro data --------------------------------------------

    def _fetch_macro_data(self, data: CompanyData) -> None:
        """Fetch macroeconomic indicators from FRED."""
        if not FRED_API_KEY or FRED_API_KEY == "your_fred_api_key_here":
            print("📡 FRED: Skipped (no API key set)")
            data.errors.append("FRED API key not configured — no macro data")
            return

        print("📡 Fetching macro data from FRED...")
        try:
            from fredapi import Fred

            fred = Fred(api_key=FRED_API_KEY)

            for label, series_id in FRED_SERIES.items():
                try:
                    series = fred.get_series(series_id)
                    # Get the most recent value
                    latest = series.dropna().iloc[-1]
                    data.macro_data[label] = {
                        "value": float(latest),
                        "date": str(series.dropna().index[-1].date()),
                        "series_id": series_id,
                    }
                    print(f"  ✅ {label}: {latest:.2f}")
                except Exception as e:
                    data.errors.append(f"FRED {label} failed: {e}")
                    print(f"  ⚠ {label} failed: {e}")
        except ImportError:
            data.errors.append("fredapi not installed")
            print("  ⚠ fredapi not installed — skipping macro data")

    # --- Step 5: Premium News -----------------------------------------------

    def _fetch_premium_news(self, data: CompanyData) -> None:
        """Fetch recent news from Benzinga and Polygon, avoiding Yahoo Finance."""
        print("📡 Fetching premium news (Benzinga/Polygon)...")
        
        # Determine the date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        news_items = []

        # 1. Fetch from Benzinga
        if BENZINGA_API_KEY and BENZINGA_API_KEY != "your_benzinga_api_key_here":
            try:
                url = f"https://api.benzinga.com/api/v2/news?token={BENZINGA_API_KEY}&tickers={data.ticker}&dateFrom={start_str}&dateTo={end_str}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    articles = response.json()
                    for article in articles:
                        # Append unique articles
                        if not any(a.get("title") == article.get("title") for a in news_items):
                            news_items.append({
                                "title": article.get("title", ""),
                                "publisher": "Benzinga",
                                "link": article.get("url", ""),
                                "published": article.get("created", ""),
                                "teaser": article.get("teaser", "")
                            })
                    print(f"  ✅ Benzinga: {len(articles)} articles found.")
                else:
                    data.errors.append(f"Benzinga API failed with status {response.status_code}")
                    print(f"  ⚠ Benzinga failed: {response.status_code}")
            except Exception as e:
                data.errors.append(f"Benzinga news fetch failed: {e}")
                print(f"  ⚠ Benzinga failed: {e}")
        else:
            print("  ⚠ Skipped Benzinga (No API Key)")

        # 2. Fetch from Polygon (Massive)
        if MASSIVE_API_KEY and MASSIVE_API_KEY != "your_massive_api_key_here":
            try:
                # Polygon rate limit is 5 / min. Wrap in try/except for 429
                url = f"https://api.polygon.io/v2/reference/news?ticker={data.ticker}&published_utc.gte={start_str}&limit=20&apiKey={MASSIVE_API_KEY}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    articles = response.json().get("results", [])
                    added_polygon_count = 0
                    for article in articles:
                        publisher_name = article.get("publisher", {}).get("name", "")
                        # Explicitly filter out Yahoo Finance if it slips in via aggregators
                        if "yahoo" in publisher_name.lower():
                            continue
                            
                        # Avoid exact title duplicates from Benzinga
                        if not any(a.get("title") == article.get("title") for a in news_items):
                            news_items.append({
                                "title": article.get("title", ""),
                                "publisher": publisher_name,
                                "link": article.get("article_url", ""),
                                "published": article.get("published_utc", ""),
                                "teaser": article.get("description", "")
                            })
                            added_polygon_count += 1
                    print(f"  ✅ Polygon: {added_polygon_count} articles added.")
                elif response.status_code == 429:
                    print("  ⚠ Polygon: Rate limited (429). Falling back to Benzinga data only.")
                else:
                    data.errors.append(f"Polygon API failed with status {response.status_code}")
                    print(f"  ⚠ Polygon failed: {response.status_code}")
            except Exception as e:
                data.errors.append(f"Polygon news fetch failed: {e}")
                print(f"  ⚠ Polygon failed: {e}")
        else:
            print("  ⚠ Skipped Polygon (No API Key)")
            
        # Sort combined news generically by published date descending (newest first)
        news_items.sort(key=lambda x: x.get("published", ""), reverse=True)
        data.recent_news = news_items

# ---------------------------------------------------------------------------
# Formatting helpers (used by agents to read data)
# ---------------------------------------------------------------------------

def _format_df_as_md_table(df: pd.DataFrame, key_rows: list, title: str) -> str:
    """Helper to format a yfinance DataFrame as a Markdown table."""
    if df is None or df.empty:
        return f"{title} not available."

    lines = [f"### {title}"]

    # Extract years for the header (yfinance columns are usually timestamps)
    years = [str(col.year) if hasattr(col, "year") else str(col)[:4] for col in df.columns]
    
    # Table Header
    header = "| Metric | " + " | ".join(years) + " |"
    divider = "|----------|" + "|".join(["---" for _ in years]) + "|"
    lines.append(header)
    lines.append(divider)

    for row in key_rows:
        actual_row = None
        if row in df.index:
            actual_row = row
        else:
            # Case-insensitive substring match fallback
            for idx in df.index:
                if row.lower() in str(idx).lower():
                    actual_row = idx
                    break
            # Fallback for Total Revenue
            if not actual_row and row == "Total Revenue":
                for idx in df.index:
                    if "revenue" in str(idx).lower():
                        actual_row = idx
                        break

        if actual_row is not None:
            vals = df.loc[actual_row]
            if isinstance(vals, pd.DataFrame):
                vals = vals.iloc[0]
                
            row_data = [row.replace("Total ", "")] # Simplify row names slightly
            for val in vals:
                if pd.isna(val):
                    row_data.append("N/A")
                elif abs(val) >= 1_000_000_000:
                    row_data.append(f"${val/1_000_000_000:.2f}B")
                elif abs(val) >= 1_000_000:
                    row_data.append(f"${val/1_000_000:.2f}M")
                else:
                    if float(val).is_integer():
                         row_data.append(f"${val:,.0f}")
                    else:
                         row_data.append(f"${val:,.2f}")
            lines.append("| " + " | ".join(row_data) + " |")

    return "\n".join(lines)


def format_financial_statements(data: CompanyData) -> str:
    """Format financial statements as readable markdown tables for LLM agents."""
    sections = []

    inc_rows = ["Total Revenue", "Cost Of Revenue", "Gross Profit", 
                "Operating Expense", "Operating Income", "Net Income", "EBITDA", "Basic EPS"]
    sections.append(_format_df_as_md_table(data.income_statement, inc_rows, "INCOME STATEMENT"))

    bal_rows = ["Total Assets", "Current Assets", "Cash And Cash Equivalents", 
                "Total Liabilities Net Minority Interest", "Current Liabilities", "Total Debt", 
                "Total Equity Gross Minority Interest"]
    sections.append(_format_df_as_md_table(data.balance_sheet, bal_rows, "BALANCE SHEET"))

    cf_rows = ["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow", 
               "Investing Cash Flow", "Financing Cash Flow"]
    sections.append(_format_df_as_md_table(data.cash_flow, cf_rows, "CASH FLOW STATEMENT"))

    return "\n\n".join(sections)


def format_ratios(data: CompanyData) -> str:
    """Format key ratios as readable text for LLM agents."""
    if not data.ratios:
        return "Key ratios not available."

    lines = ["=== KEY RATIOS ==="]
    labels = {
        "trailingPE": "Trailing P/E",
        "forwardPE": "Forward P/E",
        "priceToBook": "Price/Book",
        "enterpriseToEbitda": "EV/EBITDA",
        "enterpriseToRevenue": "EV/Revenue",
        "profitMargins": "Net Margin",
        "operatingMargins": "Operating Margin",
        "grossMargins": "Gross Margin",
        "returnOnEquity": "ROE",
        "returnOnAssets": "ROA",
        "debtToEquity": "Debt/Equity",
        "currentRatio": "Current Ratio",
        "quickRatio": "Quick Ratio",
        "beta": "Beta",
        "dividendYield": "Dividend Yield",
        "revenueGrowth": "Revenue Growth",
        "earningsGrowth": "Earnings Growth",
    }
    for key, label in labels.items():
        val = data.ratios.get(key)
        if val is not None:
            # Format percentages
            if key in (
                "profitMargins", "operatingMargins", "grossMargins",
                "returnOnEquity", "returnOnAssets", "dividendYield",
                "revenueGrowth", "earningsGrowth",
            ):
                lines.append(f"  {label}: {val:.1%}")
            else:
                lines.append(f"  {label}: {val:.2f}")

    return "\n".join(lines)


def format_peer_comparison(data: CompanyData) -> str:
    """Format peer comparison as readable text for LLM agents."""
    if not data.peer_ratios:
        return "Peer comparison data not available."

    lines = ["=== PEER COMPARISON ==="]
    lines.append(
        f"{'Company':<25} {'Mkt Cap':>12} {'P/E':>8} "
        f"{'EV/EBITDA':>10} {'Margin':>8} {'ROE':>8}"
    )
    lines.append("-" * 75)

    def _fmt_price(val): return "N/A" if val is None else f"{val:.1f}"
    def _fmt_pct(val): return "N/A" if val is None else f"{val:.1%}"
    def _fmt_mc(val): return "N/A" if not val else f"${val:,.0f}"

    # Add the target company first
    mc = data.market_cap
    pe = data.ratios.get("trailingPE")
    ev = data.ratios.get("enterpriseToEbitda")
    pm = data.ratios.get("profitMargins")
    roe = data.ratios.get("returnOnEquity")
    lines.append(
        f"{data.name[:24]:<25} "
        f"{_fmt_mc(mc):>12} "
        f"{_fmt_price(pe):>8} "
        f"{_fmt_price(ev):>10} "
        f"{_fmt_pct(pm):>8} "
        f"{_fmt_pct(roe):>8}"
    )

    for peer in data.peer_ratios:
        mc = peer.get("marketCap")
        pe = peer.get("trailingPE")
        ev = peer.get("enterpriseToEbitda")
        pm = peer.get("profitMargins")
        roe = peer.get("returnOnEquity")
        name = (peer.get("name") or peer.get("ticker", "Unknown"))[:24]
        lines.append(
            f"{name:<25} "
            f"{_fmt_mc(mc):>12} "
            f"{_fmt_price(pe):>8} "
            f"{_fmt_price(ev):>10} "
            f"{_fmt_pct(pm):>8} "
            f"{_fmt_pct(roe):>8}"
        )

    return "\n".join(lines)


def format_news(data: CompanyData) -> str:
    """Format news articles (Standard yfinance news) as readable text for LLM agents."""
    if not data.news:
        return "No recent news available."

    lines = ["=== RECENT NEWS ==="]
    for i, article in enumerate(data.news, 1):
        lines.append(f"  {i}. {article['title']}")
        lines.append(f"     Source: {article['publisher']}")
    return "\n".join(lines)


def format_premium_news(data: CompanyData) -> str:
    """Format premium news articles (Benzinga/Polygon) specifically for the News Analyst."""
    if not data.recent_news:
        return "No premium news available for the last 7 days."

    lines = ["=== RECENT PREMIUM NEWS (LAST 7 DAYS) ==="]
    for i, article in enumerate(data.recent_news, 1):
        lines.append(f"  [{i}] {article['published']} | SOURCE: {article['publisher']}")
        lines.append(f"      HEADLINE: {article['title']}")
        if article.get('teaser'):
            # Truncate teaser to avoid massive context
            teaser = article['teaser'][:300] + ("..." if len(article['teaser']) > 300 else "")
            lines.append(f"      SUMMARY: {teaser}")
        lines.append("")
    return "\n".join(lines)

def format_macro(data: CompanyData) -> str:
    """Format macro data as readable text for LLM agents."""
    if not data.macro_data:
        return "Macroeconomic data not available."

    lines = ["=== MACROECONOMIC CONTEXT ==="]
    labels = {
        "GDP": "US GDP (billions)",
        "FEDFUNDS": "Fed Funds Rate (%)",
        "CPI": "CPI Index",
        "UNEMPLOYMENT": "Unemployment Rate (%)",
        "YIELD_SPREAD": "10Y-2Y Spread (%)",
    }
    for key, label in labels.items():
        entry = data.macro_data.get(key)
        if entry:
            lines.append(f"  {label}: {entry['value']:.2f} (as of {entry['date']})")

    return "\n".join(lines)


def format_company_profile(data: CompanyData) -> str:
    """Format company profile as readable text for LLM agents."""
    lines = [
        "=== COMPANY PROFILE ===",
        f"  Name: {data.name}",
        f"  Ticker: {data.ticker}",
        f"  Sector: {data.sector}",
        f"  Industry: {data.industry}",
        f"  Market Cap: ${data.market_cap:,.0f}" if data.market_cap else "",
        f"  Employees: {data.employees:,}" if data.employees else "",
        f"  Website: {data.website}" if data.website else "",
        f"  Current Price: ${data.current_price:.2f}" if data.current_price else "",
        "",
        f"  Description: {data.description[:500]}..."
        if len(data.description) > 500
        else f"  Description: {data.description}",
    ]
    return "\n".join(line for line in lines if line)


def format_market_brief_context(brief: MarketBriefData) -> str:
    """Format the MarketBriefData into a readable text block for the LLM agent."""
    lines = []

    # Indices
    lines.append("=== INDEX PERFORMANCE ===")
    for idx in brief.indices:
        direction = "▲" if idx["change_pct"] >= 0 else "▼"
        lines.append(f"  {idx['name']}: {idx['price']:,.2f} ({direction} {abs(idx['change_pct']):.2f}%)")
    lines.append("")

    # Macro
    if brief.macro_snapshot:
        lines.append("=== MACROECONOMIC SNAPSHOT ===")
        labels = {
            "GDP": "US GDP (billions)",
            "FEDFUNDS": "Fed Funds Rate (%)",
            "CPI": "CPI Index",
            "UNEMPLOYMENT": "Unemployment Rate (%)",
            "YIELD_SPREAD": "10Y-2Y Spread (%)",
        }
        for key, label in labels.items():
            entry = brief.macro_snapshot.get(key)
            if entry:
                lines.append(f"  {label}: {entry['value']:.2f} (as of {entry['date']})")
        lines.append("")

    # Market Headlines
    if brief.market_headlines:
        lines.append("=== MARKET HEADLINES (Finnhub) ===")
        for i, h in enumerate(brief.market_headlines, 1):
            lines.append(f"  [{i}] {h['source']}: {h['headline']}")
            if h.get('summary'):
                lines.append(f"      {h['summary'][:200]}")
        lines.append("")

    # World Headlines
    if brief.world_headlines:
        lines.append("=== WORLD / GEOPOLITICAL HEADLINES (GDELT) ===")
        for i, h in enumerate(brief.world_headlines, 1):
            lines.append(f"  [{i}] {h['source']}: {h['title']}")
        lines.append("")

    return "\n".join(lines)
