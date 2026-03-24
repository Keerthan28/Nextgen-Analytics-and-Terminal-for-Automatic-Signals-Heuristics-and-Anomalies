import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Database, BarChart3, Zap } from 'lucide-react';

export default function UploadZone({ onFile, loading }) {
  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) onFile(accepted[0]);
  }, [onFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    multiple: false,
    disabled: loading,
  });

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      padding: 40,
    }}>
      <div {...getRootProps()} className={`upload-zone ${isDragActive ? 'active' : ''}`}>
        <input {...getInputProps()} />
        {loading ? (
          <div className="loading">
            <div className="spinner" />
            <span>Processing dataset...</span>
          </div>
        ) : (
          <>
            <Upload size={40} color="var(--accent)" style={{ marginBottom: 16 }} />
            <h2>Drop your dataset here</h2>
            <p>Supports CSV, XLSX, and XLS files</p>
            <p style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
              or click to browse
            </p>
          </>
        )}
      </div>

      <div style={{
        display: 'flex', gap: 40, marginTop: 48,
        color: 'var(--text-muted)', fontSize: 12,
      }}>
        <Feature icon={<Database size={18} />} label="Auto schema detection" />
        <Feature icon={<BarChart3 size={18} />} label="Terminal-style charts" />
        <Feature icon={<Zap size={18} />} label="Instant insights" />
      </div>
    </div>
  );
}

function Feature({ icon, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      {icon}
      <span>{label}</span>
    </div>
  );
}
