import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { plotlyLayout, plotlyConfig, chartColors, colors, truncateLabel } from '../styles/theme';

function truncateTickValues(trace) {
  if (!trace.x || !Array.isArray(trace.x)) return trace;
  if (trace.type === 'scatter' || trace.type === 'histogram') return trace;
  const hasLong = trace.x.some(v => typeof v === 'string' && v.length > 18);
  if (!hasLong) return trace;
  return { ...trace, x: trace.x.map(v => truncateLabel(String(v), 18)) };
}

export default function TabularChart({ chartData }) {
  const { data, layout } = useMemo(() => {
    if (!chartData?.traces) return { data: [], layout: {} };

    const traces = chartData.traces.map((t, i) => {
      let base = { ...t };

      if (t.type === 'histogram') {
        base.marker = {
          color: chartColors[i % chartColors.length],
          line: { color: colors.bg, width: 0.5 },
          ...(t.marker || {}),
        };
      } else if (t.type === 'bar') {
        base.marker = {
          color: chartColors[i % chartColors.length],
          line: { color: colors.bg, width: 0.5 },
          ...(t.marker || {}),
        };
        base = truncateTickValues(base);
      } else if (t.type === 'scatter') {
        base.marker = {
          color: chartColors[i % chartColors.length],
          size: 4,
          opacity: 0.6,
          ...(t.marker || {}),
        };
      } else if (t.type === 'box') {
        base.marker = { color: chartColors[i % chartColors.length] };
        base.line = { color: chartColors[i % chartColors.length] };
      } else if (t.type === 'heatmap') {
        base.colorbar = {
          tickfont: { color: colors.textMuted, size: 10 },
          titlefont: { color: colors.text },
        };
        if (base.x) base.x = base.x.map(v => truncateLabel(String(v), 16));
        if (base.y) base.y = base.y.map(v => truncateLabel(String(v), 16));
      } else if (t.type === 'pie') {
        base.marker = {
          colors: chartColors,
          line: { color: colors.bg, width: 2 },
        };
        base.textfont = { color: colors.text, size: 11 };
        if (base.labels) base.labels = base.labels.map(v => truncateLabel(String(v), 22));
      }

      return base;
    });

    const traceCount = traces.filter(t => t.name).length;
    const needsLegend = traceCount > 1;

    const customLayout = {
      ...plotlyLayout,
      title: {
        text: chartData.layout?.title || '',
        font: { size: 13, color: colors.text },
        x: 0.01,
        y: 0.98,
        yanchor: 'top',
      },
      margin: {
        ...plotlyLayout.margin,
        t: needsLegend ? 70 : 50,
        b: 60,
        l: 60,
      },
      xaxis: {
        ...plotlyLayout.xaxis,
        title: { text: chartData.layout?.xaxis_title || '', font: { size: 11, color: colors.textMuted }, standoff: 10 },
        tickangle: -35,
        tickfont: { size: 9, color: colors.textMuted },
        automargin: true,
      },
      yaxis: {
        ...plotlyLayout.yaxis,
        title: { text: chartData.layout?.yaxis_title || '', font: { size: 11, color: colors.textMuted }, standoff: 10 },
        side: 'left',
        tickfont: { size: 9, color: colors.textMuted },
        automargin: true,
      },
      legend: {
        ...plotlyLayout.legend,
        yanchor: 'bottom',
        y: 1.03,
        xanchor: 'right',
        x: 1,
      },
      barmode: chartData.layout?.barmode || 'group',
      height: chartData.layout?.height || undefined,
      showlegend: needsLegend,
    };

    return { data: traces, layout: customLayout };
  }, [chartData]);

  if (!chartData?.traces?.length) {
    return (
      <div className="empty-state" style={{ flex: 1 }}>
        <span style={{ fontSize: 13 }}>Select columns to visualize</span>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, minHeight: 0 }}>
      <Plot
        data={data}
        layout={{ ...layout, autosize: true }}
        config={plotlyConfig}
        useResizeHandler
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
}
