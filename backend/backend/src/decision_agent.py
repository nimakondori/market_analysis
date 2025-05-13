from typing import List, Any, Dict

class DecisionAgent:
    """
    A decision-making agent to evaluate detected signals and suggest potential trade actions, with explicit SL/TP.
    """
    def evaluate_signals(self, signals: List[dict]) -> Dict[str, Any]:
        # Flags for detected conditions
        has_sell_liquidity = any(sig.get("type") == "LiquidityPool" and sig.get("side") == "buy" for sig in signals)
        has_buy_liquidity = any(sig.get("type") == "LiquidityPool" and sig.get("side") == "sell" for sig in signals)
        
        # Get all order blocks and fair value gaps
        order_blocks = [sig for sig in signals if sig.get("type") == "OrderBlock"]
        bullish_obs = [ob for ob in order_blocks if ob.get("side") == "bullish"]
        bearish_obs = [ob for ob in order_blocks if ob.get("side") == "bearish"]
        
        bullish_fvg = [sig for sig in signals if sig.get("type") == "FairValueGap" and sig.get("side") == "bullish"]
        bearish_fvg = [sig for sig in signals if sig.get("type") == "FairValueGap" and sig.get("side") == "bearish"]
        
        has_bullish_fvg = len(bullish_fvg) > 0
        has_bearish_fvg = len(bearish_fvg) > 0

        # Default: no trade
        result = {
            "action": "none",
            "entry_zone": None,
            "stop_loss": None,
            "take_profit": None,
            "reason": "No immediate action – monitor the market for now."
        }

        # Helper for 2R target
        def calc_2r(entry, sl, direction):
            risk = abs(entry - sl)
            if direction == 'long':
                return entry + 2 * risk
            else:
                return entry - 2 * risk

        # Bearish Silver Bullet (short) setup
        if has_buy_liquidity and has_bearish_fvg:
            sig = bearish_fvg[-1]
            entry_zone = (sig['gap_low'], sig['gap_high'])
            entry = (sig['gap_low'] + sig['gap_high']) / 2
            stop_loss = sig['gap_high'] * 1.001  # 0.1% above gap high
            take_profit = calc_2r(entry, stop_loss, 'short')
            
            # Include relevant order blocks in the reason
            ob_info = ""
            if bearish_obs:
                ob_info = "\n\nRelevant bearish order blocks:"
                for ob in bearish_obs[:3]:  # Show top 3 order blocks
                    ob_info += f"\n- Order block at {ob['zone'][0]:.2f} - {ob['zone'][1]:.2f} (formed on {ob['time']})"
            
            reason = (
                "Bearish setup: Sell-side liquidity (equal highs) and a bearish Fair Value Gap detected. "
                f"Entry zone: {entry_zone[0]:.2f}–{entry_zone[1]:.2f}. Stop-loss: {stop_loss:.2f} above gap high. "
                f"Take profit: {take_profit:.2f} (2R)."
                f"{ob_info}"
            )
            result = {
                "action": "sell",
                "entry_zone": entry_zone,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "reason": reason
            }
        # Bullish Silver Bullet (long) setup
        elif has_sell_liquidity and has_bullish_fvg:
            sig = bullish_fvg[-1]
            entry_zone = (sig['gap_low'], sig['gap_high'])
            entry = (sig['gap_low'] + sig['gap_high']) / 2
            stop_loss = sig['gap_low'] * 0.999  # 0.1% below gap low
            take_profit = calc_2r(entry, stop_loss, 'long')
            
            # Include relevant order blocks in the reason
            ob_info = ""
            if bullish_obs:
                ob_info = "\n\nRelevant bullish order blocks:"
                for ob in bullish_obs[:3]:  # Show top 3 order blocks
                    ob_info += f"\n- Order block at {ob['zone'][0]:.2f} - {ob['zone'][1]:.2f} (formed on {ob['time']})"
            
            reason = (
                "Bullish setup: Buy-side liquidity (equal lows) and a bullish Fair Value Gap detected. "
                f"Entry zone: {entry_zone[0]:.2f}–{entry_zone[1]:.2f}. Stop-loss: {stop_loss:.2f} below gap low. "
                f"Take profit: {take_profit:.2f} (2R)."
                f"{ob_info}"
            )
            result = {
                "action": "buy",
                "entry_zone": entry_zone,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "reason": reason
            }
        return result