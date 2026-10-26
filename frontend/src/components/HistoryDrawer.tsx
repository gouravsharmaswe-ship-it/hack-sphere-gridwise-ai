import React from 'react';
import { X, History, Download, ExternalLink, Calendar, BatteryCharging, AlertTriangle } from 'lucide-react';
import { HistoryItem } from '../types';
import { getExportCsvUrl } from '../services/api';

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  historyList: HistoryItem[];
  onSelectRun: (id: string) => void;
}

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  isOpen,
  onClose,
  historyList,
  onSelectRun,
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '750px' }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <History size={20} color="var(--primary)" />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Forecast Execution History</h2>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
          >
            <X size={20} />
          </button>
        </div>

        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
          Inspect previous 24-hour forecasting runs, model provenance, and download benchmark prediction CSVs.
        </p>

        {historyList.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
            No forecast history stored yet. Run your first 24h forecast to populate history.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '60vh', overflowY: 'auto' }}>
            {historyList.map((item) => (
              <div
                key={item.id}
                style={{
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '1rem',
                  background: 'var(--bg-surface)',
                  transition: 'background 0.15s ease',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.88rem' }}>
                      Horizon: {item.forecast_start.split(' ')[0]}
                    </span>
                    {item.is_demo ? (
                      <span className="badge badge-demo" style={{ fontSize: '0.65rem' }}>
                        Simulated
                      </span>
                    ) : (
                      <span className="badge badge-renewable" style={{ fontSize: '0.65rem' }}>
                        Telemetry
                      </span>
                    )}
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Model: {item.model_used}
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: '1rem', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    <span>Avg: <strong>{item.avg_demand_kw.toFixed(1)} kW</strong></span>
                    <span>Peak: <strong>{item.peak_demand_kw.toFixed(1)} kW</strong></span>
                    {item.overload_count > 0 ? (
                      <span style={{ color: 'var(--overload-red)', fontWeight: 600 }}>
                        {item.overload_count} Overload Violation{item.overload_count > 1 ? 's' : ''}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--renewable-text)' }}>Safe Horizon</span>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={() => {
                      onSelectRun(item.id);
                      onClose();
                    }}
                  >
                    <ExternalLink size={13} />
                    Load View
                  </button>
                  <a
                    href={getExportCsvUrl(item.id)}
                    className="btn btn-primary btn-sm"
                    download
                    title="Download predictions.csv"
                  >
                    <Download size={13} />
                    CSV
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
