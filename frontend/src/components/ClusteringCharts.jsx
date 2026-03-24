import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { plotlyLayout, plotlyConfig, chartColors, colors } from '../styles/theme';

export default function ClusteringCharts({ clusterView, pcaResult, kSuggestion, kmeansResult }) {
  if (!pcaResult) {
    return (
      <div className="empty-state" style={{ flex: 1 }}>
        <span style={{ fontSize: 13 }}>Click "Run PCA Analysis" in the Clustering panel to begin</span>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
      {clusterView === 'scree' && <ScreePlot pca={pcaResult} />}
      {clusterView === 'silhouette' && kSuggestion && <SilhouettePlot kData={kSuggestion} />}
      {clusterView === 'clusters' && kmeansResult && <ClusterScatter result={kmeansResult} />}
      {clusterView === 'clusters' && !kmeansResult && (
        <div className="empty-state" style={{ flex: 1 }}>
          <span style={{ fontSize: 13 }}>Adjust PCA components and K, then click "Run K-Means"</span>
        </div>
      )}
    </div>
  );
}


function ScreePlot({ pca }) {
  const data = useMemo(() => {
    const x = pca.explained_variance.map((_, i) => `PC${i + 1}`);
    return [
      {
        x, y: pca.explained_variance.map(v => v * 100),
        type: 'bar', name: 'Individual Variance',
        marker: { color: colors.accent, line: { color: colors.bg, width: 0.5 } },
      },
      {
        x, y: pca.cumulative_variance.map(v => v * 100),
        type: 'scatter', mode: 'lines+markers', name: 'Cumulative Variance',
        line: { color: colors.orange, width: 2.5 },
        marker: { size: 6, color: colors.orange },
        yaxis: 'y2',
      },
    ];
  }, [pca]);

  const layout = useMemo(() => ({
    ...plotlyLayout,
    title: { text: 'Scree Plot — Explained Variance per Principal Component', font: { size: 14, color: colors.textBright }, x: 0.01, y: 0.97, yanchor: 'top' },
    margin: { l: 55, r: 55, t: 60, b: 50 },
    xaxis: { ...plotlyLayout.xaxis, title: { text: 'Principal Component', font: { size: 11, color: colors.textMuted } }, tickfont: { size: 10, color: colors.textMuted }, tickangle: -30 },
    yaxis: { ...plotlyLayout.yaxis, side: 'left', title: { text: 'Individual Variance (%)', font: { size: 11, color: colors.accent } }, tickfont: { size: 10, color: colors.textMuted }, automargin: true },
    yaxis2: { overlaying: 'y', side: 'right', title: { text: 'Cumulative (%)', font: { size: 11, color: colors.orange } }, tickfont: { size: 10, color: colors.orange }, range: [0, 105], showgrid: false },
    legend: { ...plotlyLayout.legend, yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1, font: { size: 10, color: colors.textMuted } },
    showlegend: true,
    hovermode: 'x',
    annotations: pca.suggested_components ? [{
      x: `PC${pca.suggested_components}`, y: pca.cumulative_variance[pca.suggested_components - 1] * 100,
      xref: 'x', yref: 'y2',
      text: `Elbow: ${pca.suggested_components} PCs (${(pca.cumulative_variance[pca.suggested_components - 1] * 100).toFixed(1)}%)`,
      showarrow: true, arrowhead: 2, arrowcolor: colors.green,
      font: { size: 11, color: colors.green },
      ax: 40, ay: -30,
    }] : [],
  }), [pca]);

  return (
    <div style={{ flex: 1, minHeight: 350 }}>
      <Plot data={data} layout={{ ...layout, autosize: true }} config={plotlyConfig} useResizeHandler style={{ width: '100%', height: '100%' }} />
    </div>
  );
}


function SilhouettePlot({ kData }) {
  const data = useMemo(() => [{
    x: kData.scores.map(s => s.k),
    y: kData.scores.map(s => s.silhouette),
    type: 'scatter', mode: 'lines+markers', name: 'Silhouette Score',
    line: { color: colors.cyan, width: 2.5 },
    marker: { size: 8, color: kData.scores.map(s => s.k === kData.suggested_k ? colors.green : colors.cyan) },
    fill: 'tozeroy',
    fillcolor: colors.cyan + '15',
  }], [kData]);

  const layout = useMemo(() => ({
    ...plotlyLayout,
    title: { text: 'Silhouette Score — Optimal Cluster Selection', font: { size: 14, color: colors.textBright }, x: 0.01, y: 0.97, yanchor: 'top' },
    margin: { l: 55, r: 30, t: 60, b: 50 },
    xaxis: { ...plotlyLayout.xaxis, title: { text: 'Number of Clusters (K)', font: { size: 11, color: colors.textMuted } }, tickfont: { size: 10 }, dtick: 1 },
    yaxis: { ...plotlyLayout.yaxis, side: 'left', title: { text: 'Silhouette Score', font: { size: 11, color: colors.textMuted } }, tickfont: { size: 10 }, automargin: true },
    showlegend: false,
    hovermode: 'x',
    annotations: [{
      x: kData.suggested_k, y: kData.scores.find(s => s.k === kData.suggested_k)?.silhouette || 0,
      xref: 'x', yref: 'y',
      text: `Optimal: K=${kData.suggested_k} (sil=${(kData.scores.find(s => s.k === kData.suggested_k)?.silhouette || 0).toFixed(3)})`,
      showarrow: true, arrowhead: 2, arrowcolor: colors.green,
      font: { size: 11, color: colors.green },
      ax: 40, ay: -35,
    }],
  }), [kData]);

  return (
    <div style={{ flex: 1, minHeight: 350 }}>
      <Plot data={data} layout={{ ...layout, autosize: true }} config={plotlyConfig} useResizeHandler style={{ width: '100%', height: '100%' }} />
    </div>
  );
}


function ClusterScatter({ result }) {
  const data = useMemo(() => {
    const clusters = {};
    result.labels.forEach((label, i) => {
      if (!clusters[label]) clusters[label] = { x: [], y: [], text: [] };
      clusters[label].x.push(result.pc1[i]);
      clusters[label].y.push(result.pc2[i]);
      const hoverParts = [`Cluster ${label}`];
      if (result.target_values) hoverParts.push(result.target_values[i]);
      clusters[label].text.push(hoverParts.join(' | '));
    });

    return Object.entries(clusters).map(([label, pts], i) => ({
      x: pts.x, y: pts.y, text: pts.text,
      type: 'scatter', mode: 'markers',
      name: `Cluster ${label} (${pts.x.length})`,
      marker: { color: chartColors[i % chartColors.length], size: 5, opacity: 0.65 },
      hovertemplate: '%{text}<br>%{xaxis.title.text}: %{x:.2f}<br>%{yaxis.title.text}: %{y:.2f}<extra></extra>',
    }));
  }, [result]);

  const layout = useMemo(() => ({
    ...plotlyLayout,
    title: {
      text: `K-Means Clustering — ${result.n_clusters} Clusters (Silhouette: ${result.silhouette_score})`,
      font: { size: 14, color: colors.textBright }, x: 0.01, y: 0.97, yanchor: 'top',
    },
    margin: { l: 55, r: 30, t: 60, b: 55 },
    xaxis: { ...plotlyLayout.xaxis, title: { text: result.pc1_label, font: { size: 12, color: colors.textMuted } }, tickfont: { size: 10 }, automargin: true },
    yaxis: { ...plotlyLayout.yaxis, side: 'left', title: { text: result.pc2_label, font: { size: 12, color: colors.textMuted } }, tickfont: { size: 10 }, automargin: true },
    legend: { ...plotlyLayout.legend, yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1, font: { size: 10, color: colors.textMuted } },
    hovermode: 'closest',
  }), [result]);

  return (
    <div style={{ flex: 1, minHeight: 400 }}>
      <Plot data={data} layout={{ ...layout, autosize: true }} config={plotlyConfig} useResizeHandler style={{ width: '100%', height: '100%' }} />
    </div>
  );
}
