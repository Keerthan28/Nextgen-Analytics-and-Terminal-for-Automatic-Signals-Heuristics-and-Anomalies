import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { plotlyLayout, plotlyConfig, chartColors, colors } from '../styles/theme';

export default function MLCharts({ mlResults, currentResult }) {
  if (!mlResults) {
    return (
      <div className="empty-state" style={{ flex: 1 }}>
        <span style={{ fontSize: 13 }}>Configure and train models in the ML panel to view results</span>
      </div>
    );
  }

  if (!currentResult) {
    return (
      <div className="empty-state" style={{ flex: 1 }}>
        <span style={{ fontSize: 13 }}>Select a model to view results</span>
      </div>
    );
  }

  const isRegression = mlResults.task_type === 'regression';

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
      <ModelComparison mlResults={mlResults} />
      <div style={{ display: 'flex', flex: 1, minHeight: 350, gap: 4 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {isRegression ? <PredictedVsActual result={currentResult} /> : <ConfusionMatrix result={currentResult} />}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <FeatureImportance result={currentResult} />
        </div>
      </div>
      {!isRegression && <PerClassMetrics result={currentResult} />}
      {isRegression && <ResidualsPlot result={currentResult} />}
    </div>
  );
}


function ModelComparison({ mlResults }) {
  const isReg = mlResults.task_type === 'regression';

  const data = useMemo(() => {
    const models = [];
    Object.entries(mlResults.models).forEach(([key, r]) => {
      if (r.error) return;
      models.push({ key, name: r.model_name, metrics: r.metrics });
    });

    const metricDefs = isReg
      ? [{ key: 'r2', label: 'R²', color: colors.accent }, { key: 'cv_mean', label: 'CV R²', color: colors.green }]
      : [
          { key: 'accuracy', label: 'Accuracy', color: colors.accent },
          { key: 'precision', label: 'Precision', color: colors.green },
          { key: 'recall', label: 'Recall', color: colors.orange },
          { key: 'f1', label: 'F1', color: colors.purple },
          { key: 'roc_auc', label: 'ROC-AUC', color: colors.cyan },
        ];

    return metricDefs.map(md => ({
      x: models.map(m => m.name),
      y: models.map(m => m.metrics[md.key] || 0),
      type: 'bar', name: md.label,
      marker: { color: md.color, line: { color: colors.bg, width: 0.5 } },
    }));
  }, [mlResults, isReg]);

  const layout = useMemo(() => ({
    ...plotlyLayout,
    title: { text: 'Model Comparison', font: { size: 14, color: colors.textBright }, x: 0.01, y: 0.97, yanchor: 'top' },
    height: 220,
    margin: { l: 45, r: 20, t: 50, b: 50 },
    barmode: 'group',
    xaxis: { ...plotlyLayout.xaxis, tickfont: { size: 10 }, automargin: true },
    yaxis: { ...plotlyLayout.yaxis, side: 'left', range: isReg ? undefined : [0, 1.05], tickfont: { size: 9 }, automargin: true, title: { text: 'Score', font: { size: 10 } } },
    legend: { ...plotlyLayout.legend, yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1, font: { size: 8, color: colors.textMuted }, orientation: 'h' },
  }), [isReg]);

  return (
    <div style={{ flexShrink: 0, height: 220 }}>
      <Plot data={data} layout={{ ...layout, autosize: true }} config={{ ...plotlyConfig, displayModeBar: false }} useResizeHandler style={{ width: '100%', height: '100%' }} />
    </div>
  );
}


function ConfusionMatrix({ result }) {
  const { data, layout } = useMemo(() => {
    const cm = result.confusion_matrix;
    const names = result.class_names;
    const zText = cm.map(row => row.map(v => String(v)));
    return {
      data: [{ type: 'heatmap', z: cm, x: names, y: names, text: zText, texttemplate: '%{text}',
        textfont: { color: colors.textBright, size: 12 },
        colorscale: [[0, colors.bg], [0.5, colors.accent + '88'], [1, colors.accent]],
        showscale: false, hovertemplate: 'True: %{y}<br>Predicted: %{x}<br>Count: %{z}<extra></extra>' }],
      layout: { ...plotlyLayout,
        title: { text: `Confusion Matrix — ${result.model_name}`, font: { size: 13, color: colors.textBright }, x: 0.01, y: 0.97, yanchor: 'top' },
        margin: { l: 70, r: 20, t: 50, b: 60 },
        xaxis: { ...plotlyLayout.xaxis, title: { text: 'Predicted', font: { size: 10 } }, tickfont: { size: 9 }, automargin: true, side: 'bottom' },
        yaxis: { ...plotlyLayout.yaxis, title: { text: 'Actual', font: { size: 10 } }, tickfont: { size: 9 }, automargin: true, side: 'left', autorange: 'reversed' },
      },
    };
  }, [result]);

  return <Plot data={data} layout={{ ...layout, autosize: true }} config={{ ...plotlyConfig, displayModeBar: false }} useResizeHandler style={{ width: '100%', height: '100%' }} />;
}


function PredictedVsActual({ result }) {
  const { data, layout } = useMemo(() => {
    const yt = result.y_test || [];
    const yp = result.y_pred || [];
    if (!yt.length) return { data: [], layout: {} };

    const minVal = Math.min(...yt, ...yp);
    const maxVal = Math.max(...yt, ...yp);

    return {
      data: [
        { x: yt, y: yp, type: 'scatter', mode: 'markers', name: 'Predictions',
          marker: { color: colors.accent, size: 4, opacity: 0.5 },
          hovertemplate: 'Actual: %{x:.2f}<br>Predicted: %{y:.2f}<extra></extra>' },
        { x: [minVal, maxVal], y: [minVal, maxVal], type: 'scatter', mode: 'lines', name: 'Perfect',
          line: { color: colors.green, dash: 'dash', width: 1.5 } },
      ],
      layout: { ...plotlyLayout,
        title: { text: `Predicted vs Actual — ${result.model_name}`, font: { size: 13, color: colors.textBright }, x: 0.01, y: 0.97, yanchor: 'top' },
        margin: { l: 55, r: 20, t: 50, b: 50 },
        xaxis: { ...plotlyLayout.xaxis, title: { text: 'Actual', font: { size: 10 } }, tickfont: { size: 9 }, automargin: true },
        yaxis: { ...plotlyLayout.yaxis, side: 'left', title: { text: 'Predicted', font: { size: 10 } }, tickfont: { size: 9 }, automargin: true },
        legend: { ...plotlyLayout.legend, yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
        hovermode: 'closest',
      },
    };
  }, [result]);

  if (!data.length) return <div className="empty-state"><span style={{ fontSize: 11 }}>No prediction data</span></div>;
  return <Plot data={data} layout={{ ...layout, autosize: true }} config={{ ...plotlyConfig, displayModeBar: false }} useResizeHandler style={{ width: '100%', height: '100%' }} />;
}


function FeatureImportance({ result }) {
  const { data, layout } = useMemo(() => {
    const fi = (result.feature_importance || []).slice(0, 15).reverse();
    if (!fi.length) return { data: [], layout: {} };
    return {
      data: [{ type: 'bar', y: fi.map(f => f.feature), x: fi.map(f => f.importance), orientation: 'h',
        marker: { color: fi.map((_, i) => chartColors[(fi.length - 1 - i) % chartColors.length]), line: { color: colors.bg, width: 0.5 } },
        hovertemplate: '%{y}: %{x:.4f}<extra></extra>' }],
      layout: { ...plotlyLayout,
        title: { text: 'Feature Importance', font: { size: 13, color: colors.textBright }, x: 0.01, y: 0.97, yanchor: 'top' },
        margin: { l: 110, r: 20, t: 50, b: 40 },
        xaxis: { ...plotlyLayout.xaxis, title: { text: 'Importance', font: { size: 10 } }, tickfont: { size: 9 }, automargin: true },
        yaxis: { ...plotlyLayout.yaxis, side: 'left', tickfont: { size: 8 }, automargin: true },
        showlegend: false },
    };
  }, [result]);

  if (!data.length) return <div className="empty-state"><span style={{ fontSize: 11 }}>No feature importance</span></div>;
  return <Plot data={data} layout={{ ...layout, autosize: true }} config={{ ...plotlyConfig, displayModeBar: false }} useResizeHandler style={{ width: '100%', height: '100%' }} />;
}


function PerClassMetrics({ result }) {
  const { data, layout } = useMemo(() => {
    const pc = result.per_class_metrics;
    if (!pc || !Object.keys(pc).length) return { data: [], layout: {} };
    const classes = Object.keys(pc);
    return {
      data: [
        { x: classes, y: classes.map(c => pc[c].precision), type: 'bar', name: 'Precision', marker: { color: colors.green } },
        { x: classes, y: classes.map(c => pc[c].recall), type: 'bar', name: 'Recall', marker: { color: colors.orange } },
        { x: classes, y: classes.map(c => pc[c].f1), type: 'bar', name: 'F1', marker: { color: colors.purple } },
      ],
      layout: { ...plotlyLayout,
        title: { text: 'Per-Class Performance', font: { size: 13, color: colors.textBright }, x: 0.01, y: 0.97, yanchor: 'top' },
        height: 200, margin: { l: 45, r: 20, t: 50, b: 45 }, barmode: 'group',
        xaxis: { ...plotlyLayout.xaxis, tickfont: { size: 9 }, automargin: true },
        yaxis: { ...plotlyLayout.yaxis, side: 'left', range: [0, 1.05], tickfont: { size: 9 }, automargin: true },
        legend: { ...plotlyLayout.legend, yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1, font: { size: 9 }, orientation: 'h' },
      },
    };
  }, [result]);

  if (!data.length) return null;
  return <div style={{ flexShrink: 0, height: 200 }}><Plot data={data} layout={{ ...layout, autosize: true }} config={{ ...plotlyConfig, displayModeBar: false }} useResizeHandler style={{ width: '100%', height: '100%' }} /></div>;
}


function ResidualsPlot({ result }) {
  const { data, layout } = useMemo(() => {
    const residuals = result.residuals || [];
    if (!residuals.length) return { data: [], layout: {} };
    return {
      data: [{ type: 'histogram', x: residuals, nbinsx: 50, marker: { color: colors.accent, line: { color: colors.bg, width: 0.5 } }, opacity: 0.8, name: 'Residuals' }],
      layout: { ...plotlyLayout,
        title: { text: 'Residuals Distribution', font: { size: 13, color: colors.textBright }, x: 0.01, y: 0.97, yanchor: 'top' },
        height: 200, margin: { l: 45, r: 20, t: 50, b: 45 },
        xaxis: { ...plotlyLayout.xaxis, title: { text: 'Residual (Actual - Predicted)', font: { size: 10 } }, tickfont: { size: 9 }, automargin: true },
        yaxis: { ...plotlyLayout.yaxis, side: 'left', title: { text: 'Count', font: { size: 10 } }, tickfont: { size: 9 }, automargin: true },
        showlegend: false },
    };
  }, [result]);

  if (!data.length) return null;
  return <div style={{ flexShrink: 0, height: 200 }}><Plot data={data} layout={{ ...layout, autosize: true }} config={{ ...plotlyConfig, displayModeBar: false }} useResizeHandler style={{ width: '100%', height: '100%' }} /></div>;
}
