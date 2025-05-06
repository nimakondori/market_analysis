from typing import List

class AlertGenerator:
    """Generates detailed natural-language alerts for detected patterns, including ICT concepts like liquidity sweeps and inducements."""
    def generate_alerts(self, signals: List[dict]) -> List[str]:
        alerts: List[str] = []
        for sig in signals:
            stype = sig.get("type")
            if stype == "LiquidityPool":
                side = sig.get("side")
                price = sig.get("price")
                t1, t2 = sig.get("times", [None, None])
                if side == "buy":
                    # Buy-side liquidity (equal highs) alert
                    alert = (f"Equal highs detected around **{price:.4f}** (formed on {t1} and {t2}). "
                             f"This indicates a pool of **buy-side liquidity** (buy stop orders) resting above that level [oai_citation:5‡in.tradingview.com](https://in.tradingview.com/scripts/ict/#:~:text=As%20part%20of%20the%20Flow,studying%20ICT%20Smart%20Money%20Concepts). "
                             "The market may be **engineering liquidity** here by enticing breakout buyers. "
                             f"Watch for a potential **liquidity sweep** above {price:.4f} (a stop raid) followed by a sharp drop, "
                             "as smart money grabs those stops (inducement) before reversing the price down.")
                else:
                    # Sell-side liquidity (equal lows) alert
                    alert = (f"Equal lows detected around **{price:.4f}** (formed on {t1} and {t2}). "
                             f"This signifies **sell-side liquidity** (sell stop orders) below that level [oai_citation:6‡in.tradingview.com](https://in.tradingview.com/scripts/ict/#:~:text=As%20part%20of%20the%20Flow,studying%20ICT%20Smart%20Money%20Concepts). "
                             "Smart money might drive price down to **sweep liquidity** below these lows, triggering stop-loss orders of longs (and inducing breakout sellers). "
                             "Such a sweep is often followed by a quick reversal upward, indicating an inducement trap and a potential bullish move.")
                alerts.append(alert)
            elif stype == "FairValueGap":
                side = sig.get("side")
                gap = sig.get("gap")  # tuple (low_bound, high_bound)
                time = sig.get("time")
                if not gap:
                    continue
                lower, upper = gap
                if side == "bullish":
                    # Bullish FVG alert
                    alert = (f"**Bullish Fair Value Gap** spotted from ~{lower:.4f} up to {upper:.4f} (gap formed around {time}). "
                             "This price range is an **imbalance** where buying overwhelmed selling [oai_citation:7‡github.com](https://github.com/joshyattridge/smart-money-concepts#:~:text=Fair%20Value%20Gap%20), leaving a void. "
                             "Price may be drawn back down into this gap (**liquidity void**) before the uptrend resumes. "
                             "Watch for price to dip into this gap and then reject higher, which could offer a bullish entry if the gap acts as support.")
                else:
                    # Bearish FVG alert
                    alert = (f"**Bearish Fair Value Gap** spotted from ~{lower:.4f} down to {upper:.4f} (gap formed around {time}). "
                             "This zone is an **inefficiency** from aggressive selling [oai_citation:8‡github.com](https://github.com/joshyattridge/smart-money-concepts#:~:text=Fair%20Value%20Gap%20), effectively a liquidity void above. "
                             "Price often retraces up into such gaps to fill that void (retrieving liquidity) before continuing downward. "
                             "Be prepared for a possible bearish reversal if price rebounds down from this gap area.")
                alerts.append(alert)
            elif stype == "OrderBlock":
                side = sig.get("side")
                zone = sig.get("zone")  # tuple (low_price, high_price) of the order block candle range
                time = sig.get("time")
                if not zone:
                    continue
                low, high = zone
                if side == "bearish":
                    # Bearish Order Block alert
                    alert = (f"**Bearish Order Block** identified (from {low:.4f} to {high:.4f}, formed on {time}). "
                             "This was the last bullish candle before a strong drop, indicating a **supply zone** where institutions likely sold. "
                             "If price retraces into this zone, it may meet significant resistance (sell orders). "
                             "Watch for bearish signals if price revisits this order block – it could be a high-probability short entry area.")
                else:
                    # Bullish Order Block alert
                    alert = (f"**Bullish Order Block** identified (from {low:.4f} to {high:.4f}, formed on {time}). "
                             "This was the last bearish candle before a strong rally, marking a **demand zone** where smart money bought. "
                             "If price returns to this zone, it may find support (buy orders). "
                             "Look for bullish confirmation if price revisits this order block, as it could offer a reliable long entry point.")
                alerts.append(alert)
        return alerts