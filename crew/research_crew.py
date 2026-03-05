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
            "Assess the current market sentiment around the company by "
            "analyzing recent news, analyst recommendations, and identifying "
            "key catalysts or risks."
        ),
        backstory=(
            "You are a market intelligence analyst who monitors news flow and "
            "analyst sentiment. You can quickly distinguish between noise and "
            "signal, identify emerging themes, and assess how the market is "
            "positioning around a stock."
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
            "Analyze the company's competitive position within its industry, "
            "identify its economic moat, assess industry dynamics, and provide "
            "a SWOT analysis."
        ),
        backstory=(
            "You are a sector analyst with deep knowledge of industry dynamics "
            "across all major sectors. You understand Porter's Five Forces, "
            "competitive moats, industry life cycles, and macroeconomic "
            "impacts. You can assess a company's strategic position with "
            "limited data by leveraging your broad industry knowledge."
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

Provide a comprehensive sentiment analysis covering:
1. News Flow: What is the primary narrative driving the stock in the news right now? (e.g., cost-cutting, AI growth, regulatory fears).
2. Analyst Positioning: Summarize the distribution of Buy/Hold/Sell ratings. Are analysts overwhelmingly bullish, or is there skepticism?
3. Catalysts: Identify 2 specific upside catalysts that could drive the stock higher in the next 6-12 months.
4. Risks: Identify 2 specific downside risks.

Format your response as a concise sentiment analysis section.
""",
        agent=agents["sentiment"],
        expected_output="Market sentiment summary with identified catalysts, risks, and news narratives.",
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
Analyze the competitive position and industry dynamics for {data.name} ({data.ticker}).

COMPANY PROFILE:
{format_company_profile(data)}

PEER COMPANIES:
{format_peer_comparison(data)}

MACROECONOMIC CONTEXT:
{format_macro(data)}

Provide a comprehensive industry and competitive analysis covering:
1. Economic Moat: Assess the company's competitive advantage. Does it have a wide, narrow, or no moat? (Consider brand, switching costs, network effects, cost advantages).
2. Competitive Position: How does the company compare to the peers listed in terms of scale (Market Cap) and efficiency (Margins)?
3. Macro Impact: How do the current macroeconomic conditions (like the current Fed Funds rate or GDP) impact this specific industry and company?
4. Key Industry Trends: What structural tailwinds or headwinds is the sector facing?

Format your response as an industry analysis section for an equity research report.
""",
        agent=agents["industry"],
        expected_output="An industry deep dive evaluating the company's economic moat, competitive scale, and macro sensitivity.",
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

## Company Overview
Brief company description, sector, industry, and market cap.

## Financial Analysis
[Integrate the financial analyst's findings. Use bullet points for strengths/risks.]

## Valuation Analysis  
[Integrate the valuation specialist's findings regarding premiums/discounts.]

## Technical Analysis
[Integrate the technical analyst's findings.]

## Market Sentiment & Catalysts
[Integrate the sentiment analyst's findings regarding catalysts and risks.]

## Industry & Competitive Position
[Integrate the industry analyst's findings regarding the economic moat.]

## Investment Thesis Summary
Provide a final, definitive 3-bullet summary of why this stock is a Buy, Hold, or Sell. 

---
*Report generated by KerenEye Equity Research System*
*Date: {datetime.now().strftime('%Y-%m-%d')}*

IMPORTANT: 
- Be brutal as an editor. Remove any repetitive introductory phrases from the analysts (like "Based on the data provided...").
- Keep the formatting hyper-clean with Markdown headers and bullet points.
- The tone must be authoritative and objective.
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
