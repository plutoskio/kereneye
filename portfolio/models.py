"""
Portfolio Data Models — Dataclasses for holdings, transactions, and summaries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Holding:
    """A single stock holding in the portfolio."""
    ticker: str
    shares: float
    avg_cost: float  # Average purchase price per share
    date_added: str = ""  # ISO format string

    @property
    def total_cost(self) -> float:
        return self.shares * self.avg_cost

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "shares": self.shares,
            "avg_cost": self.avg_cost,
            "date_added": self.date_added,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Holding":
        return cls(
            ticker=d["ticker"],
            shares=d["shares"],
            avg_cost=d["avg_cost"],
            date_added=d.get("date_added", ""),
        )


@dataclass
class Transaction:
    """A buy or sell transaction log entry."""
    ticker: str
    type: str  # "buy" or "sell"
    shares: float
    price: float
    timestamp: str = ""  # ISO format string
    realized_pnl: float = 0.0  # P&L on this transaction (sell only)

    @property
    def total_value(self) -> float:
        return self.shares * self.price

    def to_dict(self) -> dict:
        d = {
            "ticker": self.ticker,
            "type": self.type,
            "shares": self.shares,
            "price": self.price,
            "timestamp": self.timestamp,
        }
        if self.type == "sell":
            d["realized_pnl"] = round(self.realized_pnl, 2)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        return cls(
            ticker=d["ticker"],
            type=d["type"],
            shares=d["shares"],
            price=d["price"],
            timestamp=d.get("timestamp", ""),
            realized_pnl=d.get("realized_pnl", 0.0),
        )


@dataclass
class EnrichedHolding:
    """A holding enriched with live market data for API responses."""
    ticker: str
    name: str
    sector: str
    shares: float
    avg_cost: float
    current_price: float
    date_added: str

    @property
    def total_cost(self) -> float:
        return self.shares * self.avg_cost

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def pnl(self) -> float:
        return self.market_value - self.total_cost

    @property
    def pnl_pct(self) -> float:
        if self.total_cost == 0:
            return 0.0
        return (self.pnl / self.total_cost) * 100

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "sector": self.sector,
            "shares": self.shares,
            "avg_cost": round(self.avg_cost, 2),
            "current_price": round(self.current_price, 2),
            "total_cost": round(self.total_cost, 2),
            "market_value": round(self.market_value, 2),
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "date_added": self.date_added,
        }


@dataclass
class PortfolioSummary:
    """Aggregate portfolio summary with P&L, allocation, and cash."""
    total_value: float = 0.0        # Holdings market value + cash
    total_cost: float = 0.0
    total_pnl: float = 0.0          # Unrealized P&L
    total_pnl_pct: float = 0.0
    realized_pnl: float = 0.0       # Realized P&L from sells
    cash_balance: float = 0.0
    holdings_value: float = 0.0     # Market value of holdings only
    holdings: list[dict] = field(default_factory=list)
    sector_allocation: dict = field(default_factory=dict)
    last_updated: str = ""

    def to_dict(self) -> dict:
        return {
            "total_value": round(self.total_value, 2),
            "total_cost": round(self.total_cost, 2),
            "total_pnl": round(self.total_pnl, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "cash_balance": round(self.cash_balance, 2),
            "holdings_value": round(self.holdings_value, 2),
            "holdings_count": len(self.holdings),
            "holdings": self.holdings,
            "sector_allocation": self.sector_allocation,
            "last_updated": self.last_updated,
        }
