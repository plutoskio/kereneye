"""
Portfolio Analytics — Performance calculations for the portfolio.

Computes returns, Sharpe ratio, Beta vs S&P 500, and allocation breakdowns.
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional

from .models import EnrichedHolding


def calculate_portfolio_performance(
    enriched_holdings: list[EnrichedHolding],
    period: str = "1y",
) -> dict:
    """
    Calculate portfolio-level performance metrics:
    - Historical portfolio value over time
    - Total return
    - Annualized return
    - Sharpe ratio
    - Beta vs S&P 500
    - Best and worst performers
    """

    if not enriched_holdings:
        return {
            "total_return_pct": 0,
            "annualized_return_pct": 0,
            "sharpe_ratio": None,
            "beta": None,
            "volatility_pct": 0,
            "best_performer": None,
            "worst_performer": None,
            "portfolio_history": [],
            "benchmark_history": [],
        }

    # ---------------------------------------------------------------
    # 1. Fetch price history for all holdings + S&P 500
    # ---------------------------------------------------------------
    tickers = [h.ticker for h in enriched_holdings]
    all_tickers = tickers + ["^GSPC"]  # S&P 500 as benchmark

    try:
        price_data = yf.download(all_tickers, period=period, progress=False)["Close"]
    except Exception as e:
        print(f"  ⚠ Failed to download price data: {e}")
        return _empty_performance()

    if price_data.empty:
        return _empty_performance()

    # Handle single ticker case (yf.download returns Series, not DataFrame)
    if isinstance(price_data, pd.Series):
        price_data = price_data.to_frame(name=all_tickers[0])

    # Forward-fill missing data, then drop any remaining NaN rows
    price_data = price_data.ffill().dropna()

    if len(price_data) < 2:
        return _empty_performance()

    # ---------------------------------------------------------------
    # 2. Build portfolio value time series
    # ---------------------------------------------------------------
    # Weight each stock by number of shares
    holdings_map = {h.ticker: h.shares for h in enriched_holdings}

    portfolio_value = pd.Series(0.0, index=price_data.index)
    for ticker in tickers:
        if ticker in price_data.columns:
            portfolio_value += price_data[ticker] * holdings_map.get(ticker, 0)

    # Normalize to percentage returns for Sharpe/Beta
    portfolio_returns = portfolio_value.pct_change().dropna()

    # ---------------------------------------------------------------
    # 3. S&P 500 benchmark returns
    # ---------------------------------------------------------------
    benchmark_col = "^GSPC"
    if benchmark_col in price_data.columns:
        benchmark_returns = price_data[benchmark_col].pct_change().dropna()
        benchmark_values = price_data[benchmark_col]
    else:
        benchmark_returns = pd.Series(dtype=float)
        benchmark_values = pd.Series(dtype=float)

    # ---------------------------------------------------------------
    # 4. Total return
    # ---------------------------------------------------------------
    if len(portfolio_value) >= 2 and portfolio_value.iloc[0] != 0:
        total_return_pct = ((portfolio_value.iloc[-1] / portfolio_value.iloc[0]) - 1) * 100
    else:
        total_return_pct = 0.0

    # ---------------------------------------------------------------
    # 5. Annualized return
    # ---------------------------------------------------------------
    trading_days = len(portfolio_returns)
    if trading_days > 0 and portfolio_value.iloc[0] != 0:
        total_return_decimal = portfolio_value.iloc[-1] / portfolio_value.iloc[0]
        years = trading_days / 252
        annualized_return_pct = ((total_return_decimal ** (1 / years)) - 1) * 100 if years > 0 else 0
    else:
        annualized_return_pct = 0.0

    # ---------------------------------------------------------------
    # 6. Volatility (annualized)
    # ---------------------------------------------------------------
    if len(portfolio_returns) > 1:
        volatility = portfolio_returns.std() * np.sqrt(252) * 100
    else:
        volatility = 0.0

    # ---------------------------------------------------------------
    # 7. Sharpe Ratio (assuming 4.5% risk-free rate)
    # ---------------------------------------------------------------
    risk_free_rate = 0.045  # Approximate current Treasury rate
    if volatility > 0:
        sharpe = (annualized_return_pct / 100 - risk_free_rate) / (volatility / 100)
        sharpe = round(sharpe, 2)
    else:
        sharpe = None

    # ---------------------------------------------------------------
    # 8. Beta vs S&P 500
    # ---------------------------------------------------------------
    beta = None
    if len(benchmark_returns) > 10 and len(portfolio_returns) > 10:
        # Align the two series
        aligned = pd.DataFrame({
            "portfolio": portfolio_returns,
            "benchmark": benchmark_returns,
        }).dropna()

        if len(aligned) > 10:
            cov = aligned["portfolio"].cov(aligned["benchmark"])
            var = aligned["benchmark"].var()
            if var > 0:
                beta = round(cov / var, 2)

    # ---------------------------------------------------------------
    # 9. Best / worst performer
    # ---------------------------------------------------------------
    performers = []
    for h in enriched_holdings:
        if h.total_cost > 0:
            performers.append({
                "ticker": h.ticker,
                "name": h.name,
                "pnl_pct": h.pnl_pct,
            })

    performers.sort(key=lambda x: x["pnl_pct"], reverse=True)
    best = performers[0] if performers else None
    worst = performers[-1] if performers else None

    # ---------------------------------------------------------------
    # 10. Build history arrays for charting
    # ---------------------------------------------------------------
    portfolio_history = []
    for date, value in portfolio_value.items():
        portfolio_history.append({
            "date": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date),
            "value": round(float(value), 2),
        })

    benchmark_history = []
    if not benchmark_values.empty:
        # Normalize benchmark to portfolio's starting value for comparison
        bench_start = benchmark_values.iloc[0]
        port_start = portfolio_value.iloc[0] if portfolio_value.iloc[0] != 0 else 1

        for date, value in benchmark_values.items():
            normalized = (value / bench_start) * port_start if bench_start != 0 else 0
            benchmark_history.append({
                "date": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date),
                "value": round(float(normalized), 2),
            })

    return {
        "total_return_pct": round(total_return_pct, 2),
        "annualized_return_pct": round(annualized_return_pct, 2),
        "sharpe_ratio": sharpe,
        "beta": beta,
        "volatility_pct": round(volatility, 2),
        "best_performer": best,
        "worst_performer": worst,
        "portfolio_history": portfolio_history,
        "benchmark_history": benchmark_history,
    }


def _empty_performance() -> dict:
    """Return an empty performance result."""
    return {
        "total_return_pct": 0,
        "annualized_return_pct": 0,
        "sharpe_ratio": None,
        "beta": None,
        "volatility_pct": 0,
        "best_performer": None,
        "worst_performer": None,
        "portfolio_history": [],
        "benchmark_history": [],
    }
