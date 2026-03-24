import { useState } from 'react';
import { colors } from '../styles/theme';

export default function MLControls({
  aiConfig, aiLoading, fetchAIConfig,
  targetColumn, setTargetColumn,
  taskType, setTaskType,
  excludeColumns, toggleExcludeColumn,
  selectedModelTypes, toggleModelType,
  preliminary, mlResults, selectedModel, setSelectedModel,
  currentResult, mlLoading, mlError,
  runPreliminary, trainModels,
  availableModels, allColumns,
  encodedFeatureNames,
  onOpenEncodingTab,
}) {
  const [showColumns, setShowColumns] = useState(false);
  const [showEncoded, setShowEncoded] = useState(false);
  const allTargetOptions = [...allColumns, ...(targetColumn && !allColumns.includes(targetColumn) ? [targetColumn] : [])];
  const hasEncoded = encodedFeatureNames && encodedFeatureNames.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 12, fontSize: 10 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: colors.textBright, borderBottom: `1px solid ${colors.border}`, paddingBottom: 6 }}>
        ML Configuration
      </div>

      {/* AI Config Button */}
      {!aiConfig && !aiLoading && (
        <button onClick={fetchAIConfig} style={{ ...btnStyle, borderColor: colors.cyan, color: colors.cyan, background: colors.cyan + '15' }}>
          Ask AI to detect target + task type
        </button>
      )}
      {aiLoading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: colors.cyan }}>
          <div className="spinner" style={{ width: 10, height: 10 }} /> Gemini analyzing…
        </div>
      )}
      {aiConfig && <AIConfigCard config={aiConfig} />}

      {/* Target Column */}
      <Section title="Target Column">
        <select className="select" style={{ width: '100%', fontSize: 10 }}
          value={targetColumn || ''} onChange={e => { setTargetColumn(e.target.value || null); }}>
          <option value="">— Select target —</option>
          {allTargetOptions.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </Section>

      {/* Task Type */}
      <Section title="Task Type">
        <div style={{ display: 'flex', gap: 4 }}>
          <ToggleBtn active={taskType === 'classification'} onClick={() => setTaskType('classification')} accent={colors.accent}>Classification</ToggleBtn>
          <ToggleBtn active={taskType === 'regression'} onClick={() => setTaskType('regression')} accent={colors.orange}>Regression</ToggleBtn>
        </div>
      </Section>

      {/* Encoding status */}
      {hasEncoded ? (
        <div style={{
          fontSize: 9, lineHeight: 1.4, padding: 8, borderRadius: 6,
          background: colors.green + '12', border: `1px solid ${colors.green}33`,
        }}>
          <span style={{ color: colors.green, fontWeight: 600 }}>Encoded </span>
          <span style={{ color: colors.text }}>
            {allColumns.length} raw columns → <b>{encodedFeatureNames.length}</b> features.{' '}
          </span>
          <button
            type="button"
            onClick={() => onOpenEncodingTab?.()}
            style={{ background: 'none', border: 'none', color: colors.orange, cursor: 'pointer', textDecoration: 'underline', padding: 0, fontSize: 9, fontWeight: 600 }}
          >
            Change encodings
          </button>
        </div>
      ) : (
        <div style={{ fontSize: 9, color: colors.textMuted, lineHeight: 1.4, background: colors.bgTertiary, padding: 8, borderRadius: 6 }}>
          <span style={{ color: colors.orange, fontWeight: 600 }}>Not encoded yet. </span>
          Go to the{' '}
          <button
            type="button"
            onClick={() => onOpenEncodingTab?.()}
            style={{ background: 'none', border: 'none', color: colors.orange, cursor: 'pointer', textDecoration: 'underline', padding: 0, fontSize: 9, fontWeight: 600 }}
          >
            Encoding
          </button>
          {' '}tab to configure and apply encodings before training.
        </div>
      )}

      {/* Encoded feature list */}
      {hasEncoded && (
        <Section title={`Encoded Features (${encodedFeatureNames.length})`}>
          <button onClick={() => setShowEncoded(p => !p)} style={linkBtnStyle}>
            {showEncoded ? 'Hide encoded features' : 'Show all encoded feature names'}
          </button>
          {showEncoded && (
            <div style={{ maxHeight: 180, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 2, marginTop: 4 }}>
              {encodedFeatureNames.map(name => (
                <div key={name} style={{ fontSize: 8, color: colors.text, fontFamily: 'JetBrains Mono, monospace', padding: '1px 0' }}>
                  {name}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* Columns to Exclude (raw) */}
      <Section title={`Raw Columns (${allColumns.length - excludeColumns.length} of ${allColumns.length} included)`}>
        <button onClick={() => setShowColumns(p => !p)} style={linkBtnStyle}>
          {showColumns ? 'Hide columns' : 'Show columns to include/exclude'}
        </button>
        {showColumns && (
          <div style={{ maxHeight: 160, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 2, marginTop: 4 }}>
            {allColumns.map(col => {
              const excluded = excludeColumns.includes(col);
              return (
                <label key={col} style={{ display: 'flex', alignItems: 'center', gap: 5, cursor: 'pointer', color: excluded ? colors.textMuted : colors.text, fontSize: 9 }}>
                  <input type="checkbox" checked={!excluded} onChange={() => toggleExcludeColumn(col)}
                    style={{ accentColor: colors.accent, width: 12, height: 12 }} />
                  <span style={{ textDecoration: excluded ? 'line-through' : 'none' }}>{col}</span>
                </label>
              );
            })}
          </div>
        )}
        {excludeColumns.length > 0 && (
          <div style={{ fontSize: 8, color: colors.orange, marginTop: 2 }}>
            Excluded: {excludeColumns.join(', ')}
          </div>
        )}
      </Section>

      {/* Model Selection */}
      <Section title="Algorithms">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {availableModels.map(m => {
            const checked = selectedModelTypes.includes(m.id);
            return (
              <label key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 5, cursor: 'pointer', fontSize: 9 }}>
                <input type="checkbox" checked={checked} onChange={() => toggleModelType(m.id)}
                  style={{ accentColor: colors.purple, width: 12, height: 12 }} />
                <span style={{ color: checked ? colors.text : colors.textMuted }}>{m.name}</span>
              </label>
            );
          })}
        </div>
      </Section>

      {/* Preliminary */}
      <button onClick={runPreliminary} disabled={!targetColumn || mlLoading === 'preliminary'} style={btnStyle}>
        {mlLoading === 'preliminary' ? 'Analyzing…' : 'Run Preliminary Analysis'}
      </button>

      {mlError && (
        <div style={{ color: colors.red, background: colors.bgSecondary, padding: 6, borderRadius: 4 }}>{mlError}</div>
      )}

      {preliminary && <PreliminaryCard data={preliminary} />}

      {/* Train */}
      {preliminary?.ready && (
        <button onClick={trainModels}
          disabled={mlLoading === 'training' || selectedModelTypes.length === 0}
          style={{ ...btnStyle, borderColor: colors.green, color: colors.green, background: colors.green + '15' }}>
          {mlLoading === 'training'
            ? `Training ${selectedModelTypes.length} model(s)…`
            : `Train ${selectedModelTypes.length} Model(s)`}
        </button>
      )}

      {mlLoading === 'training' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: colors.textMuted }}>
          <div className="spinner" style={{ width: 10, height: 10 }} /> Training in progress…
        </div>
      )}

      {/* Results */}
      {mlResults && (
        <>
          <Section title="Results">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {Object.entries(mlResults.models).map(([key, r]) => {
                if (r.error) return <div key={key} style={{ color: colors.red, fontSize: 9 }}>{key}: {r.error}</div>;
                const isBest = key === mlResults.best_model;
                const isActive = key === selectedModel;
                const scoreKey = mlResults.task_type === 'classification' ? 'f1' : 'r2';
                const scoreLabel = mlResults.task_type === 'classification' ? 'F1' : 'R²';
                return (
                  <button key={key} onClick={() => setSelectedModel(key)} style={{
                    padding: '5px 8px', fontSize: 9, textAlign: 'left', cursor: 'pointer',
                    border: `1px solid ${isActive ? colors.accent : colors.border}`,
                    background: isActive ? colors.accent + '18' : colors.bgTertiary,
                    color: isActive ? colors.accent : colors.text,
                    borderRadius: 4, display: 'flex', justifyContent: 'space-between',
                  }}>
                    <span>{r.model_name}</span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                      {scoreLabel}: {r.metrics?.[scoreKey]?.toFixed(3)}
                      {isBest && <span style={{ color: colors.green, marginLeft: 3 }}>BEST</span>}
                    </span>
                  </button>
                );
              })}
            </div>
          </Section>

          {currentResult && <MetricsSummary result={currentResult} taskType={mlResults.task_type} />}
        </>
      )}
    </div>
  );
}


function AIConfigCard({ config }) {
  if (!config || !config.target_column) return null;
  return (
    <div style={{ background: colors.cyan + '12', border: `1px solid ${colors.cyan}33`, borderRadius: 5, padding: 8, fontSize: 9 }}>
      <div style={{ fontWeight: 600, color: colors.cyan, marginBottom: 4 }}>AI Recommendation</div>
      <div style={{ color: colors.text }}>Target: <b>{config.target_column}</b> — {config.reason_target}</div>
      <div style={{ color: colors.text }}>Task: <b>{config.task_type}</b> — {config.reason_task}</div>
      {config.exclude_columns?.length > 0 && (
        <div style={{ color: colors.orange, marginTop: 2 }}>Exclude: {config.exclude_columns.join(', ')}</div>
      )}
      {config.recommended_models?.length > 0 && (
        <div style={{ color: colors.purple, marginTop: 2 }}>Models: {config.recommended_models.join(', ')}</div>
      )}
      {config.confidence != null && (
        <div style={{ color: colors.textMuted, marginTop: 2 }}>Confidence: {(config.confidence * 100).toFixed(0)}%</div>
      )}
    </div>
  );
}


function Section({ title, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ fontSize: 9, fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 }}>{title}</div>
      {children}
    </div>
  );
}


function ToggleBtn({ active, onClick, children, accent }) {
  return (
    <button onClick={onClick} style={{
      flex: 1, padding: '4px 0', fontSize: 9, fontWeight: 600, cursor: 'pointer',
      border: `1px solid ${active ? accent : colors.border}`,
      background: active ? accent + '22' : 'transparent',
      color: active ? accent : colors.textMuted,
      borderRadius: 4,
    }}>{children}</button>
  );
}


function PreliminaryCard({ data }) {
  return (
    <div style={{ background: colors.bgTertiary, borderRadius: 5, padding: 8, fontSize: 9 }}>
      <div style={{ fontWeight: 600, color: colors.textBright, marginBottom: 4 }}>Data Readiness</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 10px', marginBottom: 4 }}>
        <Stat label="Rows" value={data.rows} />
        <Stat label="Features" value={data.total_features} />
        <Stat label="Task" value={data.task_type} />
        {data.n_classes && <Stat label="Classes" value={data.n_classes} />}
        {data.minority_class_pct != null && <Stat label="Minority" value={`${data.minority_class_pct}%`} />}
      </div>

      {data.class_distribution && (
        <div style={{ color: colors.textMuted, fontSize: 8, marginBottom: 3 }}>
          {Object.entries(data.class_distribution).map(([k, v]) => `${k}: ${v}`).join(' · ')}
        </div>
      )}
      {data.target_stats && (
        <div style={{ color: colors.textMuted, fontSize: 8, marginBottom: 3 }}>
          Mean: {data.target_stats.mean} · Std: {data.target_stats.std} · Range: [{data.target_stats.min}, {data.target_stats.max}]
        </div>
      )}

      {data.issues?.map((issue, i) => (
        <div key={i} style={{ color: colors.orange, fontSize: 8, marginBottom: 1 }}>⚠ {issue}</div>
      ))}
      {data.leakage_columns?.length > 0 && (
        <div style={{ color: colors.red, fontSize: 8, marginTop: 2 }}>Auto-excluded leaky: {data.leakage_columns.join(', ')}</div>
      )}

      <div style={{
        marginTop: 4, padding: '2px 6px', borderRadius: 3, display: 'inline-block', fontSize: 8, fontWeight: 600,
        background: data.ready ? colors.green + '22' : colors.red + '22',
        color: data.ready ? colors.green : colors.red,
      }}>
        {data.ready ? 'Ready' : 'Not ready'}
      </div>
    </div>
  );
}


function MetricsSummary({ result, taskType }) {
  const m = result.metrics;
  return (
    <div style={{ background: colors.bgTertiary, borderRadius: 5, padding: 8, fontSize: 9 }}>
      <div style={{ fontWeight: 600, color: colors.textBright, marginBottom: 4 }}>{result.model_name}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 10px' }}>
        {taskType === 'classification' ? (
          <>
            <Stat label="Accuracy" value={m.accuracy?.toFixed(3)} />
            <Stat label="Precision" value={m.precision?.toFixed(3)} />
            <Stat label="Recall" value={m.recall?.toFixed(3)} />
            <Stat label="F1" value={m.f1?.toFixed(3)} />
            {m.roc_auc && <Stat label="ROC-AUC" value={m.roc_auc?.toFixed(3)} />}
          </>
        ) : (
          <>
            <Stat label="R²" value={m.r2?.toFixed(3)} />
            <Stat label="RMSE" value={m.rmse?.toFixed(3)} />
            <Stat label="MAE" value={m.mae?.toFixed(3)} />
          </>
        )}
        <Stat label="CV" value={`${m.cv_mean?.toFixed(3)} ± ${m.cv_std?.toFixed(3)}`} />
      </div>
      <div style={{ color: colors.textMuted, fontSize: 8, marginTop: 3 }}>
        Train: {result.train_size} · Test: {result.test_size} · Features: {result.features_used?.length || '?'}
      </div>
    </div>
  );
}


function Stat({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
      <span style={{ color: colors.textMuted }}>{label}</span>
      <span style={{ color: colors.text, fontFamily: 'JetBrains Mono, monospace' }}>{value}</span>
    </div>
  );
}


const btnStyle = {
  padding: '7px 10px', fontSize: 10, fontWeight: 600, cursor: 'pointer',
  border: `1px solid ${colors.purple}`, background: colors.purple + '18',
  color: colors.purple, borderRadius: 6,
};

const linkBtnStyle = {
  fontSize: 9, color: colors.accent, background: 'none', border: 'none',
  cursor: 'pointer', padding: 0, textDecoration: 'underline',
};
