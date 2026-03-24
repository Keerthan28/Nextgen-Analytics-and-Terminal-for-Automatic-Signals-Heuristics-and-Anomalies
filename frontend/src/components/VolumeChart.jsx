import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { plotlyLayout, plotlyConfig, colors } from '../styles/theme';

export default function VolumeChart({ chartData }) {
  const { data, layout } = useMemo(() => {
    if (!chartData?.volume) return { data: [], layout: {} };

    const x = chartData.x || [];
    const volume = chartData.volume;

    const barColors = [];
    const ohlc = chartData.ohlc;
    if (ohlc?.close) {
      for (let i = 0; i < volume.length; i++) {
        const prev = i > 0 ? ohlc.close[i - 1] : ohlc.close[i];
        barColors.push(ohlc.close[i] >= prev ? colors.green : colors.red);
      }
    } else {
      volume.forEach(() => barColors.push(colors.accent));
    }

    const traces = [{
      x,
      y: volume,
      type: 'bar',
      marker: { color: barColors, opacity: 0.6 },
      name: 'Volume',
      hovertemplate: '%{x}<br>Vol: %{y:,.0f}<extra></extra>',
    }];

    const ly = {
      ...plotlyLayout,
      height: 120,
      margin: { ...plotlyLayout.margin, t: 5, b: 25 },
      yaxis: {
        ...plotlyLayout.yaxis,
        showticklabels: true,
        tickfont: { size: 9 },
      },
      xaxis: {
        ...plotlyLayout.xaxis,
        showticklabels: false,
      },
      showlegend: false,
    };

    return { data: traces, layout: ly };
  }, [chartData]);

  if (!chartData?.volume) return null;

  return (
    <div style={{ height: 120, flexShrink: 0 }}>
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
