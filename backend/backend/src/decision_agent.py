from typing import List, Any

class DecisionAgent:
    """
    A simple decision-making agent to evaluate detected signals and suggest potential trade actions.
    (This can be extended with more complex logic or even an AI agent in the future for adaptive decision-making.)
    """
    def evaluate_signals(self, signals: List[dict]) -> str:
        # Flags for detected conditions
        has_sell_liquidity = any(sig.get("type") == "LiquidityPool" and sig.get("side") == "buy" for sig in signals)
        has_buy_liquidity = any(sig.get("type") == "LiquidityPool" and sig.get("side") == "sell" for sig in signals)
        has_bearish_ob = any(sig.get("type") == "OrderBlock" and sig.get("side") == "bearish" for sig in signals)
        has_bullish_ob = any(sig.get("type") == "OrderBlock" and sig.get("side") == "bullish" for sig in signals)

        # Detect Fair Value Gaps
        bullish_fvg = [sig for sig in signals if sig.get("type") == "FairValueGap" and sig.get("side") == "bullish"]
        bearish_fvg = [sig for sig in signals if sig.get("type") == "FairValueGap" and sig.get("side") == "bearish"]
        has_bullish_fvg = len(bullish_fvg) > 0
        has_bearish_fvg = len(bearish_fvg) > 0

        suggestion = "No immediate action – monitor the market for now."
        # Bearish Silver Bullet (short) setup
        if has_buy_liquidity and has_bearish_fvg:
            if has_bearish_ob:
                sig = bearish_fvg[-1]
                suggestion = (
                    "**Bearish Silver Bullet:** Sell-side liquidity (equal highs) detected, a bearish Fair Value Gap at "
                    f"{sig['gap_low']}–{sig['gap_high']}, and a bearish order block present. "
                    "Enter short inside the gap, place stop-loss above the gap_high, and target a minimum 2R reward."
                )
            else:
                sig = bearish_fvg[-1]
                suggestion = (
                    "**Bearish setup:** Sell-side liquidity (equal highs) and a bearish Fair Value Gap at "
                    f"{sig['gap_low']}–{sig['gap_high']} detected. Consider entering short inside the gap with a stop-loss above gap_high, "
                    "and wait for order block or market structure shift for confirmation."
                )
        # Bullish Silver Bullet (long) setup
        elif has_sell_liquidity and has_bullish_fvg:
            if has_bullish_ob:
                sig = bullish_fvg[-1]
                suggestion = (
                    "**Bullish Silver Bullet:** Buy-side liquidity (equal lows) detected, a bullish Fair Value Gap at "
                    f"{sig['gap_low']}–{sig['gap_high']}, and a bullish order block present. "
                    "Enter long inside the gap, place stop-loss below the gap_low, and target a minimum 2R reward."
                )
            else:
                sig = bullish_fvg[-1]
                suggestion = (
                    "**Bullish setup:** Buy-side liquidity (equal lows) and a bullish Fair Value Gap at "
                    f"{sig['gap_low']}–{sig['gap_high']} detected. Consider entering long inside the gap with a stop-loss below gap_low, "
                    "and wait for order block or market structure shift for confirmation."
                )
        return suggestion