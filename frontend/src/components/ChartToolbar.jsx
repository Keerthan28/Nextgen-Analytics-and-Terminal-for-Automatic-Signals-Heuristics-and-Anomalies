import { BarChart3, TrendingUp, CandlestickChart } from 'lucide-react';

const TIMEFRAMES = ['1D', '5D', '1M', '3M', '6M', 'YTD', '1Y', 'MAX'];

const CHART_TYPES = [
  { id: 'line', label: 'Line', icon: <TrendingUp size={13} /> },
  { id: 'ohlc', label: 'OHLC', icon: <BarChart3 size={13} /> },
  { id: 'candlestick', label: 'Candle', icon: <CandlestickChart size={13} /> },
];

export default function ChartToolbar({
  chartType,
  timeframe,
  hasOHLC,
  compareMode,
  onChartTypeChange,
  onTimeframeChange,
  onCompareModeToggle,
}) {
  return (
    <div className="toolbar">
      <div className="btn-group">
        {CHART_TYPES.map(ct => (
          <button
            key={ct.id}
            className={`btn ${chartType === ct.id ? 'active' : ''}`}
            onClick={() => onChartTypeChange(ct.id)}
            disabled={['ohlc', 'candlestick'].includes(ct.id) && !hasOHLC}
            title={['ohlc', 'candlestick'].includes(ct.id) && !hasOHLC ? 'Requires OHLC data' : ''}
          >
            {ct.icon} {ct.label}
          </button>
        ))}
      </div>

      <div className="separator" style={{ width: 1, height: 20, background: 'var(--border)' }} />

      <div className="btn-group">
        {TIMEFRAMES.map(tf => (
          <button
            key={tf}
            className={`btn ${timeframe === tf ? 'active' : ''}`}
            onClick={() => onTimeframeChange(timeframe === tf ? null : tf)}
            style={{ padding: '5px 8px', fontSize: 11 }}
          >
            {tf}
          </button>
        ))}
      </div>

      <div className="spacer" />

      <button
        className={`btn ${compareMode ? 'active' : ''}`}
        onClick={onCompareModeToggle}
      >
        Compare
      </button>
    </div>
  );
}
