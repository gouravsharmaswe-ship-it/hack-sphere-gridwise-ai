import React from 'react';
import { Zap, UploadCloud, History, Play, ShieldAlert, Cpu } from 'lucide-react';
import { ModelStatus } from '../types';

interface NavbarProps {
  modelStatus: ModelStatus | null;
  onOpenUpload: () => void;
  onOpenHistory: () => void;
  onRunForecast: () => void;
  isForecasting: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  modelStatus,
  onOpenUpload,
  onOpenHistory,
  onRunForecast,
  isForecasting,
}) => {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <a href="#" className="brand">
          <div className="brand-icon">
            <Zap size={22} />
          </div>
          <div className="brand-text">
            <h1>
              Gridwise AI
              <span className="badge badge-renewable" style={{ fontSize: '0.65rem', padding: '0.15rem 0.45rem' }}>
                HackSphere 3.0
              </span>
            </h1>
            <p>Smart Energy Microgrid & Demand Forecasting Engine</p>
          </div>
        </a>

        <div className="nav-actions">
          {/* Real Model Integration Status */}
          <div
            className="card"
            style={{
              padding: '0.35rem 0.75rem',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              boxShadow: 'none',
              background: '#f8fafc',
            }}
            title={modelStatus?.message || 'Model Status'}
          >
            <Cpu size={14} color={modelStatus?.status === 'active' ? '#059669' : '#d97706'} />
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              {modelStatus?.provider || 'Initializing Model...'}
            </span>
            {modelStatus?.endpoint_configured ? (
              <span className="badge badge-renewable" style={{ padding: '0.1rem 0.4rem', fontSize: '0.65rem' }}>
                QuickML Connected
              </span>
            ) : (
              <span className="badge badge-demo" style={{ padding: '0.1rem 0.4rem', fontSize: '0.65rem' }}>
                Local ML Active
              </span>
            )}
          </div>

          <button className="btn btn-outline btn-sm" onClick={onOpenUpload}>
            <UploadCloud size={15} />
            <span>Upload CSV</span>
          </button>

          <button className="btn btn-outline btn-sm" onClick={onOpenHistory}>
            <History size={15} />
            <span>History</span>
          </button>

          <button
            className="btn btn-primary btn-sm"
            onClick={onRunForecast}
            disabled={isForecasting}
          >
            <Play size={15} />
            <span>{isForecasting ? 'Forecasting...' : 'Run 24h Forecast'}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
