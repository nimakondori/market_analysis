import { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { Box, CssBaseline, Container, Paper, Typography, CircularProgress, Alert as MuiAlert, ToggleButton, ToggleButtonGroup } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import CandlestickChart from './components/CandlestickChart';
import AlertsPanel from './components/AlertsPanel';
import { Candle, Alert } from './types';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});

function App() {
  const [timeframe, setTimeframe] = useState<string>('1m');
  const [candles, setCandles] = useState<Candle[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<{ action: string; reason: string; entry_zone?: [number, number]; stop_loss?: number; take_profit?: number } | null>(null);
  const [highlightedTimestamp, setHighlightedTimestamp] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log('Fetching market data...');
        setError(null);
        const response = await fetch(`/api/market-data?interval=${timeframe}`);
        
        console.log('Response status:', response.status);
        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(
            errorData?.detail || 
            `Server error (${response.status}): ${response.statusText}`
          );
        }
        
        const data = await response.json();
        console.log('Received data:', {
          candlesCount: data.candles?.length,
          alertsCount: data.alerts?.length,
          hasSuggestion: !!data.suggestion
        });
        
        if (!data.candles || !Array.isArray(data.candles) || data.candles.length === 0) {
          throw new Error('No market data available');
        }
        
        // Log first candle for debugging
        if (data.candles.length > 0) {
          console.log('Sample candle:', data.candles[0]);
        }
        
        setCandles(data.candles);
        setAlerts(data.alerts || []);
        setSuggestion(data.suggestion);
      } catch (error) {
        console.error('Error fetching data:', error);
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
  }, [timeframe]);

  console.log('App render state:', { loading, hasError: !!error, candlesCount: candles.length });

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Market Analysis Dashboard
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
        </Box>
        <Box display="grid" gridTemplateColumns="1fr 400px" gap={2}>
          <Paper elevation={3} sx={{ p: 2, height: '70vh' }}>
            <CandlestickChart 
              candles={candles} 
              highlightedTimestamp={highlightedTimestamp}
              suggestion={suggestion}
            />
          </Paper>
          <Paper elevation={3} sx={{ p: 2, height: '70vh', overflow: 'auto' }}>
            <AlertsPanel 
              alerts={alerts} 
              onAlertHover={setHighlightedTimestamp}
            />
          </Paper>
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App; 