import { useState } from 'react';
import { Layers, Activity, BarChart3, TrendingUp, GitBranch } from 'lucide-react';
import { formatNumber } from '../utils/format';

const INDICATORS = [
  { id: 'sma', label: 'SMA (20)', icon: <TrendingUp size={12} /> },
  { id: 'ema', label: 'EMA (20)', icon: <TrendingUp size={12} /> },
  { id: 'bollinger', label: 'Bollinger Bands', icon: <GitBranch size={12} /> },
  { id: 'rsi', label: 'RSI (14)', icon: <Activity size={12} /> },
  { id: 'macd', label: 'MACD', icon: <BarChart3 size={12} /> },
  { id: 'volatility', label: 'Rolling Volatility', icon: <Activity size={12} /> },
  { id: 'drawdown', label: 'Drawdown', icon: <Activity size={12} /> },
  { id: 'abnormal_volume', label: 'Volume Anomaly', icon: <Layers size={12} /> },
];

export default function Sidebar({ profile, selectedSeries, indicators, onSeriesChange, onIndicatorChange }) {
  if (!profile) return null;
  const schema = profile.schema;

  const handleSeriesToggle = (col) => {
    const next = selectedSeries.includes(col)
      ? selectedSeries.filter(c => c !== col)
      : [...selectedSeries, col];
    onSeriesChange(next);
  };

  const handleIndicatorToggle = (id) => {
    const active = indicators.map(i => i.indicator);
    let next;
    if (active.includes(id)) {
      next = indicators.filter(i => i.indicator !== id);
    } else {
      next = [...indicators, { indicator: id, params: {} }];
    }
    onIndicatorChange(next);
  };

  const activeIndicators = indicators.map(i => i.indicator);

  return (
    <div className="sidebar">
      <div className="panel-title">Dataset Fields</div>

      <Section title="Date / Time">
        {schema.datetime_column ? (
          <FieldItem name={schema.datetime_column} type="datetime" />
        ) : (
          <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>No datetime detected</span>
        )}
      </Section>

      <Section title="Value Series">
        <div className="checkbox-group">
          {schema.value_columns.map(col => (
            <label key={col}>
              <input
                type="checkbox"
                checked={selectedSeries.includes(col)}
                onChange={() => handleSeriesToggle(col)}
              />
              <span className="mono" style={{ fontSize: 11 }}>{col}</span>
            </label>
          ))}
          {schema.columns.filter(c =>
            ['open', 'high', 'low'].includes(c.role)
          ).map(c => (
            <label key={c.column_name}>
              <input
                type="checkbox"
                checked={selectedSeries.includes(c.column_name)}
                onChange={() => handleSeriesToggle(c.column_name)}
              />
              <span className="mono" style={{ fontSize: 11 }}>{c.column_name}</span>
              <span className="tag blue" style={{ fontSize: 9, marginLeft: 4 }}>{c.role}</span>
            </label>
          ))}
        </div>
      </Section>

      {schema.volume_column && (
        <Section title="Volume">
          <FieldItem name={schema.volume_column} type="volume" />
        </Section>
      )}

      <Section title="Statistics">
        {Object.entries(profile.stats || {}).map(([col, stats]) => (
          <div key={col} style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)', marginBottom: 4 }} className="mono">
              {col}
            </div>
            {['mean', 'std', 'min', 'max', 'median'].map(k => (
              <div className="stat-row" key={k}>
                <span className="label">{k}</span>
                <span className="value">{formatNumber(stats[k], 2)}</span>
              </div>
            ))}
          </div>
        ))}
      </Section>

      <div className="panel-title" style={{ marginTop: 16 }}>Indicators</div>

      <div className="checkbox-group">
        {INDICATORS.map(ind => (
          <label key={ind.id}>
            <input
              type="checkbox"
              checked={activeIndicators.includes(ind.id)}
              onChange={() => handleIndicatorToggle(ind.id)}
            />
            <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
              {ind.icon} {ind.label}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{
        fontSize: 10, fontWeight: 600, color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6,
      }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function FieldItem({ name, type }) {
  const typeColor = { datetime: 'blue', numeric: 'green', volume: 'purple', category: 'orange' };
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0' }}>
      <span className={`tag ${typeColor[type] || 'blue'}`} style={{ fontSize: 9 }}>{type}</span>
      <span className="mono" style={{ fontSize: 11 }}>{name}</span>
    </div>
  );
}
