import time
import yfinance as yf
import pandas as pd

# Configurable parameters
SYMBOLS = ["^GSPC", "^DJI", "^IXIC"]        # symbols for S&P 500, Dow Jones, Nasdaq indices
INTERVAL = "5m"                             # timeframe interval: "1m", "5m", "1h", etc.
LOOKBACK_BARS = 50                          # how many recent bars to analyze for patterns
POLL_INTERVAL = 300 if INTERVAL == "5m" else 60  # seconds to wait between data fetches (adjust per interval)

# Helper: Fetch latest data for all symbols
def fetch_data(symbols, interval, lookback):
    """Fetch recent OHLC data for given symbols from Yahoo Finance."""
    data_dict = {}
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            # Fetch recent data (e.g., 1 day for intraday intervals)
            if interval.endswith("m") or interval.endswith("h"):
                hist = ticker.history(period="1d", interval=interval)
            else:
                # for daily or higher, maybe 100 days
                hist = ticker.history(period="100d", interval=interval)
            # Keep only the last `lookback` bars for analysis
            hist = hist.tail(lookback)
            # Ensure columns are lowercase for consistency
            hist = hist.rename(columns=str.lower)
            data_dict[symbol] = hist
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            data_dict[symbol] = None
    return data_dict

# Helper: Identify Fair Value Gaps in a DataFrame of OHLC data
def find_fvg(df):
    """Find Fair Value Gaps in the price data. Returns list of dict with info about each FVG found."""
    fvg_list = []
    highs = df['high'].values
    lows = df['low'].values
    opens = df['open'].values
    closes = df['close'].values
    # We iterate from second candle to second-last candle (index 1 to len-2) for 3-candle patterns
    for i in range(1, len(df)-1):
        prev_high = highs[i-1]
        next_low = lows[i+1]
        prev_low = lows[i-1]
        next_high = highs[i+1]
        # Identify bullish FVG
        if closes[i] > opens[i] and prev_high < next_low:
            # bullish gap between prev_high and next_low
            fvg_list.append({
                "type": "bullish",
                "index": i,
                "gap_top": prev_high,
                "gap_bottom": next_low,
                "timestamp": df.iloc[i].name
            })
        # Identify bearish FVG
        if closes[i] < opens[i] and prev_low > next_high:
            # bearish gap between next_high and prev_low
            fvg_list.append({
                "type": "bearish",
                "index": i,
                "gap_top": prev_low,
                "gap_bottom": next_high,
                "timestamp": df.iloc[i].name
                
            })
    return fvg_list

# Helper: Identify Order Blocks in a DataFrame
def find_order_blocks(df):
    """Detect Order Blocks (bullish and bearish) in the data. Returns list of dicts with OB info."""
    ob_list = []
    highs = df['high'].values
    lows = df['low'].values
    opens = df['open'].values
    closes = df['close'].values

    # Simple approach: find swing highs/lows and check last candle before swing reversal
    for i in range(2, len(df)-1):
        # Bullish OB: a bearish candle at a local low with a subsequent bullish break above it
        # Check if candle i is bearish
        if closes[i] < opens[i]:
            # local low condition: candle i's low is lower than lows of some candles before (e.g. previous 2 candles)
            if lows[i] == min(lows[i-2:i+1]):  # comparing with two previous candles for local swing
                # Check if next candle breaks above this candle's high
                if closes[i+1] > highs[i] or highs[i+1] > highs[i]:
                    ob_list.append({
                        "type": "bullish",
                        "index": i,
                        "zone_low": lows[i],
                        "zone_high": highs[i]
                    })
        # Bearish OB: a bullish candle at a local high with subsequent bearish break below it
        if closes[i] > opens[i]:
            if highs[i] == max(highs[i-2:i+1]):  # local swing high
                if closes[i+1] < lows[i] or lows[i+1] < lows[i]:
                    ob_list.append({
                        "type": "bearish",
                        "index": i,
                        "zone_low": lows[i],
                        "zone_high": highs[i]
                    })
    return ob_list

# Helper: Generate alert messages for identified patterns
def generate_alerts(symbol, df, fvg_list, ob_list, last_alerts):
    """
    Compare current price to identified FVGs/OBs and generate alert messages for new opportunities.
    `last_alerts` is a dict to track already alerted zones (to avoid repeating).
    """
    alerts = []
    current_price = df['close'].iloc[-1]
    # Check each FVG if price has entered the gap for first time
    for fvg in fvg_list:
        fvg_type = fvg["type"]
        top = fvg["gap_top"]
        bottom = fvg["gap_bottom"]
        zone_key = (fvg_type, "FVG", top, bottom)
        if zone_key in last_alerts:
            continue  # already alerted this FVG
        # Condition: if bullish FVG and current price <= bottom (entered or below gap)
        if fvg_type == "bullish" and current_price <= bottom:
            msg = (f"({symbol}) Alert: Price has filled into a **bullish Fair Value Gap** zone "
                   f"(~{top:.2f} to {bottom:.2f}). This imbalance could serve as a support area – "
                   f"potential long entry signal if bullish trend resumes.")
            alerts.append(msg)
            last_alerts[zone_key] = True
        # If bearish FVG and current price >= top (entered the gap from below)
        if fvg_type == "bearish" and current_price >= top:
            msg = (f"({symbol}) Alert: Price has rallied into a **bearish Fair Value Gap** zone "
                   f"(~{bottom:.2f} to {top:.2f}). This supply imbalance could cap the price – "
                   f"potential short entry signal if bearish pressure returns.")
            alerts.append(msg)
            last_alerts[zone_key] = True

    # Check each Order Block if price has returned to the zone
    for ob in ob_list:
        ob_type = ob["type"]
        z_low = ob["zone_low"]
        z_high = ob["zone_high"]
        zone_key = (ob_type, "OB", z_low, z_high)
        if zone_key in last_alerts:
            continue  # already alerted this OB zone
        # If bullish OB and price is back down in the zone (between z_low and z_high)
        if ob_type == "bullish" and z_low <= current_price <= z_high:
            # Suggest SL a bit below zone low, TP at recent high
            recent_high = max(df['high'].iloc[ob['index']+1:])  # high after OB formed
            sl = z_low * 0.99  # e.g., 1% below zone low (adjust as needed)
            tp = recent_high
            msg = (f"({symbol}) Alert: **Bullish Order Block** retest at ~{current_price:.2f}. "
                   f"Price is back in a demand zone from earlier. Potential long entry with stop-loss ~{sl:.2f} "
                   f"below the zone, targeting ~{tp:.2f} or higher.")
            alerts.append(msg)
            last_alerts[zone_key] = True
        # If bearish OB and price is back up into the zone
        if ob_type == "bearish" and z_low <= current_price <= z_high:
            recent_low = min(df['low'].iloc[ob['index']+1:])
            sl = z_high * 1.01  # 1% above zone high
            tp = recent_low
            msg = (f"({symbol}) Alert: **Bearish Order Block** retest at ~{current_price:.2f}. "
                   f"Price is retesting a supply zone from earlier. Potential short entry with stop-loss ~{sl:.2f} "
                   f"above the zone, targeting ~{tp:.2f} or lower.")
            alerts.append(msg)
            last_alerts[zone_key] = True
    return alerts

# Main loop: continuously fetch data and analyze
if __name__ == "__main__":
    print(f"Starting ICT pattern watcher for {SYMBOLS} on {INTERVAL} timeframe...")
    last_alerted_zones = {}  # to avoid duplicate alerts
    while True:
        data = fetch_data(SYMBOLS, INTERVAL, LOOKBACK_BARS)
        for symbol, df in data.items():
            if df is None or df.empty:
                continue  # skip if data fetch failed
            # Find patterns in the latest data
            fvg_zones = find_fvg(df)
            ob_zones = find_order_blocks(df)
            # Generate any new alerts
            alerts = generate_alerts(symbol, df, fvg_zones, ob_zones, last_alerted_zones)
            for alert in alerts:
                print(alert)
        # Wait for the next interval
        time.sleep(POLL_INTERVAL)