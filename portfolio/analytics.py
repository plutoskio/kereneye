"""
Portfolio Analytics — Performance calculations for the portfolio.

Computes returns, Sharpe ratio, Beta vs S&P 500, and allocation breakdowns.
Uses each holding's date_added to only count its contribution from that date.
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
    Calculate portfolio-level performance metrics.
    Each holding only contributes to the portfolio value from its date_added.
    """

    if not enriched_holdings:
        return _empty_performance()

    # ---------------------------------------------------------------
    # 1. Determine date range from period
    # ---------------------------------------------------------------
    today = datetime.now()
    period_map = {
        "1mo": 30, "3mo": 90, "6mo": 180,
        "1y": 365, "2y": 730, "5y": 1825,
    }
    if period == "ytd":
        start_date = datetime(today.year, 1, 1)
        download_kwargs = {"start": start_date.strftime("%Y-%m-%d")}
    else:
        days = period_map.get(period, 365)
        start_date = today - timedelta(days=days)
        download_kwargs = {"period": period}

    # ---------------------------------------------------------------
    # 2. Fetch price history for all holdings + S&P 500
    # ---------------------------------------------------------------
    tickers = [h.ticker for h in enriched_holdings]
    all_tickers = tickers + ["^GSPC"]

    try:
        price_data = yf.download(all_tickers, progress=False, **download_kwargs)["Close"]
    except Exception as e:
        print(f"  ⚠ Failed to download price data: {e}")
        return _empty_performance()

    if price_data.empty:
        return _empty_performance()

    if isinstance(price_data, pd.Series):
        price_data = price_data.to_frame(name=all_tickers[0])

    price_data = price_data.ffill().dropna()

    if len(price_data) < 2:
        return _empty_performance()

    # ---------------------------------------------------------------
    # 3. Build date-aware portfolio value time series
    # ---------------------------------------------------------------
    # Parse each holding's date_added
    holdings_dates = {}
    for h in enriched_holdings:
        try:
            dt = datetime.fromisoformat(h.date_added)
            holdings_dates[h.ticker] = dt
        except (ValueError, TypeError):
            # If no date, assume it was always held
            holdings_dates[h.ticker] = start_date

    holdings_map = {h.ticker: h for h in enriched_holdings}

    portfolio_value = pd.Series(0.0, index=price_data.index)
    for ticker in tickers:
        if ticker not in price_data.columns:
            continue

        h = holdings_map[ticker]
        add_date = holdings_dates[ticker]

        # Create a mask: only count this holding from its date_added
        mask = price_data.index >= pd.Timestamp(add_date.date())
        contribution = price_data[ticker] * h.shares
        contribution = contribution.where(mask, 0.0)
        portfolio_value += contribution

    # Also calculate cost basis time series (for accurate return calculations)
    cost_basis = pd.Series(0.0, index=price_data.index)
    for ticker in tickers:
        if ticker not in price_data.columns:
            continue

        h = holdings_map[ticker]
        add_date = holdings_dates[ticker]
        mask = price_data.index >= pd.Timestamp(add_date.date())
        cost_contribution = pd.Series(h.shares * h.avg_cost, index=price_data.index)
        cost_contribution = cost_contribution.where(mask, 0.0)
        cost_basis += cost_contribution

    # Only consider dates where we have at least one holding
    active_mask = portfolio_value > 0
    if not active_mask.any():
        return _empty_performance()

    first_active = portfolio_value[active_mask].index[0]
    portfolio_value = portfolio_value.loc[first_active:]
    cost_basis = cost_basis.loc[first_active:]

    portfolio_returns = portfolio_value.pct_change().dropna()
    # Remove infinite or huge returns (from 0 -> value transitions)
    portfolio_returns = portfolio_returns.replace([np.inf, -np.inf], 0)
    portfolio_returns = portfolio_returns[portfolio_returns.abs() < 1]  # Cap at 100%

    # ---------------------------------------------------------------
    # 4. S&P 500 benchmark returns
    # ---------------------------------------------------------------
    benchmark_col = "^GSPC"
    if benchmark_col in price_data.columns:
        benchmark_prices = price_data[benchmark_col].loc[first_active:]
        benchmark_returns = benchmark_prices.pct_change().dropna()
    else:
        benchmark_returns = pd.Series(dtype=float)
        benchmark_prices = pd.Series(dtype=float)

    # ---------------------------------------------------------------
    # 5. Total return (based on current value vs cost basis)
    # ---------------------------------------------------------------
    current_value = portfolio_value.iloc[-1]
    current_cost = cost_basis.iloc[-1]
    if current_cost > 0:
        total_return_pct = ((current_value / current_cost) - 1) * 100
    else:
        total_return_pct = 0.0

    # ---------------------------------------------------------------
    # 6. Annualized return
    # ---------------------------------------------------------------
    trading_days = len(portfolio_returns)
    if trading_days > 0 and current_cost > 0:
        total_return_decimal = current_value / current_cost
        years = trading_days / 252
        annualized_return_pct = ((total_return_decimal ** (1 / years)) - 1) * 100 if years > 0 else 0
    else:
        annualized_return_pct = 0.0

    # ---------------------------------------------------------------
    # 7. Volatility (annualized)
    # ---------------------------------------------------------------
    if len(portfolio_returns) > 1:
        volatility = portfolio_returns.std() * np.sqrt(252) * 100
    else:
        volatility = 0.0

    # ---------------------------------------------------------------
    # 8. Sharpe Ratio (assuming 4.5% risk-free rate)
    # ---------------------------------------------------------------
    risk_free_rate = 0.045
    if volatility > 0:
        sharpe = (annualized_return_pct / 100 - risk_free_rate) / (volatility / 100)
        sharpe = round(sharpe, 2)
    else:
        sharpe = None

    # ---------------------------------------------------------------
    # 9. Beta vs S&P 500
    # ---------------------------------------------------------------
    beta = None
    if len(benchmark_returns) > 10 and len(portfolio_returns) > 10:
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
    # 10. Best / worst performer
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
    # 11. Build history arrays for charting
    # ---------------------------------------------------------------
    portfolio_history = []
    for date, value in portfolio_value.items():
        portfolio_history.append({
            "date": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date),
            "value": round(float(value), 2),
        })

    benchmark_history = []
    if not benchmark_prices.empty:
        bench_start = benchmark_prices.iloc[0]
        port_start = portfolio_value.iloc[0] if portfolio_value.iloc[0] != 0 else 1

        for date, value in benchmark_prices.items():
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
        "volatility_pct": round(float(volatility), 2),
        "best_performer": best,
        "worst_performer": worst,
        "portfolio_history": portfolio_history,
        "benchmark_history": benchmark_history,
    }


def _empty_performance() -> dict:
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
