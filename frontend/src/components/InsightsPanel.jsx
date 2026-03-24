import { Zap, AlertTriangle, Info, AlertCircle, Sparkles, ChevronRight } from 'lucide-react';
import { formatPercent, formatNumber } from '../utils/format';

const severityIcon = {
  critical: <AlertCircle size={13} color="var(--red)" />,
  warning: <AlertTriangle size={13} color="var(--orange)" />,
  info: <Info size={13} color="var(--accent)" />,
};

export default function InsightsPanel({ insights, llmInsights, llmChartInsights, llmLoading }) {
  return (
    <div className="insights-panel">
      {/* AI Narrative (top priority) */}
      {llmInsights?.narrative && (
        <AISection title="AI Analysis" loading={false}>
          <div style={{
            fontSize: 12, color: 'var(--text)', lineHeight: 1.6,
            padding: '10px 12px', background: 'var(--bg)', borderRadius: 6,
            borderLeft: '3px solid var(--purple)',
          }}>
            {llmInsights.narrative}
          </div>

          {llmInsights.findings?.map((f, i) => (
            <div key={i} className={`insight-card ${f.severity || 'info'}`} style={{ marginTop: 6 }}>
              <div className="title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Sparkles size={11} color="var(--purple)" />
                {f.title}
              </div>
              <div className="desc">{f.description}</div>
              {f.recommendation && (
                <div style={{
                  marginTop: 4, fontSize: 10, color: 'var(--cyan)',
                  display: 'flex', alignItems: 'flex-start', gap: 4,
                }}>
                  <ChevronRight size={10} style={{ marginTop: 1, flexShrink: 0 }} />
                  {f.recommendation}
                </div>
              )}
            </div>
          ))}
        </AISection>
      )}

      {/* AI Chart-specific insights */}
      {llmChartInsights?.chart_narrative && (
        <AISection title="Chart Analysis" loading={false}>
          <div style={{
            fontSize: 11, color: 'var(--text)', lineHeight: 1.5,
            padding: '8px 10px', background: 'var(--bg)', borderRadius: 6,
            borderLeft: '3px solid var(--cyan)',
            marginBottom: 6,
          }}>
            {llmChartInsights.chart_narrative}
          </div>

          {llmChartInsights.observations?.map((o, i) => (
            <div key={i} className={`insight-card ${o.severity || 'info'}`} style={{ marginTop: 4 }}>
              <div className="title" style={{ fontSize: 11 }}>
                {severityIcon[o.severity] || severityIcon.info} {o.title}
              </div>
              <div className="desc">{o.detail}</div>
            </div>
          ))}
        </AISection>
      )}

      {llmLoading && !llmInsights?.narrative && (
        <AISection title="AI Analysis" loading={true}>
          <div className="loading" style={{ padding: 16, fontSize: 11 }}>
            <div className="spinner" />
            <span>Gemini is analyzing your data...</span>
          </div>
        </AISection>
      )}

      {/* Statistical insights */}
      {insights && (
        <>
          <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: llmInsights ? 8 : 0 }}>
            <Zap size={12} /> Statistical Insights
          </div>

          {insights.summary && (
            <div style={{
              fontSize: 11, color: 'var(--text-muted)', marginBottom: 10,
              padding: '8px 10px', background: 'var(--bg)', borderRadius: 6,
              lineHeight: 1.5,
            }}>
              {insights.summary}
            </div>
          )}

          {insights.top_findings?.length === 0 && !llmInsights?.narrative && (
            <div className="empty-state" style={{ padding: 20 }}>
              <Info size={24} />
              <span style={{ fontSize: 12 }}>No significant findings</span>
            </div>
          )}

          {insights.top_findings?.map((item, i) => (
            <div key={i} className={`insight-card ${item.severity}`}>
              <div className="title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {severityIcon[item.severity] || severityIcon.info}
                {item.title}
              </div>
              <div className="desc">{item.description}</div>
              {item.value != null && (
                <div style={{
                  marginTop: 4, fontSize: 11,
                  fontFamily: "'JetBrains Mono', monospace",
                  color: item.value > 0 ? 'var(--green)' : item.value < 0 ? 'var(--red)' : 'var(--text-muted)',
                }}>
                  {item.metric === 'return' || item.metric === 'max_drawdown'
                    ? formatPercent(item.value)
                    : formatNumber(item.value)}
                </div>
              )}
              <div className="rule">{item.rule}</div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}


function AISection({ title, loading, children }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="panel-title" style={{
        display: 'flex', alignItems: 'center', gap: 6,
        background: 'rgba(188,140,255,0.06)',
        margin: '-12px -12px 8px -12px',
        padding: '8px 12px',
        borderBottom: '1px solid rgba(188,140,255,0.15)',
      }}>
        <Sparkles size={12} color="var(--purple)" />
        <span style={{ color: 'var(--purple)' }}>{title}</span>
        <span style={{
          marginLeft: 'auto',
          fontSize: 8,
          color: 'var(--purple)',
          opacity: 0.6,
          textTransform: 'uppercase',
          letterSpacing: 1,
        }}>
          Gemini
        </span>
      </div>
      {children}
    </div>
  );
}
