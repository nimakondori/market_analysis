import { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, UTCTimestamp, SeriesMarker, CrosshairMode } from 'lightweight-charts';
import { Candle } from '../types';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
dayjs.extend(utc);
dayjs.extend(timezone);

interface Props {
  candles: Candle[];
  highlightedTimestamp: string | null;
}

const CandlestickChart = ({ candles, highlightedTimestamp }: Props) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  const formatTime = (timestamp: number): string => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true,
      timeZone: 'America/New_York'
    });
  };

  const convertCandles = (candles: Candle[]): CandlestickData<UTCTimestamp>[] => {
    return candles.map(candle => {
      const timestamp = dayjs.tz(candle.time, 'YYYY-MM-DD HH:mm:ss', 'America/New_York').unix() as UTCTimestamp;
      return {
        time: timestamp,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close
      };
    }).sort((a, b) => a.time - b.time);
  };

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1e1e1e' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: UTCTimestamp) => formatTime(time),
      },
      localization: {
        timeFormatter: (time: UTCTimestamp) => formatTime(time),
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          labelVisible: true,
          labelBackgroundColor: '#2B2B43',
        },
        horzLine: {
          labelVisible: true,
          labelBackgroundColor: '#2B2B43',
        },
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    seriesRef.current = candlestickSeries;
    const convertedData = convertCandles(candles);
    candlestickSeries.setData(convertedData);

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    chartRef.current = chart;

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    if (seriesRef.current && candles.length > 0) {
      const convertedData = convertCandles(candles);
      seriesRef.current.setData(convertedData);
    }
  }, [candles]);

  useEffect(() => {
    if (!seriesRef.current || !highlightedTimestamp) return;

    const timestamp = dayjs.tz(highlightedTimestamp, 'YYYY-MM-DD HH:mm:ss', 'America/New_York').unix() as UTCTimestamp;
    const markers: SeriesMarker<UTCTimestamp>[] = [{
      time: timestamp,
      position: 'aboveBar',
      color: '#2196F3',
      shape: 'circle',
      text: formatTime(timestamp),
    }];

    seriesRef.current.setMarkers(markers);

    return () => {
      if (seriesRef.current) {
        seriesRef.current.setMarkers([]);
      }
    };
  }, [highlightedTimestamp]);

  return (
    <div
      ref={chartContainerRef}
      style={{
        width: '100%',
        height: '100%',
      }}
    />
  );
};

export default CandlestickChart; 