from datetime import datetime, timedelta
import pandas_market_calendars as mcal
from typing import Tuple, List
import pytz

class MarketCalendar:
    """Utility class for handling market hours and trading days."""
    
    def __init__(self):
        # Initialize NYSE calendar (most widely used for US markets)
        self.calendar = mcal.get_calendar('NYSE')
        self.eastern = pytz.timezone('America/New_York')
        self.market_open_time = 9  # 9:30 AM ET
        self.market_open_minute = 30
        self.market_close_time = 16  # 4:00 PM ET
        self.market_close_minute = 0
        
    def is_market_hours(self, dt: datetime) -> bool:
        """Check if the given datetime is during market hours (9:30 AM - 4:00 PM ET)."""
        if not dt.tzinfo:
            dt = pytz.utc.localize(dt)
        et_time = dt.astimezone(self.eastern)
        
        # Check if it's during market hours
        if et_time.hour < self.market_open_time or et_time.hour > self.market_close_time:
            return False
        if et_time.hour == self.market_open_time and et_time.minute < self.market_open_minute:
            return False
        if et_time.hour == self.market_close_time and et_time.minute > self.market_close_minute:
            return False
            
        return True
        
    def is_market_open(self, date: datetime = None) -> bool:
        """
        Check if the market is open on the given date.
        
        Args:
            date: The date to check. Defaults to current date/time.
            
        Returns:
            bool: True if market is open, False otherwise
        """
        if date is None:
            # Use market close time (4:00 PM ET)
            date = datetime.now(self.eastern).replace(second=0, microsecond=0)
            
        # Convert to date only (remove time component)
        date_only = date.date()
        
        # Get market schedule for the date
        schedule = self.calendar.schedule(
            start_date=date_only,
            end_date=date_only
        )
        
        return not schedule.empty
    
    def get_last_trading_day(self, date: datetime = None) -> datetime:
        """
        Get the last trading day before the given date.
        
        Args:
            date: The reference date. Defaults to current date/time.
            
        Returns:
            datetime: The last trading day
        """
        if date is None:
            # Use market close time (4:00 PM ET)
            date = datetime.now(self.eastern).replace(hour=16, minute=0, second=0, microsecond=0)
            
        # Look back up to 5 days to find the last trading day
        for i in range(5):
            check_date = date - timedelta(days=i)
            if self.is_market_open(check_date):
                # Set time to market close (4:00 PM ET)
                return check_date.replace(hour=16, minute=0, second=0, microsecond=0)
                
        raise ValueError("Could not find a trading day within the last 5 days")
    
    def filter_market_hours(self, candles: List['Candle']) -> List['Candle']:
        """Filter candles to only include those during market hours."""
        return [candle for candle in candles if self.is_market_hours(candle.time)]
    
    def get_valid_trading_range(self, end_date: datetime = None, days_back: int = 365, interval: str = "1d") -> Tuple[datetime, datetime]:
        """
        Get a valid date range for market data that ensures the end date is a trading day
        and extends back the specified number of days.
        
        Args:
            end_date: The desired end date. Defaults to current date/time.
            days_back: Number of days to look back. Defaults to 365.
            interval: The timeframe interval (e.g., "1m", "5m", "1d")
            
        Returns:
            Tuple[datetime, datetime]: (start_date, end_date) where end_date is guaranteed to be a trading day
        """
        if end_date is None:
            # Use current time in Eastern timezone
            end_date = datetime.now(self.eastern)
            
        # For intraday data (minutes), limit to 7 days and use current time
        if interval.endswith('m') or interval.endswith('h'):
            # For intraday data, we can only get up to 7 days of data
            days_back = min(days_back, 7)
            # Use current time as end date, but cap at market close
            if self.is_market_hours(end_date):
                end_date = end_date.replace(second=0, microsecond=0)
            else:
                # Use last market close
                end_date = self.get_last_trading_day(end_date)
            start_date = end_date - timedelta(days=days_back)
            return start_date, end_date
            
        # For daily or longer intervals, ensure end_date is a trading day
        end_date = self.get_last_trading_day(end_date)
        start_date = end_date - timedelta(days=days_back)
        
        return start_date, end_date 