import { useState } from 'react';
import { colors } from '../styles/theme';

export default function ClusteringControls({
  numericCols,
  categoryCols,
  columnOrder,
  selectedFeatureColumns,
  toggleFeatureColumn,
  aiClustering,
  aiClusteringLoading,
  fetchClusteringFeaturesAI,
  pcaResult, kSuggestion, kmeansResult,
  nComponents, setNComponents,
  nClusters, setNClusters,
  clusterLoading, clusterError, clusterView, setClusterView,
  runPCAAnalysis, runKMeansAnalysis, resetClustering,
  onOpenEncodingTab,
}) {
  const [showFeatures, setShowFeatures] = useState(false);
  const canRun = columnOrder?.length > 0 && selectedFeatureColumns.length > 0;
  const hasCategoricalSelected = selectedFeatureColumns.some((c) => categoryCols.includes(c));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: colors.textBright, borderBottom: `1px solid ${colors.border}`, paddingBottom: 6 }}>
        PCA + K-Means
      </div>

      {(!columnOrder || columnOrder.length === 0) && (
        <div style={{ fontSize: 10, color: colors.orange }}>No feature columns in schema.</div>
      )}

      {columnOrder?.length > 0 && !pcaResult && (
        <>
          <button
            onClick={fetchClusteringFeaturesAI}
            disabled={!!aiClusteringLoading}
            style={{ ...btnStyle, borderColor: colors.cyan, color: colors.cyan, background: colors.cyan + '15' }}
          >
            {aiClusteringLoading ? 'AI selecting columns…' : 'AI: suggest numeric columns'}
          </button>

          {aiClustering?.reason && (
            <div style={{ fontSize: 9, color: colors.textMuted, background: colors.bgTertiary, padding: 8, borderRadius: 5, borderLeft: `3px solid ${colors.cyan}` }}>
              <span style={{ color: colors.cyan, fontWeight: 600 }}>AI </span>
              {aiClustering.reason}
              {aiClustering.confidence != null && (
                <span style={{ color: colors.textMuted }}> · confidence {(Number(aiClustering.confidence) * 100).toFixed(0)}%</span>
              )}
            </div>
          )}

          <div style={{ fontSize: 9, fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Features ({selectedFeatureColumns.length}/{columnOrder.length})
          </div>
          {categoryCols?.length > 0 && (
            <div style={{
              fontSize: 9, lineHeight: 1.5, color: colors.textMuted,
              background: colors.bgTertiary, padding: 8, borderRadius: 5,
              borderLeft: `3px solid ${colors.orange}`,
            }}>
              <span style={{ fontWeight: 600, color: colors.orange }}>Categorical columns</span>{' '}
              can be included in clustering after encoding.{' '}
              <button
                type="button"
                onClick={() => onOpenEncodingTab?.()}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: colors.orange, fontWeight: 600, padding: 0,
                  textDecoration: 'underline', fontSize: 9,
                }}
              >
                Open Encoding tab
              </button>{' '}
              to configure how each categorical column is converted to numbers (binary, one-hot, label, frequency, etc.).
            </div>
          )}
          {hasCategoricalSelected && (
            <div style={{ fontSize: 8, color: colors.purple, lineHeight: 1.35 }}>
              Selected categorical columns will use your encoding settings. Target encoding becomes frequency for clustering.
            </div>
          )}
          <button
            type="button"
            onClick={() => setShowFeatures((s) => !s)}
            style={{ fontSize: 9, color: colors.accent, background: 'none', border: 'none', cursor: 'pointer', padding: 0, textAlign: 'left', textDecoration: 'underline' }}
          >
            {showFeatures ? 'Hide column list' : 'Include / exclude columns (numeric + categorical)'}
          </button>
          {showFeatures && (
            <div style={{ maxHeight: 220, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
              {columnOrder.map((col) => {
                const on = selectedFeatureColumns.includes(col);
                const role = numericCols.includes(col) ? 'num' : 'cat';
                return (
                  <label key={col} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 9, color: on ? colors.text : colors.textMuted }}>
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() => toggleFeatureColumn(col)}
                      style={{ accentColor: colors.accent, width: 12, height: 12 }}
                    />
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: role === 'num' ? colors.green : colors.orange, minWidth: 22 }}>{role}</span>
                    <span style={{ textDecoration: on ? 'none' : 'line-through' }}>{col}</span>
                  </label>
                );
              })}
            </div>
          )}

          <button onClick={runPCAAnalysis} disabled={!!clusterLoading || !canRun} style={btnStyle}>
            {clusterLoading === 'pca' ? 'Computing PCA…' : 'Run PCA Analysis'}
          </button>
        </>
      )}

      {clusterError && (
        <div style={{ fontSize: 11, color: colors.red, background: colors.bgSecondary, padding: 8, borderRadius: 4 }}>{clusterError}</div>
      )}

      {pcaResult && (
        <>
          <button
            type="button"
            onClick={resetClustering}
            style={{ fontSize: 9, color: colors.textMuted, background: 'transparent', border: 'none', cursor: 'pointer', textDecoration: 'underline', alignSelf: 'flex-start', padding: 0 }}
          >
            Change columns & re-run PCA
          </button>
          <div style={{ fontSize: 9, color: colors.textMuted }}>
            Using {pcaResult.feature_names?.length ?? 0} feature(s): {pcaResult.feature_names?.slice(0, 4).join(', ')}
            {(pcaResult.feature_names?.length || 0) > 4 ? '…' : ''}
          </div>
          {pcaResult.encoding_notes?.length > 0 && (
            <div style={{ fontSize: 8, color: colors.orange }}>{pcaResult.encoding_notes.join(' · ')}</div>
          )}

          <div style={{ display: 'flex', gap: 3 }}>
            <TabBtn active={clusterView === 'scree'} onClick={() => setClusterView('scree')}>Scree</TabBtn>
            <TabBtn active={clusterView === 'silhouette'} onClick={() => setClusterView('silhouette')}>Silhouette</TabBtn>
            <TabBtn active={clusterView === 'clusters'} onClick={() => setClusterView('clusters')}>Clusters</TabBtn>
          </div>

          <div style={{ background: colors.bgTertiary, borderRadius: 6, padding: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: colors.textBright }}>Configuration</div>

            <label style={labelStyle}>
              <span>PCA Components</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="range" min={2} max={pcaResult.max_components}
                  value={nComponents} onChange={e => setNComponents(+e.target.value)}
                  style={{ flex: 1, accentColor: colors.accent }} />
                <span style={{ fontSize: 11, color: colors.accent, minWidth: 18, textAlign: 'right' }}>{nComponents}</span>
              </div>
              <span style={{ fontSize: 9, color: colors.textMuted }}>
                Suggested: {pcaResult.suggested_components} (≥80% var)
              </span>
            </label>

            <label style={labelStyle}>
              <span>Clusters (K)</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="range" min={2} max={15}
                  value={nClusters} onChange={e => setNClusters(+e.target.value)}
                  style={{ flex: 1, accentColor: colors.cyan }} />
                <span style={{ fontSize: 11, color: colors.cyan, minWidth: 18, textAlign: 'right' }}>{nClusters}</span>
              </div>
              {kSuggestion && (
                <span style={{ fontSize: 9, color: colors.textMuted }}>
                  Best silhouette: k={kSuggestion.suggested_k}
                </span>
              )}
            </label>

            <button onClick={runKMeansAnalysis} disabled={clusterLoading === 'kmeans'} style={btnStyle}>
              {clusterLoading === 'kmeans' ? 'Clustering…' : `Run K-Means (K=${nClusters}, ${nComponents} PCs)`}
            </button>
          </div>

          {kmeansResult && <ClusterSummary result={kmeansResult} />}
        </>
      )}
    </div>
  );
}

function TabBtn({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{
      flex: 1, padding: '5px 0', fontSize: 9, fontWeight: 600, cursor: 'pointer',
      border: `1px solid ${active ? colors.accent : colors.border}`,
      background: active ? colors.accent + '22' : 'transparent',
      color: active ? colors.accent : colors.textMuted,
      borderRadius: 4,
    }}>{children}</button>
  );
}

function ClusterSummary({ result }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: colors.textBright }}>
        Cluster Summary (sil: {result.silhouette_score})
      </div>
      {result.cluster_summary.map(c => {
        const clrIdx = c.cluster % 10;
        const clr = ['#58a6ff','#3fb950','#f0883e','#bc8cff','#39d2c0','#f85149','#d29922','#79c0ff','#56d364','#db6d28'][clrIdx];
        return (
          <div key={c.cluster} style={{
            background: colors.bgTertiary, borderRadius: 4, padding: 7,
            borderLeft: `3px solid ${clr}`,
          }}>
            <div style={{ fontWeight: 600, color: colors.text, fontSize: 10 }}>
              Cluster {c.cluster} — {c.size} pts
            </div>
            {c.target_distribution && (
              <div style={{ color: colors.textMuted, fontSize: 9, marginTop: 2 }}>
                {Object.entries(c.target_distribution).map(([k, v]) => `${k}: ${v}`).join(' · ')}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const btnStyle = {
  padding: '7px 10px', fontSize: 10, fontWeight: 600, cursor: 'pointer',
  border: `1px solid ${colors.accent}`, background: colors.accent + '18',
  color: colors.accent, borderRadius: 6,
};

const labelStyle = {
  display: 'flex', flexDirection: 'column', gap: 3, fontSize: 10, color: colors.textMuted,
};
