"""
Portfolio Analytics — Performance calculations for the portfolio.

Computes returns, Sharpe ratio, Beta vs S&P 500, and allocation breakdowns.
Uses each holding's date_added to only count its contribution from that date.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from services.market_data_service import download_close_prices
from .models import EnrichedHolding


def calculate_portfolio_performance(
    enriched_holdings: list[EnrichedHolding],
    period: str = "1y",
    cash_balance: float = 0.0,
) -> dict:
    """
    Calculate portfolio-level performance metrics.
    Each holding only contributes to the portfolio value from its date_added.
    To avoid treating later purchases as performance, assume the account began
    with enough cash to fund each recorded position at its purchase cost.
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
        price_data = download_close_prices(all_tickers, **download_kwargs)
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
    # 3. Build date-aware holdings and synthetic cash time series
    # ---------------------------------------------------------------
    holdings_dates = {}
    for h in enriched_holdings:
        try:
            dt = datetime.fromisoformat(h.date_added)
            holdings_dates[h.ticker] = dt
        except (ValueError, TypeError):
            # If no date, assume it was always held
            holdings_dates[h.ticker] = start_date

    holdings_map = {h.ticker: h for h in enriched_holdings}
    first_visible_date = price_data.index[0]

    holdings_value = pd.Series(0.0, index=price_data.index)
    for ticker in tickers:
        if ticker not in price_data.columns:
            continue

        h = holdings_map[ticker]
        add_date = holdings_dates[ticker]

        # Create a mask: only count this holding from its date_added
        mask = price_data.index >= pd.Timestamp(add_date.date())
        contribution = price_data[ticker] * h.shares
        contribution = contribution.where(mask, 0.0)
        holdings_value += contribution

    # Start with any explicit positive cash balance and synthetically reserve
    # purchase cash before each position becomes active.
    starting_cash = max(float(cash_balance), 0.0)
    synthetic_cash = pd.Series(starting_cash, index=price_data.index)

    for ticker in tickers:
        h = holdings_map[ticker]
        add_date = pd.Timestamp(holdings_dates[ticker].date())
        reserve_amount = h.shares * h.avg_cost

        if add_date > first_visible_date:
            reserve_mask = price_data.index < add_date
            reserve_series = pd.Series(reserve_amount, index=price_data.index)
            synthetic_cash += reserve_series.where(reserve_mask, 0.0)

    portfolio_equity = holdings_value + synthetic_cash

    # Only consider dates where we have at least one holding
    active_mask = portfolio_equity > 0
    if not active_mask.any():
        return _empty_performance()

    first_active = portfolio_equity[active_mask].index[0]
    portfolio_equity = portfolio_equity.loc[first_active:]
    holdings_value = holdings_value.loc[first_active:]
    synthetic_cash = synthetic_cash.loc[first_active:]

    portfolio_returns = portfolio_equity.pct_change().dropna()
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
    initial_equity = portfolio_equity.iloc[0]
    current_equity = portfolio_equity.iloc[-1]
    if initial_equity > 0:
        total_return_pct = ((current_equity / initial_equity) - 1) * 100
    else:
        total_return_pct = 0.0

    # ---------------------------------------------------------------
    # 6. Annualized return
    # ---------------------------------------------------------------
    trading_days = len(portfolio_returns)
    if trading_days > 0 and initial_equity > 0:
        total_return_decimal = current_equity / initial_equity
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
    normalized_portfolio = ((portfolio_equity / initial_equity) - 1) * 100 if initial_equity > 0 else portfolio_equity * 0
    for date, value in normalized_portfolio.items():
        portfolio_history.append({
            "date": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date),
            "value": round(float(value), 2),
        })

    portfolio_value_history = []
    for date, value in portfolio_equity.items():
        portfolio_value_history.append({
            "date": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date),
            "value": round(float(value), 2),
        })

    benchmark_history = []
    if not benchmark_prices.empty:
        bench_start = benchmark_prices.iloc[0]
        normalized_benchmark = ((benchmark_prices / bench_start) - 1) * 100 if bench_start != 0 else benchmark_prices * 0

        for date, value in normalized_benchmark.items():
            benchmark_history.append({
                "date": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date),
                "value": round(float(value), 2),
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
        "portfolio_value_history": portfolio_value_history,
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
        "portfolio_value_history": [],
        "benchmark_history": [],
    }
