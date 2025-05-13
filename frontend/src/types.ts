export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Alert {
  id: string;
  timestamp: string;
  message: string;
  type: 'buy' | 'sell' | 'neutral';
  confidence: number;
  stop_loss?: number;
  take_profit?: number;
} 