import React from 'react';
import { AlertOctagon, Info, ShieldAlert } from 'lucide-react';
import { DispatchEvaluation } from '../types';

interface AlertBannerProps {
  data: DispatchEvaluation[];
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ data }) => {
  const overloadItems = data.filter((item) => item.is_critical_overload);

  if (overloadItems.length === 0) {
    return null;
  }

  const peakOverloadKw = Math.max(...overloadItems.map((o) => o.predicted_demand_kw));
  const peakTimestamp = overloadItems.find((o) => o.predicted_demand_kw === peakOverloadKw)?.timestamp;

  return (
    <div className="alert-banner">
      <AlertOctagon size={24} style={{ flexShrink: 0, marginTop: '2px' }} />
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <h3 className="alert-title">
            CRITICAL OVERLOAD ALERT — {overloadItems.length} Hour{overloadItems.length > 1 ? 's' : ''} Exceed 200 kW
          </h3>
          <span className="badge badge-overload" style={{ background: '#ffffff', color: 'var(--overload-red)' }}>
            Peak Overload: {peakOverloadKw.toFixed(1)} kW at {peakTimestamp?.split(' ')[1] || peakTimestamp}
          </span>
        </div>
        <p className="alert-desc">
          Grid demand is predicted to exceed the 200.0 kW critical safety threshold. The dispatch engine has flagged these
          intervals for immediate peak-shaving, battery reserve injection, or non-essential load curtailment.
        </p>
        <div style={{ marginTop: '0.65rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.75rem' }}>
          {overloadItems.slice(0, 6).map((item) => (
            <span
              key={item.timestamp}
              style={{
                background: 'rgba(255,255,255,0.7)',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                fontWeight: 600,
                border: '1px solid rgba(220, 38, 38, 0.3)',
              }}
            >
              {item.timestamp.split(' ')[1] || item.timestamp}: {item.predicted_demand_kw.toFixed(1)} kW
            </span>
          ))}
          {overloadItems.length > 6 && (
            <span style={{ padding: '0.2rem 0.5rem', opacity: 0.8 }}>
              +{overloadItems.length - 6} more hours
            </span>
          )}
        </div>
        <p style={{ marginTop: '0.5rem', fontSize: '0.72rem', opacity: 0.85, fontStyle: 'italic' }}>
          * Decision-support rules only: Recommendations assist human operators and do not directly actuate electrical hardware.
        </p>
      </div>
    </div>
  );
};
