"""Shared in-memory state for local single-process API usage."""

from portfolio.manager import PortfolioManager


company_data_cache: dict[str, object] = {}
research_task_status: dict[str, str] = {}
news_task_status: dict[str, str] = {}
brief_task_status = {"status": "Not Started"}
portfolio_news_task_status = {"status": "Idle"}
portfolio_manager = PortfolioManager()
