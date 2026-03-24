import { Hash, Type, Target, Lightbulb, AlertTriangle, Sparkles } from 'lucide-react';
import { formatNumber } from '../utils/format';

export default function TabularSidebar({ profile, llmSuggestions, llmLoading, onSuggestionClick }) {
  if (!profile) return null;
  const schema = profile.schema;
  const tp = profile.tabular_profile || {};

  const hasLLMSuggestions = llmSuggestions && llmSuggestions.length > 0;
  const staticSuggestions = tp.suggested_charts || [];

  return (
    <div className="sidebar">
      <div className="panel-title">Dataset Overview</div>

      <div className="card" style={{ marginBottom: 12 }}>
        <div className="stat-row">
          <span className="label">Rows</span>
          <span className="value">{schema.row_count.toLocaleString()}</span>
        </div>
        <div className="stat-row">
          <span className="label">Columns</span>
          <span className="value">{schema.columns.length}</span>
        </div>
        <div className="stat-row">
          <span className="label">Numeric</span>
          <span className="value">{schema.value_columns.length}</span>
        </div>
        <div className="stat-row">
          <span className="label">Categorical</span>
          <span className="value">{schema.category_columns.length}</span>
        </div>
        {schema.target_column && (
          <div className="stat-row">
            <span className="label" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Target size={10} /> Target
            </span>
            <span className="value" style={{ color: 'var(--accent)' }}>{schema.target_column}</span>
          </div>
        )}
      </div>

      {tp.target_breakdown && (
        <>
          <div className="panel-title" style={{ marginTop: 12 }}>Target Distribution</div>
          <div className="card">
            {Object.entries(tp.target_breakdown.distribution).map(([k, v]) => {
              const rate = tp.target_breakdown.rates[k];
              return (
                <div key={k} style={{ marginBottom: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
                    <span className="mono" style={{ fontWeight: 500 }}>{k}</span>
                    <span className="mono" style={{ color: 'var(--text-muted)' }}>
                      {v.toLocaleString()} ({rate}%)
                    </span>
                  </div>
                  <div style={{ height: 4, background: 'var(--border)', borderRadius: 2 }}>
                    <div style={{
                      height: '100%', width: `${rate}%`, borderRadius: 2,
                      background: rate > 50 ? 'var(--accent)' : 'var(--orange)',
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* LLM-powered suggestions (shown first when available) */}
      {hasLLMSuggestions && (
        <>
          <div className="panel-title" style={{
            marginTop: 12, display: 'flex', alignItems: 'center', gap: 4,
            color: 'var(--purple)',
          }}>
            <Sparkles size={10} /> AI-Suggested Charts
          </div>
          {llmSuggestions.map((s, i) => (
            <button
              key={`llm-${i}`}
              className="card"
              onClick={() => onSuggestionClick(s)}
              style={{
                width: '100%', textAlign: 'left', cursor: 'pointer',
                padding: '8px 10px', transition: 'border-color 0.15s',
                borderLeft: '2px solid var(--purple)',
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-bright)', marginBottom: 2 }}>
                {s.title}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                {s.description}
              </div>
              <span className="tag purple" style={{ fontSize: 9, marginTop: 4 }}>{s.chart_type}</span>
            </button>
          ))}
        </>
      )}

      {llmLoading && !hasLLMSuggestions && (
        <div style={{ marginTop: 12 }}>
          <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--purple)' }}>
            <Sparkles size={10} /> AI-Suggested Charts
          </div>
          <div className="loading" style={{ padding: 12, fontSize: 11 }}>
            <div className="spinner" />
            <span>Gemini analyzing...</span>
          </div>
        </div>
      )}

      {/* Static suggestions (fallback / supplementary) */}
      {staticSuggestions.length > 0 && (
        <>
          <div className="panel-title" style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
            <Lightbulb size={10} /> {hasLLMSuggestions ? 'More Charts' : 'Suggested Charts'}
          </div>
          {staticSuggestions.slice(0, hasLLMSuggestions ? 6 : 12).map((s, i) => (
            <button
              key={`static-${i}`}
              className="card"
              onClick={() => onSuggestionClick(s)}
              style={{
                width: '100%', textAlign: 'left', cursor: 'pointer',
                padding: '8px 10px', transition: 'border-color 0.15s',
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-bright)', marginBottom: 2 }}>
                {s.title}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                {s.description}
              </div>
              <span className="tag blue" style={{ fontSize: 9, marginTop: 4 }}>{s.chart_type}</span>
            </button>
          ))}
        </>
      )}

      {tp.correlations?.length > 0 && (
        <>
          <div className="panel-title" style={{ marginTop: 12 }}>Top Correlations</div>
          {tp.correlations.slice(0, 8).map((c, i) => (
            <div key={i} className="stat-row">
              <span className="label" style={{ fontSize: 10 }}>{c.col_a} / {c.col_b}</span>
              <span className="value" style={{
                color: Math.abs(c.r) > 0.7 ? 'var(--orange)' : 'var(--text-muted)',
                fontSize: 11,
              }}>
                {c.r > 0 ? '+' : ''}{c.r.toFixed(3)}
              </span>
            </div>
          ))}
        </>
      )}

      {Object.keys(tp.category_summary || {}).length > 0 && (
        <>
          <div className="panel-title" style={{ marginTop: 12 }}>Category Summary</div>
          {Object.entries(tp.category_summary).slice(0, 6).map(([col, info]) => (
            <div key={col} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)', marginBottom: 3 }} className="mono">{col}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>
                {info.nunique} unique · {info.missing} missing
              </div>
              {Object.entries(info.top_values).slice(0, 4).map(([val, cnt]) => (
                <div key={val} className="stat-row" style={{ fontSize: 10 }}>
                  <span className="label">{val}</span>
                  <span className="value">{cnt.toLocaleString()}</span>
                </div>
              ))}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
