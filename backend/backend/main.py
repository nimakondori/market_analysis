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
async def get_market_data(interval: str = Query("1m", description="Timeframe interval, e.g. 1m, 5m, 1h, 1d")):
    # validate the requested interval
    allowed_intervals = set(fetcher._interval_periods.keys()) if hasattr(fetcher, '_interval_periods') else set()
    if interval not in allowed_intervals:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported interval '{interval}'. Valid intervals: {', '.join(sorted(allowed_intervals))}"
        )
    try:
        # Try different symbols in order of preference
        symbols = ["^GSPC"]  # Try SPY first (supports 1m intraday), then fallback to S&P 500 index
        # Use requested interval; fetch all available bars (limit=0 disables trimming)
        lookback_bars = 0
        
        last_error = None
        for symbol in symbols:
            try:
                print(f"Attempting to fetch data for {symbol} with interval={interval}")
                candles = fetcher.fetch(symbol=symbol, interval=interval, limit=lookback_bars)
                if candles:
                    break
            except Exception as e:
                print(f"Failed to fetch {symbol} ({interval}): {str(e)}")
                last_error = e
                continue
        else:  # If no symbol succeeded
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch data for all symbols. Last error: {str(last_error)}"
            )
            
        # Analyze patterns
        signals = analyzer.analyze(candles)
        alerts = alert_gen.generate_alerts(signals)
        suggestion = agent.evaluate_signals(signals)
        
        # Convert candles to frontend format, ensuring we use the actual market data time
        formatted_candles = []
        for candle in candles:
            # Convert to Eastern Time for consistency
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
            alert_type = 'neutral'
            if 'Bullish' in alert_text:
                alert_type = 'buy'
            elif 'Bearish' in alert_text:
                alert_type = 'sell'
                
            # Convert signal time to Eastern Time for consistency
            signal_time = signal.get('time', datetime.now())
            if isinstance(signal_time, datetime):
                et_time = signal_time.astimezone(analyzer.eastern)
                timestamp = et_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                # Fallback to current time if no valid timestamp
                timestamp = datetime.now(analyzer.eastern).strftime('%Y-%m-%d %H:%M:%S')
                
            formatted_alerts.append({
                'id': str(i + 1),
                'timestamp': timestamp,
                'message': alert_text,
                'type': alert_type,
                'confidence': 0.85  # Default confidence
            })
        
        return {
            'candles': formatted_candles,
            'alerts': formatted_alerts,
            'suggestion': suggestion
        }
        
    except Exception as e:
        print(f"Error in get_market_data: {str(e)}")  # Add logging
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process market data: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001) 