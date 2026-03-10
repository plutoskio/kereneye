"""
Configuration management for the equity research multi-agent system.
Loads API keys from environment variables / .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# --- API Keys ---
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
BENZINGA_API_KEY = os.getenv("BENZINGA_API_KEY", "")
MASSIVE_API_KEY = os.getenv("MASSIVE_API_KEY", "")

# --- Data Collection Settings ---
PRICE_HISTORY_PERIOD = "5y"        # How far back to fetch price data
MAX_PEERS = 5                       # Max number of peer companies to compare
FRED_SERIES = {
    "GDP": "GDP",                   # US GDP
    "FEDFUNDS": "FEDFUNDS",         # Federal Funds Rate
    "CPI": "CPIAUCSL",             # Consumer Price Index
    "UNEMPLOYMENT": "UNRATE",       # Unemployment Rate
    "YIELD_SPREAD": "T10Y2Y",      # 10Y-2Y Treasury Spread
}

# --- Output Settings ---
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "reports")
