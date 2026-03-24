import { useState } from 'react';
import { ChevronDown, ChevronUp, Table } from 'lucide-react';

export default function DataPreview({ profile }) {
  const [expanded, setExpanded] = useState(false);

  if (!profile?.preview?.length) return null;

  const preview = profile.preview;
  const cols = Object.keys(preview[0] || {});

  return (
    <div style={{
      borderTop: '1px solid var(--border)',
      background: 'var(--bg-secondary)',
      flexShrink: 0,
    }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 16px', fontSize: 11, color: 'var(--text-muted)',
          background: 'transparent', fontWeight: 500,
        }}
      >
        <Table size={12} />
        Data Preview ({profile.schema.row_count.toLocaleString()} rows)
        <span style={{ flex: 1 }} />
        {expanded ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </button>

      {expanded && (
        <div style={{ maxHeight: 200, overflow: 'auto', padding: '0 8px 8px' }}>
          <table className="data-table">
            <thead>
              <tr>{cols.map(c => <th key={c}>{c}</th>)}</tr>
            </thead>
            <tbody>
              {preview.map((row, i) => (
                <tr key={i}>
                  {cols.map(c => (
                    <td key={c}>{row[c] != null ? String(row[c]) : ''}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
