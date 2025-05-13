from typing import List, Dict
from datetime import datetime
import pytz

from src.data_fetcher import Candle  # assumes Candle has attributes: time (datetime), open, high, low, close, volume


class PatternAnalyzer:
    """
    Reimplementation following ICT's Silver Bullet model:
    - Liquidity Pools: equal highs (buy-side) and equal lows (sell-side)
    - Fair Value Gaps: 3-candle directional impulses leaving a wick gap
    - Order Blocks: last opposing candle before a large displacement
    - Silver Bullet Time Windows: only flag FVGs occurring during 3–4 AM, 10–11 AM, or 2–3 PM Eastern Time
    """

    def __init__(self, lookback: int = 100, equal_tolerance: float = 1e-3):
        self.lookback = lookback
        self.equal_tolerance = equal_tolerance
        self.eastern = pytz.timezone("America/New_York")

    def analyze(self, candles: List[Candle]) -> List[Dict]:
        """Run all pattern detectors on the most recent `lookback` candles."""
        signals = []
        n = len(candles)
        if n < 3:
            return signals
        start = max(0, n - self.lookback)

        signals.extend(self._detect_equal_highs(candles, start))
        signals.extend(self._detect_equal_lows(candles, start))
        signals.extend(self._detect_fvg(candles, start))
        signals.extend(self._detect_order_blocks(candles, start))

        return signals

    def _detect_equal_highs(self, candles: List[Candle], start: int) -> List[Dict]:
        """Find pivot highs that repeat within tolerance (buy-side liquidity)."""
        events = []
        highs: Dict[float, list] = {}
        for c in candles[start:]:
            price = round(c.high, 6)
            found = False
            for lvl in list(highs):
                if abs(lvl - price) <= self.equal_tolerance:
                    highs[lvl].append(c.time)
                    found = True
                    break
            if not found:
                highs[price] = [c.time]
        for lvl, times in highs.items():
            if len(times) >= 2:
                events.append({
                    "type": "LiquidityPool",
                    "side": "buy",
                    "price": lvl,
                    "times": [times[0], times[1]],
                })
        return events

    def _detect_equal_lows(self, candles: List[Candle], start: int) -> List[Dict]:
        """Find pivot lows that repeat within tolerance (sell-side liquidity)."""
        events = []
        lows: Dict[float, list] = {}
        for c in candles[start:]:
            price = round(c.low, 6)
            found = False
            for lvl in list(lows):
                if abs(lvl - price) <= self.equal_tolerance:
                    lows[lvl].append(c.time)
                    found = True
                    break
            if not found:
                lows[price] = [c.time]
        for lvl, times in lows.items():
            if len(times) >= 2:
                events.append({
                    "type": "LiquidityPool",
                    "side": "sell",
                    "price": lvl,
                    "times": [times[0], times[1]],
                })
        return events

    def _detect_fvg(self, candles: List[Candle], start: int) -> List[Dict]:
        """
        Detect 3-candle Fair Value Gaps:
        - Three consecutive candles in same direction
        - Last candle's wick does not overlap first candle's wick
        - Only during Silver Bullet windows (ET)
        """
        events = []
        for i in range(start, len(candles) - 2):
            c0, c1, c2 = candles[i], candles[i+1], candles[i+2]
            # Check directional impulse
            bullish = all(c.close > c.open for c in (c0, c1, c2))
            bearish = all(c.close < c.open for c in (c0, c1, c2))
            if bullish and c2.low > c0.high:
                et_time = c2.time.astimezone(self.eastern)
                if self._in_silver_window(et_time):
                    events.append({
                        "type": "FairValueGap",
                        "side": "bullish",
                        "gap_low": c0.high,
                        "gap_high": c2.low,
                        "time": c2.time
                    })
            elif bearish and c2.high < c0.low:
                et_time = c2.time.astimezone(self.eastern)
                if self._in_silver_window(et_time):
                    events.append({
                        "type": "FairValueGap",
                        "side": "bearish",
                        "gap_low": c2.high,
                        "gap_high": c0.low,
                        "time": c2.time
                    })
        return events

    def _in_silver_window(self, dt: datetime) -> bool:
        """Return True if dt falls in one of the Silver Bullet time windows (ET)."""
        h = dt.hour + dt.minute / 60.0
        return (3.0 <= h < 4.0) or (10.0 <= h < 11.0) or (14.0 <= h < 15.0)

    def _detect_order_blocks(self, candles: List[Candle], start: int) -> List[Dict]:
        """
        Identify order blocks as the last opposing-direction candle 
        before a strong displacement (3-candle impulse).
        """
        events = []
        min_body_size = 0.0002  # Minimum body size as a percentage of price
        min_volume = 1000  # Minimum volume threshold
        
        for i in range(start, len(candles) - 3):
            c0, c1, c2, c3 = candles[i], candles[i+1], candles[i+2], candles[i+3]
            
            # Calculate body size as percentage of price
            body_size = abs(c0.close - c0.open) / c0.open
            
            # Skip if candle is too small or volume is too low
            if body_size < min_body_size or (c0.volume and c0.volume < min_volume):
                continue
                
            # displacement if 3-candle impulse
            if all(c.close > c.open for c in (c1, c2, c3)):
                # last bearish before bullish move
                if c0.close < c0.open:
                    events.append({
                        "type": "OrderBlock",
                        "side": "bullish",
                        "zone": (c0.low, c0.high),
                        "time": c0.time,
                        "body_size": body_size,
                        "volume": c0.volume
                    })
            elif all(c.close < c.open for c in (c1, c2, c3)):
                # last bullish before bearish move
                if c0.close > c0.open:
                    events.append({
                        "type": "OrderBlock",
                        "side": "bearish",
                        "zone": (c0.low, c0.high),
                        "time": c0.time,
                        "body_size": body_size,
                        "volume": c0.volume
                    })
        
        # Sort order blocks by body size and volume
        events.sort(key=lambda x: (x.get('body_size', 0) * (x.get('volume', 0) or 0)), reverse=True)
        return events