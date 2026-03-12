"""
Portfolio Analytics — Performance calculations for the portfolio.

Computes returns, Sharpe ratio, Beta vs S&P 500, and allocation breakdowns
by replaying the transaction ledger into daily portfolio equity.
"""

from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from services.market_data_service import download_close_prices
from .models import EnrichedHolding, Transaction


def _parse_timestamp(value: str | None, fallback: datetime) -> pd.Timestamp:
    try:
        return pd.Timestamp(datetime.fromisoformat(value)).normalize()
    except (TypeError, ValueError):
        return pd.Timestamp(fallback.date())


def _resolve_market_date(tx_date: pd.Timestamp, market_index: pd.DatetimeIndex) -> pd.Timestamp | None:
    if market_index.empty:
        return None

    position = market_index.searchsorted(tx_date)
    if position >= len(market_index):
        return market_index[-1]
    return market_index[position]


def _get_portfolio_inception_date(
    transactions: list[Transaction],
    fallback: datetime,
    market_index: pd.DatetimeIndex,
) -> pd.Timestamp | None:
    if not transactions:
        return _resolve_market_date(pd.Timestamp(fallback.date()), market_index)

    first_tx = min(_parse_timestamp(tx.timestamp, fallback) for tx in transactions)
    return _resolve_market_date(first_tx, market_index)


def _build_inferred_transactions(
    enriched_holdings: list[EnrichedHolding],
    fallback_date: datetime,
) -> list[Transaction]:
    inferred = []
    for holding in enriched_holdings:
        inferred.append(
            Transaction(
                type="buy",
                ticker=holding.ticker,
                shares=holding.shares,
                price=holding.avg_cost,
                timestamp=holding.date_added or fallback_date.date().isoformat(),
            )
        )
    return inferred


def _replay_cash_from_zero(transactions: list[Transaction]) -> float:
    cash = 0.0

    for transaction in transactions:
        if transaction.type == "buy":
            cash -= transaction.shares * transaction.price
        elif transaction.type == "sell":
            cash += transaction.shares * transaction.price
        elif transaction.type == "cash_deposit":
            cash += transaction.amount
        elif transaction.type == "cash_withdrawal":
            cash -= transaction.amount
        elif transaction.type == "cash_snapshot":
            cash = transaction.amount

    return float(cash)


def calculate_portfolio_performance(
    enriched_holdings: list[EnrichedHolding],
    transactions: list[Transaction],
    period: str = "1y",
    cash_balance: float = 0.0,
) -> dict:
    """
    Calculate portfolio-level performance metrics.
    Replay the dated transaction ledger to reconstruct historical positions and
    cash. External cash flows are neutralized in the return series so adding
    capital does not appear as performance.
    """

    if not enriched_holdings and not transactions and cash_balance <= 0:
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
    ledger_transactions = list(transactions) if transactions else _build_inferred_transactions(enriched_holdings, start_date)

    tickers = sorted(
        {
            h.ticker for h in enriched_holdings
        } | {
            t.ticker for t in ledger_transactions if t.ticker
        }
    )
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

    price_data.index = pd.to_datetime(price_data.index).tz_localize(None).normalize()
    price_data = price_data.sort_index().ffill()
    price_data = price_data.dropna(how="all")

    if len(price_data) < 2:
        return _empty_performance()

    # ---------------------------------------------------------------
    # 3. Replay transactions into daily positions and cash
    # ---------------------------------------------------------------
    market_index = price_data.index
    first_visible_date = market_index[0]

    sorted_transactions = sorted(
        ledger_transactions,
        key=lambda tx: _parse_timestamp(tx.timestamp, start_date),
    )

    initial_cash = float(cash_balance) - _replay_cash_from_zero(sorted_transactions)
    cash = initial_cash
    positions = defaultdict(float)
    scheduled_transactions = defaultdict(list)

    for transaction in sorted_transactions:
        tx_date = _parse_timestamp(transaction.timestamp, start_date)

        if tx_date < first_visible_date:
            if transaction.type == "buy":
                positions[transaction.ticker] += transaction.shares
                cash -= transaction.shares * transaction.price
            elif transaction.type == "sell":
                positions[transaction.ticker] -= transaction.shares
                cash += transaction.shares * transaction.price
            elif transaction.type == "cash_deposit":
                cash += transaction.amount
            elif transaction.type == "cash_withdrawal":
                cash -= transaction.amount
            elif transaction.type == "cash_snapshot":
                cash = transaction.amount
            continue

        market_date = _resolve_market_date(tx_date, market_index)
        if market_date is not None:
            scheduled_transactions[market_date].append(transaction)

    equity_points = []
    holdings_points = []
    external_flow_points = []

    for date in market_index:
        day_external_flow = 0.0

        for transaction in scheduled_transactions.get(date, []):
            if transaction.type == "buy":
                positions[transaction.ticker] += transaction.shares
                cash -= transaction.shares * transaction.price
            elif transaction.type == "sell":
                positions[transaction.ticker] -= transaction.shares
                if abs(positions[transaction.ticker]) <= 1e-9:
                    positions.pop(transaction.ticker, None)
                cash += transaction.shares * transaction.price
            elif transaction.type == "cash_deposit":
                cash += transaction.amount
                day_external_flow += transaction.amount
            elif transaction.type == "cash_withdrawal":
                cash -= transaction.amount
                day_external_flow -= transaction.amount
            elif transaction.type == "cash_snapshot":
                snapshot_delta = transaction.amount - cash
                cash = transaction.amount
                day_external_flow += snapshot_delta

        holdings_value = 0.0
        for ticker, shares in positions.items():
            if ticker not in price_data.columns or abs(shares) <= 1e-9:
                continue

            price = price_data.at[date, ticker]
            if pd.isna(price):
                continue

            holdings_value += float(price) * shares

        portfolio_equity = cash + holdings_value
        equity_points.append(portfolio_equity)
        holdings_points.append(holdings_value)
        external_flow_points.append(day_external_flow)

    portfolio_equity = pd.Series(equity_points, index=market_index, dtype=float)
    holdings_value = pd.Series(holdings_points, index=market_index, dtype=float)
    external_flows = pd.Series(external_flow_points, index=market_index, dtype=float)

    # Only consider dates where the account has positive equity
    active_mask = portfolio_equity > 0
    if not active_mask.any():
        return _empty_performance()

    first_active = portfolio_equity[active_mask].index[0]
    inception_date = _get_portfolio_inception_date(sorted_transactions, start_date, market_index)
    history_start = max(first_active, inception_date) if inception_date is not None else first_active

    portfolio_equity = portfolio_equity.loc[history_start:]
    holdings_value = holdings_value.loc[history_start:]
    external_flows = external_flows.loc[history_start:]

    previous_equity = portfolio_equity.shift(1)
    portfolio_returns = (portfolio_equity - previous_equity - external_flows) / previous_equity
    portfolio_returns = portfolio_returns.replace([np.inf, -np.inf], np.nan).dropna()
    portfolio_returns = portfolio_returns[portfolio_returns.abs() < 1]

    # ---------------------------------------------------------------
    # 4. S&P 500 benchmark returns
    # ---------------------------------------------------------------
    benchmark_col = "^GSPC"
    if benchmark_col in price_data.columns:
        benchmark_prices = price_data[benchmark_col].loc[history_start:]
        benchmark_returns = benchmark_prices.pct_change().dropna()
    else:
        benchmark_returns = pd.Series(dtype=float)
        benchmark_prices = pd.Series(dtype=float)

    # ---------------------------------------------------------------
    # 5. Total return (based on current value vs cost basis)
    # ---------------------------------------------------------------
    if len(portfolio_returns) > 0:
        cumulative_return = (1 + portfolio_returns).prod()
        total_return_pct = (cumulative_return - 1) * 100
    else:
        total_return_pct = 0.0

    # ---------------------------------------------------------------
    # 6. Annualized return
    # ---------------------------------------------------------------
    trading_days = len(portfolio_returns)
    if trading_days > 0:
        total_return_decimal = 1 + (total_return_pct / 100)
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
    normalized_portfolio = pd.Series(0.0, index=portfolio_equity.index, dtype=float)
    if len(portfolio_returns) > 0:
        cumulative_growth = (1 + portfolio_returns).cumprod()
        normalized_portfolio.loc[cumulative_growth.index] = (cumulative_growth - 1) * 100

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
        "total_return_pct": round(float(total_return_pct), 2),
        "annualized_return_pct": round(float(annualized_return_pct), 2),
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
