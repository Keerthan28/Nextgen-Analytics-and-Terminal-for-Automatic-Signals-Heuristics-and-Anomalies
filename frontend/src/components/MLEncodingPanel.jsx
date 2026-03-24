import { useState } from 'react';
import { colors } from '../styles/theme';

export default function MLEncodingPanel({
  encodingProfile,
  encodingSpec,
  encodingReasons,
  encodingLoading,
  fetchEncodingAI,
  setEncodingForColumn,
  targetColumn,
  reloadProfile,
  encodeData,
  encodingResult,
  encodingRunning,
}) {
  const cols = encodingProfile?.columns || [];
  const [showPreview, setShowPreview] = useState(false);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 12, fontSize: 10 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: colors.textBright, borderBottom: `1px solid ${colors.border}`, paddingBottom: 6 }}>
        Feature Encoding
      </div>

      <p style={{ fontSize: 9, color: colors.textMuted, lineHeight: 1.45, margin: 0 }}>
        Configure how each column is encoded to numbers. Click <b>Encode Data</b> to apply.
        Used for <b>ML training</b> and <b>PCA / K-Means clustering</b>.
      </p>

      {targetColumn && (
        <div style={{ fontSize: 8, color: colors.accent }}>
          Target <span className="mono">{targetColumn}</span> is excluded from features.
        </div>
      )}

      {cols.length === 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-start' }}>
          <div style={{ fontSize: 9, color: colors.orange }}>
            No column data loaded yet. Make sure a dataset is uploaded.
          </div>
          {reloadProfile && (
            <button type="button" onClick={reloadProfile} style={smallBtnStyle(colors.accent)}>
              Reload columns
            </button>
          )}
        </div>
      )}

      {cols.length > 0 && (
        <>
          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              type="button"
              onClick={fetchEncodingAI}
              disabled={!!encodingLoading}
              style={{ ...actionBtnStyle(colors.orange), flex: 1 }}
            >
              {encodingLoading ? 'Gemini suggesting…' : 'AI: suggest encodings'}
            </button>
          </div>

          {/* Column list */}
          <div style={{ maxHeight: 'calc(100vh - 340px)', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {cols.map((row) => (
              <div key={row.name} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 30px 100px', gap: 6, alignItems: 'center' }}>
                  <span style={{ fontSize: 9, color: colors.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={row.name}>
                    {row.name}
                  </span>
                  <span style={{ fontSize: 8, color: row.role === 'numeric' ? colors.green : colors.orange, fontFamily: 'JetBrains Mono, monospace' }}>
                    {row.role === 'numeric' ? 'num' : 'cat'}
                  </span>
                  <select
                    className="select"
                    style={{ fontSize: 8, padding: '3px 4px' }}
                    value={encodingSpec?.[row.name] ?? row.default_encoding}
                    onChange={(e) => setEncodingForColumn(row.name, e.target.value)}
                  >
                    {row.allowed_encodings.map((enc) => (
                      <option key={enc} value={enc}>{enc.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                {encodingReasons?.[row.name] && (
                  <div style={{ fontSize: 7, color: colors.textMuted, paddingLeft: 2 }}>{encodingReasons[row.name]}</div>
                )}
              </div>
            ))}
          </div>

          {/* Encode button */}
          <button
            type="button"
            onClick={encodeData}
            disabled={!!encodingRunning}
            style={{
              padding: '9px 14px', fontSize: 11, fontWeight: 700, cursor: 'pointer',
              border: `1px solid ${colors.green}`,
              background: colors.green + '20',
              color: colors.green,
              borderRadius: 6,
              letterSpacing: 0.3,
            }}
          >
            {encodingRunning ? 'Encoding…' : 'Encode Data'}
          </button>

          {/* Encoding result */}
          {encodingResult && (
            <div style={{
              display: 'flex', flexDirection: 'column', gap: 8,
              background: colors.bgTertiary, borderRadius: 6, padding: 10,
              borderLeft: `3px solid ${colors.green}`,
            }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: colors.green }}>
                Encoding Complete
              </div>

              <div style={{ display: 'flex', gap: 12, fontSize: 9, color: colors.text }}>
                <span><b>{encodingResult.rows}</b> rows</span>
                <span><b>{encodingResult.columns}</b> features</span>
              </div>

              {/* Summary */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <div style={{ fontSize: 8, fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Column Summary
                </div>
                {encodingResult.summary.map((s) => (
                  <div key={s.column} style={{ fontSize: 8, color: colors.text, display: 'flex', gap: 6, alignItems: 'center' }}>
                    <span style={{
                      color: s.role === 'numeric' ? colors.green : colors.orange,
                      fontFamily: 'JetBrains Mono, monospace', minWidth: 20,
                    }}>
                      {s.role === 'numeric' ? 'N' : 'C'}
                    </span>
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={s.column}>
                      {s.column}
                    </span>
                    <span style={{ color: s.encoding === 'drop' ? colors.red : colors.cyan, fontFamily: 'JetBrains Mono, monospace' }}>
                      {s.encoding}
                    </span>
                    <span style={{ color: colors.textMuted, minWidth: 16, textAlign: 'right' }}>
                      →{s.output_columns}
                    </span>
                  </div>
                ))}
              </div>

              {/* Preview toggle */}
              <button
                type="button"
                onClick={() => setShowPreview((p) => !p)}
                style={{ fontSize: 8, color: colors.accent, background: 'none', border: 'none', cursor: 'pointer', padding: 0, textAlign: 'left', textDecoration: 'underline' }}
              >
                {showPreview ? 'Hide preview' : `Show preview (first ${encodingResult.preview?.length || 0} rows)`}
              </button>

              {showPreview && encodingResult.preview?.length > 0 && (
                <div style={{ overflow: 'auto', maxHeight: 200 }}>
                  <table style={{ borderCollapse: 'collapse', fontSize: 7, fontFamily: 'JetBrains Mono, monospace', whiteSpace: 'nowrap' }}>
                    <thead>
                      <tr>
                        {encodingResult.feature_names.map((n) => (
                          <th key={n} style={{ padding: '3px 6px', borderBottom: `1px solid ${colors.border}`, color: colors.textMuted, fontWeight: 600, textAlign: 'left' }}>
                            {n}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {encodingResult.preview.map((row, i) => (
                        <tr key={i}>
                          {encodingResult.feature_names.map((n) => (
                            <td key={n} style={{ padding: '2px 6px', borderBottom: `1px solid ${colors.border}22`, color: colors.text }}>
                              {row[n] != null ? (typeof row[n] === 'number' ? Number(row[n]).toFixed(3) : String(row[n])) : '—'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function actionBtnStyle(color) {
  return {
    padding: '7px 10px', fontSize: 10, fontWeight: 600, cursor: 'pointer',
    border: `1px solid ${color}`, background: color + '15',
    color, borderRadius: 6,
  };
}

function smallBtnStyle(color) {
  return {
    padding: '6px 12px', fontSize: 9, fontWeight: 600, cursor: 'pointer',
    border: `1px solid ${color}`, background: color + '15',
    color, borderRadius: 5,
  };
}
