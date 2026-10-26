import React, { useState } from 'react';
import { X, UploadCloud, CheckCircle, AlertCircle, FileText } from 'lucide-react';
import { uploadTelemetryCsv } from '../services/api';

interface TelemetryUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyUploadedData: () => void;
}

export const TelemetryUploadModal: React.FC<TelemetryUploadModalProps> = ({
  isOpen,
  onClose,
  onApplyUploadedData,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setSelectedFile(file);
    setErrorMessage(null);
    setValidationResult(null);

    // Validate on backend
    setIsUploading(true);
    try {
      const res = await uploadTelemetryCsv(file);
      setValidationResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'CSV validation failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <FileText size={20} color="var(--primary)" />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Telemetry Ingestion & Validation</h2>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
          >
            <X size={20} />
          </button>
        </div>

        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Upload a microgrid telemetry CSV file containing weather features. Expected columns:
          <code style={{ background: '#f1f5f9', padding: '0.1rem 0.35rem', borderRadius: 4, marginLeft: 4 }}>
            timestamp, ambient_temp_c, humidity_pct, solar_irradiance_wm2
          </code>
        </p>

        {/* Dropzone */}
        <label className="dropzone" style={{ display: 'block' }}>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <UploadCloud size={36} color="var(--primary)" style={{ margin: '0 auto 0.5rem' }} />
          <p style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
            {selectedFile ? selectedFile.name : 'Click to select CSV file'}
          </p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Supports standard CSV telemetry up to 10MB
          </p>
        </label>

        {isUploading && (
          <p style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Parsing and validating CSV schema...
          </p>
        )}

        {errorMessage && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--overload-bg)',
              color: 'var(--overload-text)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.82rem',
            }}
          >
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        {validationResult && (
          <div style={{ marginTop: '1.25rem' }}>
            <div
              style={{
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                background: 'var(--renewable-bg)',
                color: 'var(--renewable-text)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.85rem',
                fontWeight: 600,
                marginBottom: '1rem',
              }}
            >
              <CheckCircle size={18} />
              <span>
                Schema Valid! {validationResult.total_rows} rows found.
                {validationResult.can_run_24h_forecast ? ' (Ready for 24h forecasting)' : ' (Needs >= 24 rows)'}
              </span>
            </div>

            {/* Preview table */}
            {validationResult.preview && validationResult.preview.length > 0 && (
              <div>
                <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  Preview (First {validationResult.preview.length} rows):
                </p>
                <div style={{ maxHeight: 180, overflowY: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 6 }}>
                  <table className="timeline-table" style={{ fontSize: '0.75rem' }}>
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>Temp (°C)</th>
                        <th>Humidity (%)</th>
                        <th>Solar (W/m²)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {validationResult.preview.map((row: any, idx: number) => (
                        <tr key={idx}>
                          <td>{row.timestamp}</td>
                          <td>{row.ambient_temp_c}</td>
                          <td>{row.humidity_pct}</td>
                          <td>{row.solar_irradiance_wm2}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button className="btn btn-outline" onClick={onClose}>
                Close
              </button>
              <button
                className="btn btn-primary"
                onClick={() => {
                  onApplyUploadedData();
                  onClose();
                }}
              >
                Use For 24h Horizon
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
