"""
Research Crew — CrewAI multi-agent orchestration for equity research.

This module defines the 6 analysis agents and the report writer,
configures their tasks, and runs them against the collected data.
"""

from datetime import datetime
from crewai import Agent, Crew, Task, Process

from data.collector import (
    CompanyData,
    format_company_profile,
    format_financial_statements,
    format_ratios,
    format_peer_comparison,
    format_news,
    format_macro,
)
from tools.technical_tools import compute_technical_indicators, format_technical_summary
from config import OPENAI_MODEL_NAME


# ---------------------------------------------------------------------------
# Agent Definitions
# ---------------------------------------------------------------------------

def _create_agents() -> dict:
    """Create all analysis agents. Returns dict keyed by role."""

    financial_analyst = Agent(
        role="Senior Financial Analyst",
        goal=(
            "Analyze the company's financial statements and key ratios to "
            "identify trends, strengths, weaknesses, and red flags in its "
            "financial performance."
        ),
        backstory=(
            "You are a seasoned equity research analyst with 15 years of "
            "experience at a top-tier investment bank. You specialize in "
            "fundamental analysis and can quickly identify financial trends, "
            "margin pressures, earnings quality issues, and balance sheet "
            "risks. You communicate findings clearly and concisely."
        ),
        verbose=False,
        allow_delegation=False,
        llm=OPENAI_MODEL_NAME,
    )

    valuation_analyst = Agent(
        role="Valuation Specialist",
        goal=(
            "Determine whether the stock is fairly valued, overvalued, or "
            "undervalued by analyzing valuation multiples, peer comparisons, "
            "and analyst consensus targets."
        ),
        backstory=(
            "You are a valuation expert who has built hundreds of DCF models "
            "and comparable company analyses. You understand that valuation is "
            "both art and science — you combine quantitative multiples with "
            "qualitative judgment about growth prospects and risk."
        ),
        verbose=False,
        allow_delegation=False,
        llm=OPENAI_MODEL_NAME,
    )

    sentiment_analyst = Agent(
        role="Market Sentiment Analyst",
        goal=(
            "Assess the prevailing market narrative, but more importantly, "
            "synthesize the absolute strongest Bull Case and the most devastating "
            "Bear Case currently debated by institutional investors."
        ),
        backstory=(
            "You are a contrarian market intelligence analyst. You ignore surface-level "
            "noise and focus on the core existential debates surrounding a company. "
            "You understand how shifting sentiment, regulatory fears, or technological "
            "breakthroughs (like GenAI) can destroy or double a stock's value overnight."
        ),
        verbose=False,
        allow_delegation=False,
        llm=OPENAI_MODEL_NAME,
    )

    technical_analyst = Agent(
        role="Technical Analyst",
        goal=(
            "Analyze price action and technical indicators to identify trends, "
            "momentum, support/resistance levels, and potential entry/exit points."
        ),
        backstory=(
            "You are a chartered market technician (CMT) with deep expertise "
            "in price action analysis. You use moving averages, RSI, MACD, "
            "Bollinger Bands, and volume analysis to form a complete technical "
            "picture. You explain technical concepts in plain language."
        ),
        verbose=False,
        allow_delegation=False,
        llm=OPENAI_MODEL_NAME,
    )

    industry_analyst = Agent(
        role="Industry & Competitive Analyst",
        goal=(
            "Analyze the company's competitive moat and identify massive structural "
            "shifts, technological disruptions (e.g., AI), or regulatory threats that "
            "could render the company's business model obsolete."
        ),
        backstory=(
            "You are a ruthless tech and sector analyst. You do not just look at "
            "current market share; you look at what will destroy this company in 5 years. "
            "If a software company is facing GenAI disruption (like Adobe vs Midjourney) "
            "or an automaker is facing EV price wars, you surface it immediately. You pull no punches."
        ),
        verbose=False,
        allow_delegation=False,
        llm=OPENAI_MODEL_NAME,
    )

    report_writer = Agent(
        role="Senior Research Editor",
        goal=(
            "Compile all analysis sections into a cohesive, professional "
            "equity research report with an executive summary and clear "
            "investment recommendation."
        ),
        backstory=(
            "You are the head of equity research publications. You transform "
            "individual analyst contributions into polished, Wall Street-grade "
            "research reports. You ensure consistency, add an executive summary "
            "with a clear investment thesis, and provide a final Buy/Hold/Sell "
            "recommendation with a confidence level."
        ),
        verbose=False,
        allow_delegation=False,
        llm=OPENAI_MODEL_NAME,
    )

    return {
        "financial": financial_analyst,
        "valuation": valuation_analyst,
        "sentiment": sentiment_analyst,
        "technical": technical_analyst,
        "industry": industry_analyst,
        "report_writer": report_writer,
    }


# ---------------------------------------------------------------------------
# Task Definitions
# ---------------------------------------------------------------------------

def _create_tasks(agents: dict, data: CompanyData) -> list:
    """Create all analysis tasks with the collected data injected as context."""

    # Pre-compute technical indicators (No more chart generation)
    tech_indicators = compute_technical_indicators(data.price_history)
    tech_summary = format_technical_summary(tech_indicators)

    # --- Analysis Tasks ---

    financial_task = Task(
        description=f"""
Analyze the financial performance of {data.name} ({data.ticker}).

COMPANY PROFILE:
{format_company_profile(data)}

FINANCIAL DATA (Last 5 Years):
{format_financial_statements(data)}

KEY RATIOS:
{format_ratios(data)}

Provide a deep, Wall Street-grade financial analysis covering:
1. Revenue trends: Calculate and explicitly state the Year-over-Year (YoY) growth/decline over the available periods.
2. Profitability: Analyze gross, operating, and net margins. State explicitly if they are *expanding* or *contracting* and why.
3. Balance sheet health: Assess leverage and liquidity (mention the Debt/Equity and Current Ratios).
4. Cash flow: Assess the quality of earnings by comparing Net Income to Operating Cash Flow.
5. Key takeaways: Bullet point 2 financial strengths and 2 risks.

Format your response as a rigorous, data-driven analysis section. Use specific numbers to justify every claim.
""",
        agent=agents["financial"],
        expected_output="A quantitative financial analysis with YoY comparisons and margin trend analysis.",
    )

    valuation_task = Task(
        description=f"""
Assess the valuation of {data.name} ({data.ticker}).

KEY RATIOS:
{format_ratios(data)}

PEER COMPARISON:
{format_peer_comparison(data)}

ANALYST TARGETS:
{data.analyst_targets}

CURRENT PRICE: ${data.current_price:.2f}
MARKET CAP: ${data.market_cap:,.0f}

Provide a deep, rigorous valuation analysis covering:
1. Multiples Analysis: What are the current P/E, EV/EBITDA, and P/B multiples implying about future growth expectations?
2. Peer Analysis: Calculate and explicitly state whether the stock trades at a **premium** or **discount** to its peer average (e.g., "Trading at a 20% premium to peers on a P/E basis"). Justify whether this premium/discount is deserved based on its margins/ROE.
3. Analyst Consensus: What is the implied upside/downside percentage to the mean Wall Street target?
4. Final Verdict: Is the stock fairly valued, overvalued, or undervalued?

Format your response as a professional valuation section for an institutional report.
""",
        agent=agents["valuation"],
        expected_output="A comprehensive valuation assessment with explicit premium/discount calculations against peers.",
    )

    sentiment_task = Task(
        description=f"""
Analyze the market sentiment for {data.name} ({data.ticker}).

RECENT NEWS:
{format_news(data)}

ANALYST RECOMMENDATIONS:
{data.recommendations.to_string() if data.recommendations is not None and not data.recommendations.empty else 'Not available'}

Provide a rigorous Bull/Bear analysis covering:
1. The Core Narrative: What is the primary existential debate driving the stock right now?
2. The Ultimate Bull Case: If everything goes right for this company over the next 3 years, why will the stock double?
3. The Devastating Bear Case: What is the most likely reason this stock collapses? (Be highly specific, not general).
4. Analyst Consensus Breakdown: Provide a quick summary of the Wall St ratings.

Format your response as a deep, opinionated sentiment analysis.
""",
        agent=agents["sentiment"],
        expected_output="An aggressive presentation of the ultimate Bull and Bear cases dominating market sentiment.",
    )

    technical_task = Task(
        description=f"""
Analyze the technical profile of {data.name} ({data.ticker}).

TECHNICAL INDICATORS (Calculated over {len(data.price_history) if data.price_history is not None else 'N/A'} trading days):
{tech_summary}

Provide a comprehensive technical analysis covering:
1. Primary Trend: Identify the dominant trend (Uptrend, Downtrend, or Consolidation) using the relationship between the price and the 200-day 50-day MAs.
2. Momentum: Interpret the RSI and MACD. Is the stock overbought, oversold, or displaying bearish/bullish divergence?
3. Volatility & Levels: Note the Bollinger Band positioning and the current Support/Resistance levels.
4. Final Outlook: Provide a definitive Bullish, Bearish, or Neutral rating for the technical setup.

Write in plain language that fundamental investors can understand, avoiding overly esoteric chart jargon.
""",
        agent=agents["technical"],
        expected_output="A clean technical analysis defining the trend, momentum, and key price levels.",
    )

    industry_task = Task(
        description=f"""
Analyze the existential competitive position and structural threats for {data.name} ({data.ticker}).

COMPANY PROFILE:
{format_company_profile(data)}

PEER COMPANIES:
{format_peer_comparison(data)}

MACROECONOMIC CONTEXT:
{format_macro(data)}

Provide a ruthless industry disruption analysis covering:
1. The Economic Moat: Assess the current moat, but more importantly, determine if that moat is currently *expanding* or *decaying*.
2. Structural Threats (Crucial): What is the biggest structural or technological threat to this business model? (e.g., Generative AI disruption, GLP-1 drugs for food companies, EV adoption for legacy auto). You must identify at least one major existential threat.
3. Peer Warfare: How is the company positioned against the specific competitors listed? Who is hunting them?
4. Macro Sensitivity: How sensitive are they to the current interest rate or geopolitical environment?

Format your response as a highly critical structural threat analysis.
""",
        agent=agents["industry"],
        expected_output="A ruthless deep-dive evaluating structural, technological, and existential threats to the company's business model.",
    )

    # --- Report compilation ---

    report_task = Task(
        description=f"""
You are the Senior Research Editor compiling the final equity research report for {data.name} ({data.ticker}).

You have received analysis from five specialist analysts. Compile their work into 
a cohesive, professional equity research report.

The report MUST follow this exact structure:

# Equity Research Report: {data.name} ({data.ticker})

## Executive Summary
Write a compelling 2-3 paragraph executive summary that synthesizes the most critical data points from the analysts.
- Conclude with a clear **BUY / HOLD / SELL** recommendation with a confidence level (High/Medium/Low).

## The Bull & The Bear Case
Be incredibly aggressive and specific here based on the sentiment analyst.
- **The Bull Case:** [Detail the massive upside catalyst]
- **The Bear Case:** [Detail the devastating downside scenario]

## Structural & Technological Threats
[Integrate the industry analyst's findings regarding AI disruption, moat decay, and existential, business-ending threats. Do NOT sugarcoat this section.]

## Financial & Valuation Analysis
[Integrate the financial and valuation findings. Provide precise margin trends and peer premium/discount multiples.]

## Technical Outlook
[Integrate the technical analyst's findings concisely.]

## Investment Thesis Summary
Provide a final, definitive 3-bullet summary of why this stock is a Buy, Hold, or Sell. 

---
*Report generated by KerenEye Equity Research System*
*Date: {datetime.now().strftime('%Y-%m-%d')}*

IMPORTANT: 
- Be ruthless and highly opinionated. Institutional investors want to know what destroys the company.
- You must explicitly address Generative AI or equivalent structural tech shifts if the company is in software/tech/services. 
- Keep the formatting hyper-clean with Markdown headers and bullet points.
- The tone must be authoritative, objective, and deep.
""",
        agent=agents["report_writer"],
        expected_output="The final, polished equity research report.",
        context=[
            financial_task,
            valuation_task,
            sentiment_task,
            technical_task,
            industry_task,
        ],
    )

    return [
        financial_task,
        valuation_task,
        sentiment_task,
        technical_task,
        industry_task,
        report_task,
    ]


# ---------------------------------------------------------------------------
# Crew Runner
# ---------------------------------------------------------------------------

def run_research_crew(data: CompanyData) -> str:
    """
    Run the full equity research crew on the collected data.

    Returns the final report as a string.
    """
    print("\n🤖 Initializing research crew...\n")

    agents = _create_agents()
    tasks = _create_tasks(agents, data)

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,  # Tasks run in order; report_writer goes last
        verbose=True,
    )

    print("🚀 Running analysis agents...\n")
    result = crew.kickoff()

    return str(result)
