import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { plotlyLayout, plotlyConfig, colors } from '../styles/theme';

export default function SubChart({ chartData, indicatorKey, title }) {
  const { data, layout } = useMemo(() => {
    if (!chartData?.indicators) return { data: [], layout: {} };

    const x = chartData.x || [];
    const traces = [];

    if (indicatorKey === 'rsi') {
      const vals = chartData.indicators['rsi_rsi'];
      if (!vals) return { data: [], layout: {} };
      traces.push({
        x, y: vals,
        type: 'scatter', mode: 'lines',
        name: 'RSI',
        line: { color: colors.purple, width: 1.2 },
      });
      traces.push({
        x, y: Array(x.length).fill(70),
        type: 'scatter', mode: 'lines',
        name: 'Overbought',
        line: { color: colors.red, width: 0.5, dash: 'dash' },
        showlegend: false,
      });
      traces.push({
        x, y: Array(x.length).fill(30),
        type: 'scatter', mode: 'lines',
        name: 'Oversold',
        line: { color: colors.green, width: 0.5, dash: 'dash' },
        showlegend: false,
      });
    } else if (indicatorKey === 'macd') {
      const macdLine = chartData.indicators['macd_macd'];
      const signalLine = chartData.indicators['macd_signal'];
      const hist = chartData.indicators['macd_histogram'];
      if (!macdLine) return { data: [], layout: {} };

      if (hist) {
        traces.push({
          x, y: hist,
          type: 'bar',
          name: 'Histogram',
          marker: {
            color: hist.map(v => v >= 0 ? colors.green : colors.red),
            opacity: 0.5,
          },
        });
      }
      traces.push({
        x, y: macdLine,
        type: 'scatter', mode: 'lines',
        name: 'MACD',
        line: { color: colors.accent, width: 1.2 },
      });
      if (signalLine) {
        traces.push({
          x, y: signalLine,
          type: 'scatter', mode: 'lines',
          name: 'Signal',
          line: { color: colors.orange, width: 1, dash: 'dot' },
        });
      }
    } else if (indicatorKey === 'volatility') {
      const vals = chartData.indicators['volatility_volatility'];
      if (!vals) return { data: [], layout: {} };
      traces.push({
        x, y: vals,
        type: 'scatter', mode: 'lines',
        name: 'Volatility',
        line: { color: colors.orange, width: 1.2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(210,153,34,0.1)',
      });
    } else if (indicatorKey === 'drawdown') {
      const vals = chartData.indicators['drawdown_drawdown'];
      if (!vals) return { data: [], layout: {} };
      traces.push({
        x,
        y: vals.map(v => v != null ? v * 100 : null),
        type: 'scatter', mode: 'lines',
        name: 'Drawdown %',
        line: { color: colors.red, width: 1.2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(248,81,73,0.1)',
      });
    }

    if (traces.length === 0) return { data: [], layout: {} };

    const ly = {
      ...plotlyLayout,
      height: 140,
      margin: { ...plotlyLayout.margin, t: 24, b: 20 },
      title: { text: title, font: { size: 10, color: colors.textMuted }, x: 0.01, y: 0.98, yanchor: 'top' },
      legend: { ...plotlyLayout.legend, yanchor: 'top', y: 0.98, xanchor: 'right', x: 1, font: { size: 9, color: colors.textMuted } },
    };

    return { data: traces, layout: ly };
  }, [chartData, indicatorKey, title]);

  if (data.length === 0) return null;

  return (
    <div style={{ height: 140, flexShrink: 0 }}>
      <Plot
        data={data}
        layout={{ ...layout, autosize: true }}
        config={{ ...plotlyConfig, displayModeBar: false }}
        useResizeHandler
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
}
