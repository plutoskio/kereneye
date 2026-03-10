"""
Portfolio Manager — CRUD operations with JSON file persistence.

Manages holdings and transactions, persisted to cache/portfolio/.
Fetches live prices via yfinance for real-time P&L calculations.
"""

import json
import os
from datetime import datetime
from typing import Optional

import yfinance as yf

from .models import Holding, Transaction, EnrichedHolding, PortfolioSummary


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "portfolio")
HOLDINGS_FILE = os.path.join(CACHE_DIR, "holdings.json")
TRANSACTIONS_FILE = os.path.join(CACHE_DIR, "transactions.json")

os.makedirs(CACHE_DIR, exist_ok=True)


class PortfolioManager:
    """Manages portfolio holdings and transactions with JSON persistence."""

    # -------------------------------------------------------------------
    # Persistence helpers
    # -------------------------------------------------------------------

    def _load_holdings(self) -> list[Holding]:
        """Load holdings from JSON file."""
        if not os.path.exists(HOLDINGS_FILE):
            return []
        try:
            with open(HOLDINGS_FILE, "r") as f:
                data = json.load(f)
            return [Holding.from_dict(h) for h in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def _save_holdings(self, holdings: list[Holding]) -> None:
        """Save holdings to JSON file."""
        with open(HOLDINGS_FILE, "w") as f:
            json.dump([h.to_dict() for h in holdings], f, indent=2)

    def _load_transactions(self) -> list[Transaction]:
        """Load transactions from JSON file."""
        if not os.path.exists(TRANSACTIONS_FILE):
            return []
        try:
            with open(TRANSACTIONS_FILE, "r") as f:
                data = json.load(f)
            return [Transaction.from_dict(t) for t in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def _save_transactions(self, transactions: list[Transaction]) -> None:
        """Save transactions to JSON file."""
        with open(TRANSACTIONS_FILE, "w") as f:
            json.dump([t.to_dict() for t in transactions], f, indent=2)

    def _append_transaction(self, transaction: Transaction) -> None:
        """Append a single transaction to the log."""
        transactions = self._load_transactions()
        transactions.append(transaction)
        self._save_transactions(transactions)

    # -------------------------------------------------------------------
    # CRUD operations
    # -------------------------------------------------------------------

    def add_holding(self, ticker: str, shares: float, avg_cost: float) -> Holding:
        """
        Add a holding to the portfolio. If the ticker already exists,
        recalculate average cost with weighted average.
        """
        ticker = ticker.upper()
        holdings = self._load_holdings()

        existing = next((h for h in holdings if h.ticker == ticker), None)

        if existing:
            # Weighted average cost
            total_shares = existing.shares + shares
            total_cost = (existing.shares * existing.avg_cost) + (shares * avg_cost)
            existing.avg_cost = total_cost / total_shares
            existing.shares = total_shares
            result = existing
        else:
            new_holding = Holding(
                ticker=ticker,
                shares=shares,
                avg_cost=avg_cost,
                date_added=datetime.now().isoformat(),
            )
            holdings.append(new_holding)
            result = new_holding

        self._save_holdings(holdings)

        # Record transaction
        self._append_transaction(Transaction(
            ticker=ticker,
            type="buy",
            shares=shares,
            price=avg_cost,
            timestamp=datetime.now().isoformat(),
        ))

        return result

    def remove_holding(self, ticker: str) -> bool:
        """Remove a holding entirely from the portfolio."""
        ticker = ticker.upper()
        holdings = self._load_holdings()

        original_len = len(holdings)
        # Get the holding before removing for transaction log
        removed = next((h for h in holdings if h.ticker == ticker), None)
        holdings = [h for h in holdings if h.ticker != ticker]

        if len(holdings) == original_len:
            return False  # Not found

        self._save_holdings(holdings)

        # Record sell transaction (at current price if available, else avg_cost)
        if removed:
            try:
                info = yf.Ticker(ticker).info
                price = info.get("currentPrice", info.get("regularMarketPrice", removed.avg_cost))
            except Exception:
                price = removed.avg_cost

            self._append_transaction(Transaction(
                ticker=ticker,
                type="sell",
                shares=removed.shares,
                price=price,
                timestamp=datetime.now().isoformat(),
            ))

        return True

    def get_holdings(self) -> list[Holding]:
        """Get raw holdings without live prices."""
        return self._load_holdings()

    def get_transactions(self) -> list[dict]:
        """Get all transactions as dicts, newest first."""
        transactions = self._load_transactions()
        return [t.to_dict() for t in reversed(transactions)]

    # -------------------------------------------------------------------
    # Enriched data (with live prices)
    # -------------------------------------------------------------------

    def get_enriched_holdings(self) -> list[EnrichedHolding]:
        """Fetch current prices and enrich holdings with live data."""
        holdings = self._load_holdings()
        if not holdings:
            return []

        # Batch fetch all tickers at once for efficiency
        tickers_str = " ".join(h.ticker for h in holdings)
        enriched = []

        try:
            tickers_obj = yf.Tickers(tickers_str)

            for holding in holdings:
                try:
                    info = tickers_obj.tickers[holding.ticker].info or {}
                    current_price = info.get(
                        "currentPrice",
                        info.get("regularMarketPrice", 0)
                    )
                    name = info.get("longName", info.get("shortName", holding.ticker))
                    sector = info.get("sector", "Unknown")

                    enriched.append(EnrichedHolding(
                        ticker=holding.ticker,
                        name=name,
                        sector=sector,
                        shares=holding.shares,
                        avg_cost=holding.avg_cost,
                        current_price=current_price or 0,
                        date_added=holding.date_added,
                    ))
                except Exception as e:
                    print(f"  ⚠ Failed to enrich {holding.ticker}: {e}")
                    enriched.append(EnrichedHolding(
                        ticker=holding.ticker,
                        name=holding.ticker,
                        sector="Unknown",
                        shares=holding.shares,
                        avg_cost=holding.avg_cost,
                        current_price=0,
                        date_added=holding.date_added,
                    ))
        except Exception as e:
            print(f"  ⚠ Batch yfinance fetch failed: {e}")
            for holding in holdings:
                enriched.append(EnrichedHolding(
                    ticker=holding.ticker,
                    name=holding.ticker,
                    sector="Unknown",
                    shares=holding.shares,
                    avg_cost=holding.avg_cost,
                    current_price=0,
                    date_added=holding.date_added,
                ))

        return enriched

    def get_portfolio_summary(self) -> PortfolioSummary:
        """Calculate full portfolio summary with sector allocation."""
        enriched = self.get_enriched_holdings()

        if not enriched:
            return PortfolioSummary(last_updated=datetime.now().isoformat())

        total_value = sum(h.market_value for h in enriched)
        total_cost = sum(h.total_cost for h in enriched)
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

        # Sector allocation
        sector_allocation = {}
        for h in enriched:
            if h.sector not in sector_allocation:
                sector_allocation[h.sector] = 0.0
            sector_allocation[h.sector] += h.market_value

        # Convert to percentages
        if total_value > 0:
            sector_allocation = {
                k: round(v / total_value * 100, 2)
                for k, v in sector_allocation.items()
            }

        # Weight per holding
        holdings_with_weight = []
        for h in enriched:
            d = h.to_dict()
            d["weight_pct"] = round(h.market_value / total_value * 100, 2) if total_value > 0 else 0
            holdings_with_weight.append(d)

        return PortfolioSummary(
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            holdings=holdings_with_weight,
            sector_allocation=sector_allocation,
            last_updated=datetime.now().isoformat(),
        )
