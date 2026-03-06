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

## Tech Stack & Tooling Rationale

The KerenEye system is separated into a Python backend (for heavy AI processing) and a modern React frontend (for presentation).

### Backend (Python & AI)

- **[CrewAI](https://crewai.com)**: Used as the core Multi-Agent orchestration framework. 
  - *Why CrewAI?* Instead of relying on a single massive LLM prompt (which often hallucinates or loses detail), CrewAI allows us to break down complex financial analysis into distinct personas (e.g., Financial Analyst, Technical Analyst). By running these specialized agents in parallel with specific tools and focused goals, we get a much deeper, more accurate, and nuanced final report.
- **[FastAPI](https://fastapi.tiangolo.com/)**: Serves as the Python backend framework connecting the CLI core to the web app.
  - *Why FastAPI?* It is lightweight, incredibly fast, and natively supports asynchronous execution (`async`/`await`), which is crucial for running background CrewAI tasks and streaming status updates to the frontend without blocking the main server.
- **[yfinance](https://github.com/ranaroussi/yfinance)**: Financial data from Yahoo Finance.
  - *Why yfinance?* It is free, requires no API key, and provides reliable, comprehensive historical price data, financial statements, and basic corporate metadata.
- **[Finnhub](https://finnhub.io)**: Peer discovery and professional market news.
- **[FRED API](https://fred.stlouisfed.org)**: Macroeconomic data (interest rates, GDP).
- **[OpenAI GPT](https://openai.com)**: The underlying LLM backbone powering the CrewAI agents.

### Frontend (React & Vite)

- **[React](https://react.dev/) + [Vite](https://vitejs.dev/)**: The core UI framework.
  - *Why React/Vite?* React handles the complex state management required for building interactive dashboards (like syncing the 3D background with the loading status). Vite provides near-instant Hot Module Replacement (HMR) for incredibly fast development.
- **[Tailwind CSS](https://tailwindcss.com/)**: For styling.
  - *Why Tailwind?* It allows for rapid, utility-first styling to create the premium, glassmorphic "Advisory Intelligence" aesthetic strictly through standardized classes, avoiding messy external CSS files.
- **[Recharts](https://recharts.org/)**: For charting equity performance.
  - *Why Recharts?* It renders beautiful, responsive SVG charts that integrate cleanly with React state and can easily inherit Tailwind theme colors.
- **[@react-three/fiber](https://docs.pmnd.rs/react-three-fiber)**: For the 3D particle network background.
  - *Why Three.js?* It provides the premium, dynamic, and interactive "data network" visual that signals high-end institutional software.

## Operational Process: How the App Works

The operational flow of the KerenEye application is strictly built to ensure accuracy, speed, and real-time user feedback.

1. **User Request**: The user enters a stock ticker (e.g., "AAPL") into the React frontend search bar and hits enter.
2. **Instant Pre-fetch (Synchronous)**: The frontend immediately hits the backend `GET /api/company/{ticker}` endpoint. The backend synchronously uses `yfinance` to grab the company's current price, market cap, basic ratios, and historical price data. This data is returned instantly to paint the primary React dashboard and the Recharts historical chart so the user isn't left staring at a blank screen.
3. **Agent Orchestration (Asynchronous)**: Simultaneously, the frontend hits `GET /api/research/{ticker}`. This triggers the heavy lifting. The backend initializes a `Crew` of 6 distinct AI personas (Agents).
4. **Data Injection**: The raw data collected earlier is cleanly formatted into string contexts and injected into the specific Tasks assigned to each Agent. *Crucially, we do not let the LLM browse the live internet for data, preventing hallucination. We feed it strictly defined, factual data gathered by Python.*
5. **Concurrent Execution**: The first 5 agents (Financial Analyst, Valuation Specialist, Sentiment Analyst, Technical Analyst, Industry Analyst) execute their assigned tasks **simultaneously in parallel**. This vastly speeds up report generation time.
6. **Real-Time Progress Tracking (Polling)**: While the agents run, the React frontend polls `GET /api/research/status/{ticker}` every second. As tasks finish on the backend, a global status dictionary is updated, which the frontend reads to animate the beautiful, step-by-step loading stepper dynamically.
7. **Synthesis & Finalization**: Once the 5 parallel analysts finish, the 6th agent (the Report Writer) activates. It ingests all 5 outputs and synthesizes them into a cohesive, properly formatted Markdown equity research report.
8. **Rendering**: The backend returns the final Markdown string to the frontend, which is rendered using `react-markdown` in the Executive Dossier panel.
