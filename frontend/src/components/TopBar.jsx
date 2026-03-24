import { Upload, Download, FileText, Image, Code } from 'lucide-react';
import * as api from '../utils/api';

export default function TopBar({ profile, onUploadClick, onExport }) {
  return (
    <div className="top-bar">
      <div className="brand">VEDA — Visual Engine for Data Analytics</div>
      <div className="separator" />

      {profile && (
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }} className="mono">
          {profile.schema.row_count.toLocaleString()} rows · {profile.schema.columns.length} cols
        </span>
      )}

      {profile?.date_range && (
        <>
          <div className="separator" />
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }} className="mono">
            {new Date(profile.date_range.start).toLocaleDateString()} – {new Date(profile.date_range.end).toLocaleDateString()}
          </span>
        </>
      )}

      <div style={{ flex: 1 }} />

      {profile && (
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn" onClick={() => onExport('png')} title="Export PNG">
            <Image size={13} /> PNG
          </button>
          <button className="btn" onClick={() => onExport('csv')} title="Export CSV">
            <FileText size={13} /> CSV
          </button>
          <button className="btn" onClick={() => onExport('html')} title="Export Report">
            <Code size={13} /> Report
          </button>
        </div>
      )}

      <button className="btn primary" onClick={onUploadClick}>
        <Upload size={13} /> Upload
      </button>
    </div>
  );
}
