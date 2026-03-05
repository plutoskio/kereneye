"""
Technical analysis tools — compute indicators from price data.
"""

import pandas as pd
import numpy as np


def compute_technical_indicators(price_df: pd.DataFrame) -> dict:
    """
    Compute key technical indicators from OHLCV price data.

    Returns a dict with computed indicators and summary text.
    """
    if price_df is None or price_df.empty:
        return {"summary": "No price data available for technical analysis."}

    close = price_df["Close"]
    high = price_df["High"]
    low = price_df["Low"]
    volume = price_df["Volume"]

    indicators = {}

    # --- Moving Averages ---
    indicators["sma_20"] = close.rolling(20).mean().iloc[-1]
    indicators["sma_50"] = close.rolling(50).mean().iloc[-1]
    indicators["sma_200"] = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
    indicators["current_price"] = close.iloc[-1]

    # Golden/Death cross
    if pd.notna(indicators["sma_50"]) and pd.notna(indicators["sma_200"]):
        if indicators["sma_50"] > indicators["sma_200"]:
            indicators["ma_cross"] = "Golden Cross (bullish)"
        else:
            indicators["ma_cross"] = "Death Cross (bearish)"
    else:
        indicators["ma_cross"] = "Insufficient data"

    # Price vs MAs
    indicators["above_sma_50"] = close.iloc[-1] > indicators["sma_50"]
    indicators["above_sma_200"] = (
        close.iloc[-1] > indicators["sma_200"]
        if pd.notna(indicators["sma_200"])
        else None
    )

    # --- RSI (14-day) ---
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    indicators["rsi"] = rsi.iloc[-1]

    if indicators["rsi"] > 70:
        indicators["rsi_signal"] = "Overbought"
    elif indicators["rsi"] < 30:
        indicators["rsi_signal"] = "Oversold"
    else:
        indicators["rsi_signal"] = "Neutral"

    # --- MACD ---
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    indicators["macd"] = macd_line.iloc[-1]
    indicators["macd_signal"] = signal_line.iloc[-1]
    indicators["macd_histogram"] = macd_line.iloc[-1] - signal_line.iloc[-1]

    if indicators["macd"] > indicators["macd_signal"]:
        indicators["macd_trend"] = "Bullish (MACD above signal)"
    else:
        indicators["macd_trend"] = "Bearish (MACD below signal)"

    # --- Bollinger Bands ---
    sma_20 = close.rolling(20).mean()
    std_20 = close.rolling(20).std()
    indicators["bb_upper"] = (sma_20 + 2 * std_20).iloc[-1]
    indicators["bb_lower"] = (sma_20 - 2 * std_20).iloc[-1]
    indicators["bb_middle"] = sma_20.iloc[-1]

    if close.iloc[-1] > indicators["bb_upper"]:
        indicators["bb_signal"] = "Above upper band (potentially overbought)"
    elif close.iloc[-1] < indicators["bb_lower"]:
        indicators["bb_signal"] = "Below lower band (potentially oversold)"
    else:
        indicators["bb_signal"] = "Within bands (normal)"

    # --- Volume ---
    indicators["avg_volume_20d"] = volume.rolling(20).mean().iloc[-1]
    indicators["latest_volume"] = volume.iloc[-1]
    indicators["volume_trend"] = (
        "Above average" if volume.iloc[-1] > indicators["avg_volume_20d"]
        else "Below average"
    )

    # --- Price Performance ---
    indicators["price_change_1m"] = (
        (close.iloc[-1] / close.iloc[-21] - 1) if len(close) >= 21 else None
    )
    indicators["price_change_3m"] = (
        (close.iloc[-1] / close.iloc[-63] - 1) if len(close) >= 63 else None
    )
    indicators["price_change_6m"] = (
        (close.iloc[-1] / close.iloc[-126] - 1) if len(close) >= 126 else None
    )
    indicators["price_change_1y"] = (
        (close.iloc[-1] / close.iloc[0] - 1)
    )

    # --- 52-week High/Low ---
    indicators["high_52w"] = high.tail(252).max()
    indicators["low_52w"] = low.tail(252).min()
    indicators["pct_from_52w_high"] = close.iloc[-1] / indicators["high_52w"] - 1
    indicators["pct_from_52w_low"] = close.iloc[-1] / indicators["low_52w"] - 1

    # --- Volatility ---
    daily_returns = close.pct_change().dropna()
    indicators["volatility_30d"] = daily_returns.tail(30).std() * np.sqrt(252)
    indicators["volatility_1y"] = daily_returns.std() * np.sqrt(252)

    # --- Support / Resistance (simple: recent swing highs/lows) ---
    indicators["support"] = low.tail(20).min()
    indicators["resistance"] = high.tail(20).max()

    return indicators


def format_technical_summary(indicators: dict) -> str:
    """Format technical indicators into readable text for LLM agent."""
    if "summary" in indicators:
        return indicators["summary"]

    lines = ["=== TECHNICAL ANALYSIS DATA ==="]

    price = indicators.get("current_price", 0)
    lines.append(f"\n  Current Price: ${price:.2f}")
    lines.append(f"  52-Week High: ${indicators.get('high_52w', 0):.2f} "
                 f"({indicators.get('pct_from_52w_high', 0):.1%} from high)")
    lines.append(f"  52-Week Low: ${indicators.get('low_52w', 0):.2f} "
                 f"({indicators.get('pct_from_52w_low', 0):.1%} from low)")

    lines.append(f"\n  --- Moving Averages ---")
    lines.append(f"  SMA 20: ${indicators.get('sma_20', 0):.2f}")
    lines.append(f"  SMA 50: ${indicators.get('sma_50', 0):.2f} "
                 f"(price {'above' if indicators.get('above_sma_50') else 'below'})")
    if indicators.get("sma_200"):
        lines.append(f"  SMA 200: ${indicators['sma_200']:.2f} "
                     f"(price {'above' if indicators.get('above_sma_200') else 'below'})")
    lines.append(f"  MA Cross: {indicators.get('ma_cross', 'N/A')}")

    lines.append(f"\n  --- Momentum ---")
    lines.append(f"  RSI (14): {indicators.get('rsi', 0):.1f} → "
                 f"{indicators.get('rsi_signal', 'N/A')}")
    lines.append(f"  MACD: {indicators.get('macd', 0):.4f} → "
                 f"{indicators.get('macd_trend', 'N/A')}")

    lines.append(f"\n  --- Bollinger Bands ---")
    lines.append(f"  Upper: ${indicators.get('bb_upper', 0):.2f} | "
                 f"Middle: ${indicators.get('bb_middle', 0):.2f} | "
                 f"Lower: ${indicators.get('bb_lower', 0):.2f}")
    lines.append(f"  Signal: {indicators.get('bb_signal', 'N/A')}")

    lines.append(f"\n  --- Performance ---")
    for label, key in [("1 Month", "price_change_1m"),
                       ("3 Months", "price_change_3m"),
                       ("6 Months", "price_change_6m"),
                       ("1 Year", "price_change_1y")]:
        val = indicators.get(key)
        if val is not None:
            lines.append(f"  {label}: {val:.1%}")

    lines.append(f"\n  --- Volatility ---")
    lines.append(f"  30-Day Annualized: {indicators.get('volatility_30d', 0):.1%}")
    lines.append(f"  1-Year Annualized: {indicators.get('volatility_1y', 0):.1%}")

    lines.append(f"\n  --- Support/Resistance (20-day) ---")
    lines.append(f"  Support: ${indicators.get('support', 0):.2f}")
    lines.append(f"  Resistance: ${indicators.get('resistance', 0):.2f}")

    lines.append(f"\n  --- Volume ---")
    lines.append(f"  Latest: {indicators.get('latest_volume', 0):,.0f}")
    lines.append(f"  20-Day Avg: {indicators.get('avg_volume_20d', 0):,.0f}")
    lines.append(f"  Trend: {indicators.get('volume_trend', 'N/A')}")

    return "\n".join(lines)
