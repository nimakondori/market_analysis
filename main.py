from src.data_fetcher import YahooFinanceFetcher
from src.pattern_analyzer import PatternAnalyzer
from src.alert_generator import AlertGenerator
from src.decision_agent import DecisionAgent

if __name__ == "__main__":
    # Configuration: symbol and timeframe to analyze
    symbol = "^GSPC"  
    interval = "1m"       # 1-minute timeframe
    lookback_bars = 100   # analyze last 100 bars

    # Initialize components
    fetcher = YahooFinanceFetcher()
    analyzer = PatternAnalyzer(lookback=lookback_bars)
    alert_gen = AlertGenerator()
    agent = DecisionAgent()

    # Fetch recent market data
    try:
        candles = fetcher.fetch(symbol=symbol, interval=interval, limit=lookback_bars * 2)
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        exit(1)

    # Ensure we have data to analyze
    if not candles:
        print(f"No data retrieved for {symbol}.")
        exit(0)

    # Analyze patterns in the data
    signals = analyzer.analyze(candles)

    # Generate descriptive alerts for each detected pattern
    alerts = alert_gen.generate_alerts(signals)

    # Evaluate signals to get a suggestion (if any)
    suggestion = agent.evaluate_signals(signals)

    # Output the results
    print(f"=== ICT Pattern Analysis for {symbol} ({interval}) ===")
    for alert in alerts:
        print("-", alert)
    print("\nStrategy Hint:")
    print(suggestion)