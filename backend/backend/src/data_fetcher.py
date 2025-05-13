from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Set
import pandas as pd
from .market_calendar import MarketCalendar

@dataclass
class Candle:
    """Data structure for a single OHLCV candle (price bar)."""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None

class DataFetcher(ABC):
    """Abstract base class for data fetchers. Implementations should fetch OHLC data and return a list of Candle objects."""
    @abstractmethod
    def fetch(self, symbol: str, interval: str, limit: int) -> List[Candle]:
        pass

class YahooFinanceFetcher(DataFetcher):
    """Concrete DataFetcher using Yahoo Finance (via yfinance). Fetches historical data for the given symbol and interval."""
    def __init__(self):
        # map each interval to how many days of history to fetch
        self._interval_periods = {
            "1m" : "7d",
            "2m" : "14d",
            "5m" : "30d",
            "15m": "365d",
            "1h" : "365d",
            "1d" : "200d",
            "5d" : "365d",
            "1wk": "365d",
            "1mo": "365d",
            "3mo": "365d"
        }
        self.market_calendar = MarketCalendar()
        # simple in-memory cache: key=(symbol,interval,days_back) -> (fetched_at, candles)
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)

    def fetch(self, symbol: str, interval: str = "1d", limit: int = 150, attempted_symbols: Set[str] = None) -> List[Candle]:
        """
        Fetch market data for the given symbol.
        
        Args:
            symbol: The ticker symbol to fetch
            interval: The timeframe interval
            limit: Maximum number of candles to return
            attempted_symbols: Set of symbols already attempted to prevent recursion
        """
        if attempted_symbols is None:
            attempted_symbols = set()
        
        # Add current symbol to attempted set
        attempted_symbols.add(symbol)

        try:
            import yfinance as yf
        except ImportError as e:
            raise ImportError("yfinance library is required for YahooFinanceFetcher. Please install it.") from e

        try:
            # before hitting Yahoo: determine how far back to fetch
            period_str = self._interval_periods.get(interval, '60d')
            if period_str.endswith('d'):
                days_back = int(period_str[:-1])
            elif period_str.endswith('w'):
                days_back = int(period_str[:-2]) * 7
            elif period_str.endswith('mo'):
                days_back = int(period_str[:-2]) * 30
            else:
                days_back = 60
            # check in-memory cache
            cache_key = (symbol, interval, days_back)
            now = datetime.utcnow()
            cache_entry = self._cache.get(cache_key)
            if cache_entry and (now - cache_entry[0]) < self._cache_ttl:
                print(f"DEBUG: Returning cached data for {cache_key}")
                return cache_entry[1]
            # Create ticker object
            ticker = yf.Ticker(symbol)
            print(f"\nDEBUG: Fetching data for {symbol}")
            print(f"DEBUG: Parameters - interval={interval}, limit={limit}")
            
            # retry loop for history fetch
            df = None
            for attempt in range(3):
                try:
                    start_date, end_date = self.market_calendar.get_valid_trading_range(days_back=days_back, interval=interval)
                    print(f"DEBUG: Using date range for {interval} - start={start_date}, end={end_date}")
                    df = ticker.history(
                        start=start_date,
                        end=end_date,
                        interval=interval,
                        auto_adjust=True
                    )
                    print(f"DEBUG: Raw data shape: {df.shape}")
                    print(f"DEBUG: Data columns: {df.columns.tolist()}")
                    print(f"DEBUG: First few rows:\n{df.head()}")
                    if not df.empty:
                        break
                except Exception as e:
                    print(f"DEBUG: Attempt {attempt+1} failed with error: {str(e)}")
                    if attempt == 2:
                        raise ValueError(f"Failed to fetch data after 3 attempts: {str(e)}")
                    continue
            if df is None or df.empty:
                raise ValueError(f"No data available for {symbol} with interval {interval}")
        except Exception as e:
            print(f"DEBUG: Attempt failed with error: {str(e)}")
            raise ValueError(f"Failed to fetch data: {str(e)}")

        print(f"DEBUG: Retrieved {len(df)} rows of data")

        # Trim to the requested limit
        if limit:
            df = df.tail(limit)
            print(f"DEBUG: After trimming to {limit} rows: {len(df)} rows")

        # Convert DataFrame rows to Candle objects
        candles: List[Candle] = []
        for timestamp, row in df.iterrows():
            try:
                candle = Candle(
                    time=timestamp.to_pydatetime(),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume']) if 'Volume' in row and pd.notna(row['Volume']) else None
                )
                candles.append(candle)
            except (ValueError, KeyError) as e:
                print(f"DEBUG: Warning: Skipping invalid candle data: {e}")
                continue

        if not candles:
            raise ValueError(f"No valid candle data for {symbol} with interval {interval}")

        # Filter out after-hours data for intraday timeframes
        if interval.endswith('m') or interval.endswith('h'):
            candles = self.market_calendar.filter_market_hours(candles)
            if not candles:
                raise ValueError(f"No market hours data available for {symbol}")

        print(f"DEBUG: Successfully processed {len(candles)} candles")
        print(f"DEBUG: First candle time: {candles[0].time}")
        print(f"DEBUG: Last candle time: {candles[-1].time}")
        # store in cache
        self._cache[cache_key] = (datetime.utcnow(), candles)
        return candles