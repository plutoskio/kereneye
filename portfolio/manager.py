"""
Portfolio Manager — CRUD operations with JSON file persistence.

Manages holdings, transactions, and cash balance, persisted to cache/portfolio/.
Fetches live prices via the shared market data service for real-time P&L calculations.
"""

import json
import os
from datetime import datetime

from services.file_service import write_json_atomic
from services.market_data_service import get_batch_ticker_info, get_ticker_info

from .models import Holding, Transaction, EnrichedHolding, PortfolioSummary


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "portfolio")
HOLDINGS_FILE = os.path.join(CACHE_DIR, "holdings.json")
TRANSACTIONS_FILE = os.path.join(CACHE_DIR, "transactions.json")
CASH_FILE = os.path.join(CACHE_DIR, "cash.json")

os.makedirs(CACHE_DIR, exist_ok=True)


class PortfolioManager:
    """Manages portfolio holdings, transactions, and cash with JSON persistence."""

    # -------------------------------------------------------------------
    # Persistence helpers
    # -------------------------------------------------------------------

    def _load_holdings(self) -> list[Holding]:
        if not os.path.exists(HOLDINGS_FILE):
            return []
        try:
            with open(HOLDINGS_FILE, "r") as f:
                data = json.load(f)
            return [Holding.from_dict(h) for h in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def _save_holdings(self, holdings: list[Holding]) -> None:
        write_json_atomic(HOLDINGS_FILE, [h.to_dict() for h in holdings], indent=2)

    def _load_transactions(self) -> list[Transaction]:
        if not os.path.exists(TRANSACTIONS_FILE):
            return []
        try:
            with open(TRANSACTIONS_FILE, "r") as f:
                data = json.load(f)
            return [Transaction.from_dict(t) for t in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def _save_transactions(self, transactions: list[Transaction]) -> None:
        write_json_atomic(TRANSACTIONS_FILE, [t.to_dict() for t in transactions], indent=2)

    def _append_transaction(self, transaction: Transaction) -> None:
        transactions = self._load_transactions()
        transactions.append(transaction)
        self._save_transactions(transactions)

    # -------------------------------------------------------------------
    # Cash balance
    # -------------------------------------------------------------------

    def get_cash(self) -> float:
        """Get current cash balance."""
        if not os.path.exists(CASH_FILE):
            return 0.0
        try:
            with open(CASH_FILE, "r") as f:
                data = json.load(f)
            return data.get("balance", 0.0)
        except (json.JSONDecodeError, KeyError):
            return 0.0

    def set_cash(self, amount: float) -> float:
        """Set cash balance to a specific amount."""
        write_json_atomic(
            CASH_FILE,
            {
                "balance": round(amount, 2),
                "last_updated": datetime.now().isoformat(),
            },
            indent=2,
        )
        return amount

    def adjust_cash(self, delta: float) -> float:
        """Adjust cash balance by a delta amount (positive = add, negative = deduct)."""
        current = self.get_cash()
        new_balance = current + delta
        return self.set_cash(new_balance)

    # -------------------------------------------------------------------
    # Realized P&L
    # -------------------------------------------------------------------

    def get_realized_pnl(self) -> float:
        """Calculate total realized P&L from all sell transactions."""
        transactions = self._load_transactions()
        return sum(t.realized_pnl for t in transactions if t.type == "sell")

    # -------------------------------------------------------------------
    # CRUD operations
    # -------------------------------------------------------------------

    def add_holding(self, ticker: str, shares: float, avg_cost: float, date_added: str | None = None) -> Holding:
        """
        Add a holding to the portfolio. If the ticker already exists,
        recalculate average cost with weighted average.
        Deducts cost from cash balance.
        """
        ticker = ticker.upper()
        holdings = self._load_holdings()

        existing = next((h for h in holdings if h.ticker == ticker), None)

        if existing:
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
                date_added=date_added or datetime.now().isoformat(),
            )
            holdings.append(new_holding)
            result = new_holding

        self._save_holdings(holdings)

        # Deduct from cash
        self.adjust_cash(-(shares * avg_cost))

        # Record transaction
        self._append_transaction(Transaction(
            ticker=ticker,
            type="buy",
            shares=shares,
            price=avg_cost,
            timestamp=datetime.now().isoformat(),
        ))

        return result

    def sell_shares(self, ticker: str, shares: float, sell_price: float) -> dict:
        """
        Sell shares of a holding. Calculates realized P&L.
        If all shares sold, removes the holding.
        Adds proceeds to cash balance.
        Returns dict with details of the sale.
        """
        ticker = ticker.upper()
        holdings = self._load_holdings()

        existing = next((h for h in holdings if h.ticker == ticker), None)
        if not existing:
            raise ValueError(f"No holding found for {ticker}")

        if shares > existing.shares:
            raise ValueError(f"Cannot sell {shares} shares — only {existing.shares} held")

        # Calculate realized P&L for this sell
        avg_cost = existing.avg_cost
        realized_pnl = (sell_price - avg_cost) * shares

        # Update holding
        existing.shares -= shares
        if existing.shares <= 0.001:  # Effectively zero (floating point)
            holdings = [h for h in holdings if h.ticker != ticker]
        
        self._save_holdings(holdings)

        # Add proceeds to cash
        proceeds = shares * sell_price
        self.adjust_cash(proceeds)

        # Log transaction
        self._append_transaction(Transaction(
            ticker=ticker,
            type="sell",
            shares=shares,
            price=sell_price,
            timestamp=datetime.now().isoformat(),
            realized_pnl=realized_pnl,
        ))

        return {
            "ticker": ticker,
            "shares_sold": shares,
            "sell_price": sell_price,
            "proceeds": round(proceeds, 2),
            "realized_pnl": round(realized_pnl, 2),
            "remaining_shares": round(existing.shares, 4) if existing.shares > 0.001 else 0,
        }

    def remove_holding(self, ticker: str) -> bool:
        """Remove a holding entirely from the portfolio."""
        ticker = ticker.upper()
        holdings = self._load_holdings()

        original_len = len(holdings)
        removed = next((h for h in holdings if h.ticker == ticker), None)
        holdings = [h for h in holdings if h.ticker != ticker]

        if len(holdings) == original_len:
            return False

        self._save_holdings(holdings)

        if removed:
            try:
                info = get_ticker_info(ticker)
                price = info.get("currentPrice", info.get("regularMarketPrice", removed.avg_cost))
            except Exception:
                price = removed.avg_cost

            realized_pnl = (price - removed.avg_cost) * removed.shares
            proceeds = removed.shares * price
            self.adjust_cash(proceeds)

            self._append_transaction(Transaction(
                ticker=ticker,
                type="sell",
                shares=removed.shares,
                price=price,
                timestamp=datetime.now().isoformat(),
                realized_pnl=realized_pnl,
            ))

        return True

    def get_holdings(self) -> list[Holding]:
        return self._load_holdings()

    def get_transactions(self) -> list[dict]:
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

        enriched = []

        try:
            ticker_infos = get_batch_ticker_info(h.ticker for h in holdings)

            for holding in holdings:
                try:
                    info = ticker_infos.get(holding.ticker, {})
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
            print(f"  ⚠ Batch market-data fetch failed: {e}")
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
        """Calculate full portfolio summary with sector allocation, cash, and realized P&L."""
        enriched = self.get_enriched_holdings()
        cash = self.get_cash()
        realized_pnl = self.get_realized_pnl()

        if not enriched:
            return PortfolioSummary(
                cash_balance=cash,
                total_value=cash,
                realized_pnl=realized_pnl,
                last_updated=datetime.now().isoformat(),
            )

        holdings_value = sum(h.market_value for h in enriched)
        total_cost = sum(h.total_cost for h in enriched)
        unrealized_pnl = holdings_value - total_cost
        unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0

        total_value = holdings_value + cash

        # Sector allocation (of holdings only, not cash)
        sector_allocation = {}
        for h in enriched:
            if h.sector not in sector_allocation:
                sector_allocation[h.sector] = 0.0
            sector_allocation[h.sector] += h.market_value

        if holdings_value > 0:
            sector_allocation = {
                k: round(v / holdings_value * 100, 2)
                for k, v in sector_allocation.items()
            }

        # Weight per holding (of total portfolio including cash)
        holdings_with_weight = []
        for h in enriched:
            d = h.to_dict()
            d["weight_pct"] = round(h.market_value / total_value * 100, 2) if total_value > 0 else 0
            holdings_with_weight.append(d)

        return PortfolioSummary(
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=unrealized_pnl,
            total_pnl_pct=unrealized_pnl_pct,
            realized_pnl=realized_pnl,
            cash_balance=cash,
            holdings_value=holdings_value,
            holdings=holdings_with_weight,
            sector_allocation=sector_allocation,
            last_updated=datetime.now().isoformat(),
        )
