"""Shared market-data access with small in-memory TTL caches."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta

import pandas as pd
import requests
import yfinance as yf

from config import BENZINGA_API_KEY, MASSIVE_API_KEY


INFO_TTL = timedelta(seconds=60)
NEWS_TTL = timedelta(minutes=5)
HISTORY_TTL = timedelta(minutes=5)
DOWNLOAD_TTL = timedelta(minutes=5)
PREMIUM_NEWS_TTL = timedelta(minutes=15)

_info_cache: dict[str, tuple[datetime, dict]] = {}
_news_cache: dict[tuple[str, int | None], tuple[datetime, list]] = {}
_premium_news_cache: dict[tuple[str, int | None, int], tuple[datetime, list]] = {}
_history_cache: dict[tuple[str, str], tuple[datetime, pd.DataFrame]] = {}
_download_cache: dict[tuple[tuple[str, ...], tuple[tuple[str, str], ...]], tuple[datetime, pd.DataFrame | pd.Series]] = {}


def _now() -> datetime:
    return datetime.now()


def _is_fresh(fetched_at: datetime, ttl: timedelta) -> bool:
    return (_now() - fetched_at) < ttl


def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().strip()


def _normalize_symbols(symbols) -> list[str]:
    if isinstance(symbols, str):
        return [_normalize_symbol(symbols)]

    normalized = []
    for symbol in symbols:
        clean = _normalize_symbol(symbol)
        if clean and clean not in normalized:
            normalized.append(clean)
    return normalized


def _clone_news(news_items: list) -> list:
    return copy.deepcopy(news_items)


def _clone_info(info: dict) -> dict:
    return dict(info)


def _dedupe_news_items(news_items: list[dict]) -> list[dict]:
    seen_titles: set[str] = set()
    unique_items: list[dict] = []

    for item in news_items:
        title = (item.get("title") or "").strip()
        if not title:
            continue

        title_key = title.casefold()
        if title_key in seen_titles:
            continue

        seen_titles.add(title_key)
        unique_items.append(item)

    return unique_items


def _sort_news_by_published(news_items: list[dict]) -> list[dict]:
    return sorted(news_items, key=lambda item: item.get("published", ""), reverse=True)


def get_ticker(symbol: str):
    """Return a yfinance ticker object for advanced one-off properties."""
    return yf.Ticker(_normalize_symbol(symbol))


def get_ticker_info(symbol: str) -> dict:
    """Return cached ticker info when available."""
    symbol = _normalize_symbol(symbol)
    cached = _info_cache.get(symbol)
    if cached and _is_fresh(cached[0], INFO_TTL):
        return _clone_info(cached[1])

    try:
        info = get_ticker(symbol).info or {}
    except Exception:
        info = {}

    _info_cache[symbol] = (_now(), info)
    return _clone_info(info)


def get_batch_ticker_info(symbols) -> dict[str, dict]:
    """Return cached batch ticker info, fetching only cache misses."""
    normalized = _normalize_symbols(symbols)
    if not normalized:
        return {}

    results: dict[str, dict] = {}
    missing: list[str] = []

    for symbol in normalized:
        cached = _info_cache.get(symbol)
        if cached and _is_fresh(cached[0], INFO_TTL):
            results[symbol] = _clone_info(cached[1])
        else:
            missing.append(symbol)

    if not missing:
        return results

    try:
        tickers = yf.Tickers(" ".join(missing))
        fetched_at = _now()
        for symbol in missing:
            try:
                info = tickers.tickers[symbol].info or {}
            except Exception:
                info = {}
            _info_cache[symbol] = (fetched_at, info)
            results[symbol] = _clone_info(info)
    except Exception:
        for symbol in missing:
            results[symbol] = get_ticker_info(symbol)

    return results


def get_ticker_news(symbol: str, limit: int | None = None) -> list:
    """Return cached raw news items for a ticker."""
    symbol = _normalize_symbol(symbol)
    cache_key = (symbol, limit)
    cached = _news_cache.get(cache_key)
    if cached and _is_fresh(cached[0], NEWS_TTL):
        return _clone_news(cached[1])

    try:
        news_items = list(get_ticker(symbol).news or [])
    except Exception:
        news_items = []

    if limit is not None:
        news_items = news_items[:limit]

    _news_cache[cache_key] = (_now(), news_items)
    return _clone_news(news_items)


def get_batch_ticker_news(symbols, limit: int | None = None) -> dict[str, list]:
    """Return cached raw news items for multiple tickers."""
    normalized = _normalize_symbols(symbols)
    if not normalized:
        return {}

    results: dict[str, list] = {}
    missing: list[str] = []

    for symbol in normalized:
        cache_key = (symbol, limit)
        cached = _news_cache.get(cache_key)
        if cached and _is_fresh(cached[0], NEWS_TTL):
            results[symbol] = _clone_news(cached[1])
        else:
            missing.append(symbol)

    if not missing:
        return results

    try:
        tickers = yf.Tickers(" ".join(missing))
        fetched_at = _now()
        for symbol in missing:
            try:
                news_items = list(tickers.tickers[symbol].news or [])
            except Exception:
                news_items = []

            if limit is not None:
                news_items = news_items[:limit]

            _news_cache[(symbol, limit)] = (fetched_at, news_items)
            results[symbol] = _clone_news(news_items)
    except Exception:
        for symbol in missing:
            results[symbol] = get_ticker_news(symbol, limit=limit)

    return results


def get_premium_ticker_news(symbol: str, limit: int | None = None, days: int = 7) -> list[dict]:
    """Return cached premium news items for a ticker from Benzinga and Polygon."""
    symbol = _normalize_symbol(symbol)
    cache_key = (symbol, limit, days)
    cached = _premium_news_cache.get(cache_key)
    if cached and _is_fresh(cached[0], PREMIUM_NEWS_TTL):
        return _clone_news(cached[1])

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    news_items: list[dict] = []

    if BENZINGA_API_KEY and BENZINGA_API_KEY != "your_benzinga_api_key_here":
        try:
            url = (
                "https://api.benzinga.com/api/v2/news"
                f"?token={BENZINGA_API_KEY}"
                f"&tickers={symbol}"
                f"&dateFrom={start_str}"
                f"&dateTo={end_str}"
            )
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                for article in response.json():
                    news_items.append(
                        {
                            "title": article.get("title", ""),
                            "publisher": "Benzinga",
                            "link": article.get("url", ""),
                            "published": article.get("created", ""),
                            "teaser": article.get("teaser", ""),
                        }
                    )
        except Exception:
            pass

    if MASSIVE_API_KEY and MASSIVE_API_KEY != "your_massive_api_key_here":
        try:
            url = (
                "https://api.polygon.io/v2/reference/news"
                f"?ticker={symbol}"
                f"&published_utc.gte={start_str}"
                f"&limit={limit or 20}"
                f"&apiKey={MASSIVE_API_KEY}"
            )
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                for article in response.json().get("results", []):
                    publisher_name = article.get("publisher", {}).get("name", "")
                    if "yahoo" in publisher_name.lower():
                        continue

                    news_items.append(
                        {
                            "title": article.get("title", ""),
                            "publisher": publisher_name,
                            "link": article.get("article_url", ""),
                            "published": article.get("published_utc", ""),
                            "teaser": article.get("description", ""),
                        }
                    )
        except Exception:
            pass

    news_items = _sort_news_by_published(_dedupe_news_items(news_items))
    if limit is not None:
        news_items = news_items[:limit]

    _premium_news_cache[cache_key] = (_now(), news_items)
    return _clone_news(news_items)


def get_batch_premium_ticker_news(symbols, limit: int | None = None, days: int = 7) -> dict[str, list[dict]]:
    """Return premium news items for multiple tickers from Benzinga and Polygon."""
    normalized = _normalize_symbols(symbols)
    if not normalized:
        return {}

    return {
        symbol: get_premium_ticker_news(symbol, limit=limit, days=days)
        for symbol in normalized
    }


def get_price_history(symbol: str, period: str) -> pd.DataFrame:
    """Return cached price history for a ticker and period."""
    symbol = _normalize_symbol(symbol)
    cache_key = (symbol, period)
    cached = _history_cache.get(cache_key)
    if cached and _is_fresh(cached[0], HISTORY_TTL):
        return cached[1].copy()

    try:
        history = get_ticker(symbol).history(period=period)
    except Exception:
        history = pd.DataFrame()

    _history_cache[cache_key] = (_now(), history)
    return history.copy()


def download_close_prices(symbols, **kwargs):
    """Return cached close-price download data for a batch of symbols."""
    normalized = _normalize_symbols(symbols)
    if not normalized:
        return pd.DataFrame()

    cache_key = (
        tuple(normalized),
        tuple(sorted((str(key), str(value)) for key, value in kwargs.items())),
    )
    cached = _download_cache.get(cache_key)
    if cached and _is_fresh(cached[0], DOWNLOAD_TTL):
        return cached[1].copy()

    downloaded = yf.download(normalized, progress=False, **kwargs)
    close_prices = downloaded["Close"] if isinstance(downloaded, pd.DataFrame) and "Close" in downloaded else downloaded
    _download_cache[cache_key] = (_now(), close_prices)
    return close_prices.copy()
