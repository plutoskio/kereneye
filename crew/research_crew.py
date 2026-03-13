"""
Research Crew — CrewAI multi-agent orchestration for equity research.

This module defines the 6 analysis agents and the report writer,
configures their tasks, and runs them against the collected data.
"""

from datetime import datetime
from crewai import Agent, Crew, Task, Process

from data.collector import (
    CompanyData,
    MarketBriefData,
    format_company_profile,
    format_financial_statements,
    format_ratios,
    format_peer_comparison,
    format_news,
    format_premium_news,
    format_macro,
    format_market_brief_context,
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
            "Determine the brutal truth about whether a stock is fairly valued, "
            "overvalued, or undervalued. You must explicitly call out if Wall Street "
            "consensus targets are disconnected from fundamental reality."
        ),
        backstory=(
            "You are a highly contrarian valuation expert who has built hundreds of DCF models. "
            "You despise momentum-chasing and are fundamentally disciplined. You are NEVER afraid "
            "to disagree with Wall Street analysts. If a stock trades at an egregious premium "
            "with deteriorating fundamentals, you will aggressively label it as Overvalued."
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

    recent_news_analyst = Agent(
        role="Senior News Correspondent",
        goal=(
            "Read recent premium news articles from the last 7 days and identify "
            "the core signals while filtering out all the noise and clickbait. "
            "Explain exactly what happened and predict its immediate effect on the stock."
        ),
        backstory=(
            "You are a highly respected, no-nonsense financial journalist. "
            "You hate fluff, clickbait, and aggregated noise. When you read news, "
            "you instantly extract the actual impact on revenue, margins, or market share. "
            "You distill 10 articles down into the 2 or 3 events that actually matter."
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
        "recent_news": recent_news_analyst,
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
        async_execution=True,
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
        async_execution=True,
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
        async_execution=True,
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
        async_execution=True,
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
        async_execution=True,
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
- Do NOT be a cheerleader. If the valuation analysis indicates the stock is egregiously overvalued, you MUST explicitly disagree with optimistic Wall Street consensus targets.
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


def _create_news_tasks(agents: dict, data: CompanyData) -> list:
    """Create the isolated task for the News Analyst."""

    recent_news_task = Task(
        description=f"""
Analyze the recent premium news coverage for {data.name} ({data.ticker}).

RECENT PREMIUM NEWS (Last 7 Days):
{format_premium_news(data)}

Provide a highly concise and actionable news briefing:
1. Signal vs Noise: Filter out routine press releases and focus ONLY on material catalysts (e.g., earnings, M&A, executive departures, major product launches, downgrades/upgrades).
2. Primary Events: Summarize the 2 to 3 most important events that occurred in the last week.
3. Projected Impact: Explain clearly and directly how these events are affecting or will affect the stock price in the near term.

Format your response exactly as follows:
### Recent Catalysts
- [Bullet points of events]

### Stock Impact
[1-2 paragraph explanation of the effect on the stock]

Do NOT include generic company profiling or financial ratios. Focus solely on the news provided. If there is absolutely no premium news available, explicitly state: "No material news detected in the last 7 days."
""",
        agent=agents["recent_news"],
        expected_output="A concise brief summarizing material news catalysts from the past 7 days and their immediate impact on the stock.",
    )

    return [recent_news_task]

# ---------------------------------------------------------------------------
# Portfolio News Digest
# ---------------------------------------------------------------------------

def _create_portfolio_news_tasks(agents: dict, portfolio_news_str: str) -> list:
    """Create the task for the Portfolio Manager to analyze all holdings' news."""
    
    pm_strategist = Agent(
        role="Chief Portfolio Strategist",
        goal=(
            "Review the aggregated news across the entire portfolio and provide a deeply insightful, "
            "reflective analysis on how these events structurally impact the holdings. Identify "
            "hidden risks, compounding catalysts, and broader macro implications."
        ),
        backstory=(
            "You are a legendary hedge fund portfolio manager. You filter out algorithmic noise "
            "and focus on existential shifts. You don't just regurgitate the news; you reflect on "
            "what it means for the business model, the moat, and the sector. When a holding reports "
            "news, you instantly connect it to the bigger picture. You are ruthless, objective, and deeply insightful."
        ),
        verbose=False,
        allow_delegation=False,
        llm=OPENAI_MODEL_NAME,
    )

    pm_task = Task(
        description=f"""
You are the Chief Portfolio Strategist analyzing the recent news flow for the entire portfolio.

AGGREGATED RECENT NEWS FOR OPEN POSITIONS:
{portfolio_news_str}

Provide a deeply reflective and insightful impact report. Do NOT just list the headlines.
1. Distill the Noise: Filter out generic press releases, minor product updates, and clickbait.
2. The Real Story: What is the underlying theme or structural shift happening across these holdings? Are multiple companies in the portfolio facing similar macro/industry headwinds or tailwinds?
3. Price Confirmation: Use the supplied price-reaction context for each ticker. Call out when the market is validating the narrative, fading it, or reacting in the opposite direction of the headlines.
4. Impact Assessment: For the holdings with exactly material news, reflect on how this changes their long-term thesis or short-term volatility. Are their moats expanding or decaying because of this?

Format your response exactly as follows:
### Portfolio Wide Insights
[1-2 paragraphs reflecting on the broader themes or interconnected impacts across the holdings based on the news]

### Key Catalyst Breakdown
- **[TICKER]**: [Deep, insightful reflection on the specific news and what it actually means for the stock]
- **[TICKER]**: [Deep, insightful reflection on the specific news and what it actually means for the stock]

If there is no material news for the portfolio, state that the portfolio is operating under normal conditions with no immediate catalysts.
""",
        agent=pm_strategist,
        expected_output="An insightful, PM-level reflection on the structural impact of the recent holding news.",
    )

    return [pm_strategist, pm_task]

# ---------------------------------------------------------------------------
# Crew Runners
# ---------------------------------------------------------------------------

def run_research_crew(data: CompanyData, progress_callback=None) -> str:
    """
    Run the full equity research crew on the collected data.

    Returns the final report as a string.
    """
    print("\n🤖 Initializing research crew...\n")

    agents = _create_agents()
    tasks = _create_tasks(agents, data)

    stage_names = [
        "Analyzing Financials & Margins",
        "Running Valuation Models",
        "Assessing Market Sentiment",
        "Evaluating Technical Action",
        "Scanning for Industry Threats",
        "Drafting Executive Report",
        "Finalizing"
    ]
    completed_analyses = 0

    if progress_callback:
        progress_callback("Concurrent Analysis (0/5 completed)")

    def task_completed_cb(output):
        nonlocal completed_analyses
        completed_analyses += 1
        
        # Tasks 1-5 run in parallel. Task 6 is the report writer.
        if completed_analyses < 5 and progress_callback:
            progress_callback(f"Concurrent Analysis ({completed_analyses}/5 completed)")
        elif completed_analyses == 5 and progress_callback:
            progress_callback("Drafting Executive Report")

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,  # Tasks 1-5 will still run in parallel due to async_execution=True
        verbose=True,
        task_callback=task_completed_cb,
    )

    print("🚀 Running analysis agents...\n")
    result = crew.kickoff()

    return str(result)

def run_news_analysis_crew(data: CompanyData, progress_callback=None) -> str:
    """
    Run an isolated equity research crew just for recent news analysis.
    This runs asynchronously and independently of the main executive dossier.

    Returns the final news report as a string.
    """
    print("\n📰 Initializing news analysis crew...\n")

    agents = _create_agents()
    tasks = _create_news_tasks(agents, data)

    if progress_callback:
        progress_callback("Analyzing Premium News")

    def task_completed_cb(output):
        if progress_callback:
            progress_callback("Formatting Output")

    crew = Crew(
        agents=[agents["recent_news"]],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        task_callback=task_completed_cb,
    )

    print("🚀 Running news analyst...\n")
    result = crew.kickoff()

    return str(result)


def run_market_brief_crew(brief_data: MarketBriefData, progress_callback=None) -> str:
    """
    Run a standalone CrewAI agent that synthesizes the Daily Market & World Brief.
    Takes broad market data (indices, headlines, macro, world news) and produces
    a short, structured markdown summary.

    Returns the final brief as a markdown string.
    """
    print("\n🌍 Initializing market brief crew...\n")

    today = datetime.now().strftime("%B %d, %Y")

    # Format all collected data into a single context block
    context_block = format_market_brief_context(brief_data)

    if progress_callback:
        progress_callback("Analyzing Market Data")

    strategist = Agent(
        role="Chief Market Strategist",
        goal=(
            "Synthesize the latest market data, economic indicators, financial headlines, "
            "and world events into a concise, structured daily briefing that gives an investor "
            "a clear picture of what is happening right now and what to watch for."
        ),
        backstory=(
            "You are the Chief Market Strategist at a top-tier investment advisory firm. "
            "Every morning, your institutional clients rely on your briefing to understand "
            "the state of global markets. You are known for being concise, data-driven, "
            "and insightful — never vague or generic. You always reference specific numbers "
            "and specific events. Your tone is authoritative but accessible."
        ),
        verbose=False,
        allow_delegation=False,
        llm=OPENAI_MODEL_NAME,
    )

    brief_task = Task(
        description=f"""
You are writing the Daily Market & World Brief for {today}.

Using the data below, write a SHORT, structured briefing in markdown. 
The briefing MUST follow this exact structure:

## Market Pulse — {today}

**Markets:** [1-2 sentences on index performance. Reference specific indices and their % moves. Identify the main driver behind today's moves.]

**Macro:** [1-2 sentences on notable economic data or central bank activity. Reference specific numbers from the FRED data if relevant. If nothing notable, mention the current macro backdrop.]

**World:** [1-2 sentences on geopolitical events that could affect markets. Be specific about countries, conflicts, trade policies, elections, etc.]

**Outlook:** [1-2 sentences on what investors should watch for today/this week. Be actionable and specific.]

RULES:
- Keep the ENTIRE briefing under 200 words
- Reference SPECIFIC numbers (percentages, index levels, rates)
- Do NOT be vague or generic — every sentence must contain a concrete fact or insight
- Do NOT use bullet points — write in flowing prose
- Do NOT add any sections beyond the four above

=== RAW DATA ===
{context_block}
""",
        expected_output="A short, structured daily market brief in markdown format with exactly 4 sections: Markets, Macro, World, Outlook.",
        agent=strategist,
    )

    if progress_callback:
        progress_callback("Writing Daily Brief")

    def task_completed_cb(output):
        if progress_callback:
            progress_callback("Formatting Output")

    crew = Crew(
        agents=[strategist],
        tasks=[brief_task],
        process=Process.sequential,
        verbose=True,
        task_callback=task_completed_cb,
    )

    print("🚀 Running Chief Market Strategist...\n")
    result = crew.kickoff()

    return str(result)

def run_portfolio_news_crew(portfolio_news_str: str, progress_callback=None) -> str:
    """
    Run an isolated CrewAI agent to scan recent news across the entire portfolio
    and generate a reflective PM-level impact report.
    """
    print("\n📰 Initializing Portfolio News crew...\n")

    # Create dummy agents dict since _create_portfolio_news_tasks signature expects it
    agents = {} 
    pm_strategist, pm_task = _create_portfolio_news_tasks(agents, portfolio_news_str)

    if progress_callback:
        progress_callback("Synthesizing Portfolio News")

    def task_completed_cb(output):
        if progress_callback:
            progress_callback("Formatting PM Report")

    crew = Crew(
        agents=[pm_strategist],
        tasks=[pm_task],
        process=Process.sequential,
        verbose=True,
        task_callback=task_completed_cb,
    )

    print("🚀 Running Chief Portfolio Strategist...\n")
    result = crew.kickoff()

    return str(result)
