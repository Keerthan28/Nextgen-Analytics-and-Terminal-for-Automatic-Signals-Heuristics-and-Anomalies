import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { plotlyLayout, plotlyConfig, chartColors, colors } from '../styles/theme';

export default function PriceChart({ chartData, chartType, compareMode }) {
  const { data, layout } = useMemo(() => {
    if (!chartData) return { data: [], layout: {} };

    const x = chartData.x || [];
    const traces = [];

    if (['ohlc', 'candlestick'].includes(chartType) && chartData.ohlc) {
      const ohlc = chartData.ohlc;
      const TraceType = chartType === 'ohlc' ? 'ohlc' : 'candlestick';
      traces.push({
        x,
        open: ohlc.open,
        high: ohlc.high,
        low: ohlc.low,
        close: ohlc.close,
        type: TraceType,
        name: 'OHLC',
        increasing: { line: { color: colors.green }, fillcolor: colors.green },
        decreasing: { line: { color: colors.red }, fillcolor: colors.red },
      });
    } else {
      const series = chartData.series || {};
      Object.entries(series).forEach(([name, values], i) => {
        let y = values;
        if (compareMode && values.length > 0) {
          const base = values.find(v => v != null);
          if (base && base !== 0) {
            y = values.map(v => v != null ? ((v / base) - 1) * 100 : null);
          }
        }
        traces.push({
          x,
          y,
          type: 'scatter',
          mode: 'lines',
          name,
          line: { color: chartColors[i % chartColors.length], width: 1.5 },
          hovertemplate: `%{x}<br>${name}: %{y:.2f}<extra></extra>`,
        });
      });
    }

    const indicatorData = chartData.indicators || {};
    const indicatorStyles = {
      sma: { dash: 'dot', width: 1 },
      ema: { dash: 'dashdot', width: 1 },
      bollinger_upper: { dash: 'dash', width: 0.8 },
      bollinger_middle: { dash: 'solid', width: 0.8 },
      bollinger_lower: { dash: 'dash', width: 0.8 },
      macd_macd: { dash: 'solid', width: 1 },
      macd_signal: { dash: 'dot', width: 1 },
    };

    Object.entries(indicatorData).forEach(([key, values]) => {
      if (['rsi_rsi', 'macd_macd', 'macd_signal', 'macd_histogram',
           'volatility_volatility', 'drawdown_drawdown', 'abnormal_volume_abnormal_volume'].includes(key)) {
        return;
      }
      const style = indicatorStyles[key] || { dash: 'dot', width: 1 };
      traces.push({
        x,
        y: values,
        type: 'scatter',
        mode: 'lines',
        name: key.replace(/_/g, ' ').toUpperCase(),
        line: {
          color: key.includes('bollinger') ? colors.purple : colors.cyan,
          ...style,
        },
        opacity: 0.7,
      });
    });

    const ly = {
      ...plotlyLayout,
      margin: { ...plotlyLayout.margin, t: 60, b: 50 },
      yaxis: {
        ...plotlyLayout.yaxis,
        title: compareMode ? '% Change' : '',
        automargin: true,
      },
      xaxis: {
        ...plotlyLayout.xaxis,
        automargin: true,
      },
      legend: {
        ...plotlyLayout.legend,
        yanchor: 'bottom',
        y: 1.03,
        xanchor: 'right',
        x: 1,
      },
    };

    return { data: traces, layout: ly };
  }, [chartData, chartType, compareMode]);

  if (!chartData) return null;

  return (
    <div style={{ flex: 1, minHeight: 0 }}>
      <Plot
        data={data}
        layout={{
          ...layout,
          autosize: true,
        }}
        config={plotlyConfig}
        useResizeHandler
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
}
