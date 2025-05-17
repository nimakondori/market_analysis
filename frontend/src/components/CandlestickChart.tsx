import { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, UTCTimestamp, SeriesMarker, CrosshairMode, LineStyle } from 'lightweight-charts';
import { Candle } from '../types';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
dayjs.extend(utc);
dayjs.extend(timezone);

interface Props {
  candles: Candle[];
  highlightedTimestamps: string[] | null;
  suggestion?: {
    action: string;
    entry_zone?: [number, number];
    stop_loss?: number;
    take_profit?: number;
  } | null;
}

const CandlestickChart = ({ candles, highlightedTimestamps, suggestion }: Props) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const slLineRef = useRef<ISeriesApi<"Line"> | null>(null);
  const tpLineRef = useRef<ISeriesApi<"Line"> | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

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

    // Create line series for SL and TP
    const slLine = chart.addLineSeries({
      color: '#ef5350',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      lastValueVisible: true,
      priceLineVisible: true,
      priceLineWidth: 1,
    });

    const tpLine = chart.addLineSeries({
      color: '#26a69a',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      lastValueVisible: true,
      priceLineVisible: true,
      priceLineWidth: 1,
    });

    seriesRef.current = candlestickSeries;
    slLineRef.current = slLine;
    tpLineRef.current = tpLine;

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

    // Use ResizeObserver for parent/container size changes
    if (chartContainerRef.current) {
      resizeObserverRef.current = new window.ResizeObserver(() => {
        handleResize();
      });
      resizeObserverRef.current.observe(chartContainerRef.current);
    }

    window.addEventListener('resize', handleResize);
    chartRef.current = chart;

    return () => {
      window.removeEventListener('resize', handleResize);
      if (resizeObserverRef.current && chartContainerRef.current) {
        resizeObserverRef.current.unobserve(chartContainerRef.current);
      }
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
    if (!seriesRef.current || !highlightedTimestamps || highlightedTimestamps.length === 0) {
      // Clear SL and TP lines when not hovering
      if (slLineRef.current) slLineRef.current.setData([]);
      if (tpLineRef.current) tpLineRef.current.setData([]);
      if (seriesRef.current) seriesRef.current.setMarkers([]);
      return;
    }

    const markers: SeriesMarker<UTCTimestamp>[] = highlightedTimestamps.map(ts => {
      const timestamp = dayjs.tz(ts, 'YYYY-MM-DD HH:mm:ss', 'America/New_York').unix() as UTCTimestamp;
      return {
        time: timestamp,
        position: 'aboveBar',
        color: '#2196F3',
        shape: 'circle',
        text: formatTime(timestamp),
      };
    });

    seriesRef.current.setMarkers(markers);

    // Show SL and TP lines if we have a suggestion
    if (suggestion?.stop_loss && suggestion?.take_profit) {
      const timeRange = {
        from: (markers[0].time - 10 * 60) as UTCTimestamp, // 10 minutes before
        to: (markers[markers.length - 1].time + 10 * 60) as UTCTimestamp,   // 10 minutes after
      };

      if (slLineRef.current) {
        slLineRef.current.setData([
          { time: timeRange.from, value: suggestion.stop_loss },
          { time: timeRange.to, value: suggestion.stop_loss },
        ]);
      }

      if (tpLineRef.current) {
        tpLineRef.current.setData([
          { time: timeRange.from, value: suggestion.take_profit },
          { time: timeRange.to, value: suggestion.take_profit },
        ]);
      }
    }

    return () => {
      if (seriesRef.current) {
        seriesRef.current.setMarkers([]);
      }
      if (slLineRef.current) slLineRef.current.setData([]);
      if (tpLineRef.current) tpLineRef.current.setData([]);
    };
  }, [highlightedTimestamps, suggestion]);

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