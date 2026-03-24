import { BarChart3, PieChart, ScatterChart, Table2, Grid3X3, LayoutGrid } from 'lucide-react';

const CHART_TYPES = [
  { id: 'histogram', label: 'Histogram', icon: <BarChart3 size={13} /> },
  { id: 'bar', label: 'Bar', icon: <LayoutGrid size={13} /> },
  { id: 'scatter', label: 'Scatter', icon: <ScatterChart size={13} /> },
  { id: 'box', label: 'Box Plot', icon: <Table2 size={13} /> },
  { id: 'heatmap', label: 'Heatmap', icon: <Grid3X3 size={13} /> },
  { id: 'pie', label: 'Pie', icon: <PieChart size={13} /> },
];

const AGG_OPTIONS = ['count', 'mean', 'sum', 'median', 'min', 'max'];

export default function TabularToolbar({
  chartType, xCol, yCol, colorCol, agg,
  numericCols, categoryCols, allCols,
  onChartTypeChange, onXColChange, onYColChange, onColorColChange, onAggChange,
  inline = false,
}) {
  const showY = ['bar', 'scatter', 'box'].includes(chartType);
  const showColor = ['histogram', 'bar', 'scatter'].includes(chartType);
  const showAgg = chartType === 'bar' && yCol;

  const content = (
    <>
      <div className="btn-group">
        {CHART_TYPES.map(ct => (
          <button
            key={ct.id}
            className={`btn ${chartType === ct.id ? 'active' : ''}`}
            onClick={() => onChartTypeChange(ct.id)}
          >
            {ct.icon} {ct.label}
          </button>
        ))}
      </div>

      <div className="separator" style={{ width: 1, height: 20, background: 'var(--border)' }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <label style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>X</label>
        <select className="select" value={xCol || ''} onChange={e => onXColChange(e.target.value || null)}>
          <option value="">—</option>
          {allCols.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {showY && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <label style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Y</label>
          <select className="select" value={yCol || ''} onChange={e => onYColChange(e.target.value || null)}>
            <option value="">—</option>
            {numericCols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      )}

      {showColor && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <label style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Color</label>
          <select className="select" value={colorCol || ''} onChange={e => onColorColChange(e.target.value || null)}>
            <option value="">None</option>
            {categoryCols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      )}

      {showAgg && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <label style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Agg</label>
          <select className="select" value={agg} onChange={e => onAggChange(e.target.value)}>
            {AGG_OPTIONS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
      )}
    </>
  );

  if (inline) return <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>{content}</div>;
  return <div className="toolbar" style={{ flexWrap: 'wrap', gap: 6 }}>{content}</div>;
}
