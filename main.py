"""
KerenEye — Equity Research Multi-Agent System

Entry point. Accepts a stock ticker and generates a full research report.

Usage:
    python main.py AAPL
    python main.py MSFT
"""

import os
import sys
from datetime import datetime

from data.collector import DataCollector
from crew.research_crew import run_research_crew
from config import OUTPUT_DIR


def main():
    # --- Parse ticker from CLI ---
    if len(sys.argv) < 2:
        print("\n  Usage: python main.py <TICKER>")
        print("  Example: python main.py AAPL\n")
        sys.exit(1)

    ticker = sys.argv[1].upper()

    print(r"""
    ╔═══════════════════════════════════════════════╗
    ║                                               ║
    ║   🔍  KerenEye Equity Research System  🔍     ║
    ║                                               ║
    ║   Multi-Agent AI Equity Research              ║
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
    """)

    # --- Step 1: Collect all data ---
    print("=" * 60)
    print("  PHASE 1: DATA COLLECTION")
    print("=" * 60)

    collector = DataCollector()
    company_data = collector.collect(ticker)

    if not company_data.name or company_data.name == ticker:
        print(f"\n❌ Could not find company data for ticker '{ticker}'.")
        print("   Please check the ticker symbol and try again.\n")
        sys.exit(1)

    # --- Step 2: Run analysis agents ---
    print("\n" + "=" * 60)
    print("  PHASE 2: AI ANALYSIS")
    print("=" * 60)

    report = run_research_crew(company_data)

    # --- Step 3: Save report ---
    print("\n" + "=" * 60)
    print("  PHASE 3: REPORT OUTPUT")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ticker}_report_{timestamp}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w") as f:
        f.write(report)

    print(f"\n  ✅ Report saved to: {filepath}")
    print(f"  📊 Report length: {len(report):,} characters")

    # Also print to console
    print("\n" + "=" * 60)
    print("  FULL REPORT")
    print("=" * 60 + "\n")
    print(report)

    return report


if __name__ == "__main__":
    main()
