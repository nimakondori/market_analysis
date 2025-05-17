import { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { Box, CssBaseline, Container, Paper, Typography, CircularProgress, Alert as MuiAlert, ToggleButton, ToggleButtonGroup, Fab } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import CandlestickChart from './components/CandlestickChart';
import AlertsPanel from './components/AlertsPanel';
import { Candle, Alert } from './types';
import NotificationsIcon from '@mui/icons-material/Notifications';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});

const SYMBOLS = [
  { label: 'S&P 500 (SPX)', value: '^GSPC' },
  { label: 'Dow Jones (DJI)', value: '^DJI' },
  { label: 'Nasdaq (IXIC)', value: '^IXIC' },
  { label: 'Apple (AAPL)', value: 'AAPL' },
  { label: 'Microsoft (MSFT)', value: 'MSFT' },
  // Add more as needed
];

function App() {
  const [symbol, setSymbol] = useState<string>(SYMBOLS[0].value);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<{ action: string; reason: string; entry_zone?: [number, number]; stop_loss?: number; take_profit?: number } | null>(null);
  const [highlightedTimestamps, setHighlightedTimestamps] = useState<string[] | null>(null);
  const [timeframe, setTimeframe] = useState<string>('1m');
  const [isAlertsExpanded, setIsAlertsExpanded] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setError(null);
        setLoading(true);
        const response = await fetch(`/api/market-data?interval=${timeframe}&symbol=${encodeURIComponent(symbol)}`);
        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(
            errorData?.detail || 
            `Server error (${response.status}): ${response.statusText}`
          );
        }
        const data = await response.json();
        setCandles(data.candles);
        setAlerts(data.alerts || []);
        setSuggestion(data.suggestion);
      } catch (error) {
        setError(
          error instanceof Error 
            ? error.message 
            : 'Failed to connect to the market data server. Please ensure the backend is running on port 5001.'
        );
        setCandles([]);
        setAlerts([]);
        setSuggestion(null);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    const timer = window.setInterval(fetchData, 60000);
    return () => clearInterval(timer);
  }, [timeframe, symbol]);

  const selectedSymbol = SYMBOLS.find(s => s.value === symbol);

  console.log('App render state:', { loading, hasError: !!error, candlesCount: candles.length });

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Container maxWidth="xl" sx={{ py: 4, position: 'relative' }}>
        {loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              zIndex: 1000,
              backdropFilter: 'blur(2px)',
              transition: 'opacity 0.3s ease-in-out',
            }}
          >
            <CircularProgress />
          </Box>
        )}
        <Typography variant="h4" component="h1" gutterBottom>
          Market Analysis Dashboard - {selectedSymbol ? selectedSymbol.label : symbol}
        </Typography>
        
        {error && (
          <MuiAlert 
            severity="error" 
            sx={{ mb: 2 }}
            action={
              <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                Make sure the backend server is running on port 5001
              </Typography>
            }
          >
            {error}
          </MuiAlert>
        )}

        {suggestion && suggestion.action !== 'none' && (
          <MuiAlert severity={suggestion.action === 'buy' ? 'success' : 'error'} sx={{ mb: 2 }}>
            <Box sx={{ '& p': { m: 0 } }}>
              <Typography variant="subtitle1" gutterBottom>
                {suggestion.action.toUpperCase()} Signal
              </Typography>
              <ReactMarkdown>{suggestion.reason}</ReactMarkdown>
              {suggestion.entry_zone && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Entry Zone: {suggestion.entry_zone[0].toFixed(2)} - {suggestion.entry_zone[1].toFixed(2)}
                </Typography>
              )}
              {suggestion.stop_loss && (
                <Typography variant="body2">
                  Stop Loss: {suggestion.stop_loss.toFixed(2)}
                </Typography>
              )}
              {suggestion.take_profit && (
                <Typography variant="body2">
                  Take Profit: {suggestion.take_profit.toFixed(2)}
                </Typography>
              )}
            </Box>
          </MuiAlert>
        )}

        {/* Timeframe selector */}
        <Box sx={{ mb: 2 }}>
          <ToggleButtonGroup
            value={timeframe}
            exclusive
            onChange={(e, val) => { if (val) setTimeframe(val); }}
            size="small"
            color="primary"
          >
            <ToggleButton value="1m">1m</ToggleButton>
            <ToggleButton value="2m">2m</ToggleButton>
            <ToggleButton value="5m">5m</ToggleButton>
            <ToggleButton value="15m">15m</ToggleButton>
            <ToggleButton value="1h">1h</ToggleButton>
            <ToggleButton value="1d">1d</ToggleButton>
          </ToggleButtonGroup>
          <ToggleButtonGroup
            value={symbol}
            exclusive
            onChange={(e, val) => { if (val) setSymbol(val); }}
            size="small"
            color="secondary"
            sx={{ ml: 2 }}
          >
            {SYMBOLS.map(s => (
              <ToggleButton key={s.value} value={s.value}>{s.label}</ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>
        {isAlertsExpanded ? (
          <Box display="grid" gridTemplateColumns="1fr 400px" gap={2} sx={{ position: 'relative' }}>
            <Paper elevation={3} sx={{ p: 2, height: '70vh' }} key="chart-grid">
              <CandlestickChart 
                candles={candles} 
                highlightedTimestamps={highlightedTimestamps}
                suggestion={suggestion}
              />
            </Paper>
            <Paper elevation={3} sx={{ p: 2, height: '70vh', overflow: 'auto' }}>
              <AlertsPanel 
                alerts={alerts} 
                onAlertHover={setHighlightedTimestamps}
                onExpandChange={setIsAlertsExpanded}
              />
            </Paper>
          </Box>
        ) : (
          <Box sx={{ position: 'relative', width: '100%' }}>
            <Paper elevation={3} sx={{ p: 2, height: '70vh', width: '100%' }} key="chart-full">
              <CandlestickChart 
                candles={candles} 
                highlightedTimestamps={highlightedTimestamps}
                suggestion={suggestion}
              />
            </Paper>
            <Fab
              color="primary"
              size="small"
              onClick={() => setIsAlertsExpanded(true)}
              sx={{
                position: 'absolute',
                right: 16,
                top: 16,
                zIndex: 1000,
              }}
            >
              <NotificationsIcon />
            </Fab>
          </Box>
        )}
      </Container>
    </ThemeProvider>
  );
}

export default App; 