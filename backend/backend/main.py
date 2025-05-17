from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import from src
sys.path.append(str(Path(__file__).parent))

from src.data_fetcher import YahooFinanceFetcher
from src.pattern_analyzer import PatternAnalyzer
from src.alert_generator import AlertGenerator
from src.decision_agent import DecisionAgent

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # Support both Vite ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
fetcher = YahooFinanceFetcher()
analyzer = PatternAnalyzer(lookback=100)
alert_gen = AlertGenerator()
agent = DecisionAgent()

@app.get("/api/market-data")
async def get_market_data(
    interval: str = Query("1m", description="Timeframe interval, e.g. 1m, 5m, 1h, 1d"),
    symbol: str = Query("^GSPC", description="Symbol to fetch, e.g. ^GSPC, ^DJI, ^IXIC, AAPL, etc.")
):
    # Symbol mapping for human-readable names
    symbol_map = {
        '^GSPC': 'S&P 500 (SPX)',
        '^DJI': 'Dow Jones (DJI)',
        '^IXIC': 'Nasdaq (IXIC)',
        'AAPL': 'Apple (AAPL)',
        'MSFT': 'Microsoft (MSFT)',
        # Add more as needed
    }
    # validate the requested interval
    allowed_intervals = set(fetcher._interval_periods.keys()) if hasattr(fetcher, '_interval_periods') else set()
    if interval not in allowed_intervals:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported interval '{interval}'. Valid intervals: {', '.join(sorted(allowed_intervals))}"
        )
    try:
        # Use requested symbol, fallback to S&P 500 if not recognized
        yf_symbol = symbol if symbol in symbol_map else '^GSPC'
        human_name = symbol_map.get(yf_symbol, yf_symbol)
        # Use requested interval; fetch all available bars (limit=0 disables trimming)
        lookback_bars = 0
        last_error = None
        try:
            candles = fetcher.fetch(symbol=yf_symbol, interval=interval, limit=lookback_bars)
        except Exception as e:
            print(f"Failed to fetch {yf_symbol} ({interval}): {str(e)}")
            last_error = e
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch data for symbol {yf_symbol}. Error: {str(e)}"
            )
        # Analyze patterns
        signals = analyzer.analyze(candles)
        alerts = alert_gen.generate_alerts(signals)
        suggestion = agent.evaluate_signals(signals)
        # Convert candles to frontend format, ensuring we use the actual market data time
        formatted_candles = []
        for candle in candles:
            et_time = candle.time.astimezone(analyzer.eastern)
            formatted_candles.append({
                'time': et_time.strftime('%Y-%m-%d %H:%M:%S'),
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.volume if candle.volume else 0
            })
        # Format alerts for frontend, using the actual signal timestamps
        formatted_alerts = []
        for i, (signal, alert_text) in enumerate(zip(signals, alerts)):
            stype = signal.get('type')
            side = signal.get('side')
            alert_type = 'neutral'
            if stype == 'LiquidityPool':
                if side == 'buy':
                    alert_type = 'sell'
                elif side == 'sell':
                    alert_type = 'buy'
            elif stype in ('FairValueGap', 'OrderBlock'):
                if side == 'bullish':
                    alert_type = 'buy'
                elif side == 'bearish':
                    alert_type = 'sell'
            signal_time = signal.get('time', datetime.now())
            if isinstance(signal_time, datetime):
                et_time = signal_time.astimezone(analyzer.eastern)
                timestamp = et_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp = datetime.now(analyzer.eastern).strftime('%Y-%m-%d %H:%M:%S')
            stop_loss = None
            take_profit = None
            if suggestion['action'] in ['buy', 'sell'] and suggestion.get('entry_zone'):
                if (alert_type == suggestion['action'] and
                    'Fair Value Gap' in alert_text and
                    f"{suggestion['entry_zone'][0]:.2f}" in alert_text and
                    f"{suggestion['entry_zone'][1]:.2f}" in alert_text):
                    stop_loss = suggestion['stop_loss']
                    take_profit = suggestion['take_profit']
            neutral_reason = None
            if alert_type == 'neutral':
                if stype == 'LiquidityPool':
                    neutral_reason = (
                        'This alert is neutral because it only indicates the presence of a liquidity pool (equal highs/lows) and does not by itself provide a directional trade signal. '
                        'Look for confirmation from other patterns (e.g., Fair Value Gaps or Order Blocks) for actionable trades.'
                    )
                elif stype == 'FairValueGap' or stype == 'OrderBlock':
                    neutral_reason = (
                        'This alert is neutral because the detected pattern does not meet all criteria for a high-probability trade setup (e.g., missing confluence with liquidity or time window).' 
                        'Monitor the market for further developments.'
                    )
                else:
                    neutral_reason = 'No actionable trade direction detected for this pattern.'
            alert_obj = {
                'id': str(i + 1),
                'timestamp': timestamp,
                'message': f"[{timestamp}] {alert_text}",
                'type': alert_type,
                'confidence': 0.85,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            if alert_type == 'neutral':
                alert_obj['neutral_reason'] = neutral_reason
            # Pass through times if present (for frontend multi-marker support)
            if 'times' in signal:
                alert_obj['times'] = [
                    t.strftime('%Y-%m-%d %H:%M:%S') if isinstance(t, datetime) else str(t)
                    for t in signal['times']
                ]
            formatted_alerts.append(alert_obj)
        return {
            'candles': formatted_candles,
            'alerts': formatted_alerts,
            'suggestion': suggestion,
            'symbol': yf_symbol,
            'symbol_name': human_name
        }
        
    except Exception as e:
        print(f"Error in get_market_data: {str(e)}")  # Add logging
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process market data: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001) 