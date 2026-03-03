# 🔍 KerenEye — Equity Research Multi-Agent System

An AI-powered equity research system that generates comprehensive research reports for any publicly traded company. Enter a stock ticker and receive a Wall Street-grade analysis in minutes.

## Architecture

KerenEye uses a **Hub-and-Spoke multi-agent architecture** powered by [CrewAI](https://crewai.com):

```
User enters ticker (e.g., "AAPL")
         │
         ▼
┌─────────────────────────────────────┐
│   ORCHESTRATOR (pure Python)        │
│                                     │
│   1. yfinance  → financials, prices │
│   2. Finnhub   → peer discovery     │
│   3. FRED      → macro indicators   │
└─────┬───┬───┬───┬───┬──────────────┘
      │   │   │   │   │
      ▼   ▼   ▼   ▼   ▼
    [FA] [VA] [SA] [TA] [IA]   ← 5 LLM Analysis Agents
      │   │   │   │   │
      └───┴───┴───┴───┘
              │
              ▼
       [Report Writer]  ← Compiles final report
              │
              ▼
        📄 Research Report
```

### Key Design Decisions

- **Deterministic Orchestrator**: Data collection is pure Python — no LLM non-determinism in the control flow
- **LLM Agents for Analysis Only**: Agents are used only where reasoning/interpretation is needed
- **Single Data Pass**: All data fetched once, distributed to agents — no redundant API calls
- **Free Data Pipeline**: yfinance + Finnhub + FRED — all 100% free

### The Agents

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Financial Analyst** | Fundamental analysis | Financial statements, ratios | Revenue trends, margins, balance sheet health |
| **Valuation Specialist** | Fair value assessment | Ratios, peer multiples, targets | Over/undervalued assessment, peer comparison |
| **Sentiment Analyst** | Market intelligence | News, analyst ratings | Sentiment score, catalysts, risks |
| **Technical Analyst** | Price action analysis | OHLCV data, indicators | Trend, momentum, support/resistance, chart |
| **Industry Analyst** | Competitive analysis | Company profile, peers, macro | Moat analysis, SWOT, industry dynamics |
| **Report Writer** | Final compilation | All agent outputs | Professional equity research report |

## Data Sources

| Source | Cost | What It Provides |
|--------|------|------------------|
| **yfinance** | Free (no key needed) | Financial statements, prices, ratios, news, analyst targets |
| **Finnhub** | Free (API key) | Peer/competitor ticker discovery |
| **FRED** | Free (API key) | Macroeconomic indicators (GDP, rates, inflation) |

## Setup

### 1. Clone & Install

```bash
cd kereneye
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` and add your keys:
- **OpenAI API key** (required) — for the LLM agents
- **Finnhub API key** (optional) — get free at [finnhub.io](https://finnhub.io/register)
- **FRED API key** (optional) — get free at [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html)

> The system works without Finnhub/FRED keys — it will skip peer comparison and macro data.

### 3. Run

```bash
python main.py AAPL
```

The report will be saved to `output/reports/` as a Markdown file.

## Output

Each report includes:

1. **Executive Summary** — Investment thesis + Buy/Hold/Sell recommendation
2. **Company Overview** — Business description, key facts
3. **Financial Analysis** — Revenue trends, margins, balance sheet, cash flow
4. **Valuation Analysis** — Multiples, peer comparison, fair value
5. **Technical Analysis** — Price trends, indicators, support/resistance, chart
6. **Market Sentiment** — News, analyst consensus, catalysts/risks
7. **Industry & Competitive Analysis** — Moat, SWOT, industry dynamics
8. **Risk Factors** — Consolidated risks
9. **Investment Recommendation** — Final rating with confidence level

## Project Structure

```
kereneye/
├── main.py                    # CLI entry point
├── config.py                  # API keys & settings
├── requirements.txt           # Dependencies
├── .env.example               # API key template
│
├── data/
│   └── collector.py           # Data orchestrator (yfinance, Finnhub, FRED)
│
├── agents/                    # Agent module (defined in crew/)
│
├── tools/
│   ├── technical_tools.py     # RSI, MACD, MA, Bollinger, volatility
│   └── chart_tools.py         # Price chart generation
│
├── crew/
│   └── research_crew.py       # CrewAI agents, tasks, and crew runner
│
└── output/
    └── reports/               # Generated reports
```

## Tech Stack

- **[CrewAI](https://crewai.com)** — Multi-agent orchestration framework
- **[yfinance](https://github.com/ranaroussi/yfinance)** — Financial data from Yahoo Finance
- **[Finnhub](https://finnhub.io)** — Peer company discovery
- **[FRED API](https://fred.stlouisfed.org)** — Macroeconomic data
- **[matplotlib](https://matplotlib.org)** — Technical chart generation
- **[OpenAI GPT](https://openai.com)** — LLM backbone for analysis agents
