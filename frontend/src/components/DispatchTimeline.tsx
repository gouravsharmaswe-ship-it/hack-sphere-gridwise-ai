import React, { useState } from 'react';
import { BatteryCharging, Cpu, AlertTriangle, Filter, CheckCircle2 } from 'lucide-react';
import { DispatchEvaluation } from '../types';

interface DispatchTimelineProps {
  data: DispatchEvaluation[];
}

export const DispatchTimeline: React.FC<DispatchTimelineProps> = ({ data }) => {
  const [filterMode, setFilterMode] = useState<'all' | 'renewable' | 'grid' | 'overload'>('all');

  const filteredData = data.filter((item) => {
    if (filterMode === 'renewable') return item.dispatch_mode === 'Renewable Storage Mode';
    if (filterMode === 'grid') return item.dispatch_mode === 'Main Grid Mode';
    if (filterMode === 'overload') return item.is_critical_overload;
    return true;
  });

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2 className="card-title">Hourly Dispatch Timeline & Mode Recommendations</h2>
          <p className="card-subtitle">
            Automated power transition schedule evaluated against the deterministic microgrid logic.
          </p>
        </div>

        {/* Filter controls */}
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          <button
            className={`btn btn-sm ${filterMode === 'all' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setFilterMode('all')}
          >
            All (24h)
          </button>
          <button
            className={`btn btn-sm ${filterMode === 'renewable' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setFilterMode('renewable')}
          >
            Storage Mode
          </button>
          <button
            className={`btn btn-sm ${filterMode === 'grid' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setFilterMode('grid')}
          >
            Main Grid
          </button>
          <button
            className={`btn btn-sm ${filterMode === 'overload' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setFilterMode('overload')}
          >
            Overloads (&ge;200kW)
          </button>
        </div>
      </div>

      <div className="timeline-table-container">
        <table className="timeline-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Hour (Local)</th>
              <th>Predicted Demand</th>
              <th>Dispatch Recommendation</th>
              <th>Overload Status</th>
              <th>Rule Decision Basis</th>
            </tr>
          </thead>
          <tbody>
            {filteredData.map((item) => {
              const isOverload = item.is_critical_overload;
              const isStorage = item.dispatch_mode === 'Renewable Storage Mode';

              return (
                <tr key={item.timestamp} className={isOverload ? 'overload-row' : ''}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {item.timestamp}
                  </td>
                  <td>
                    {item.local_hour}:00
                    {item.is_peak_hour && (
                      <span className="badge badge-peak" style={{ marginLeft: '0.35rem', fontSize: '0.65rem' }}>
                        Peak 18–22
                      </span>
                    )}
                  </td>
                  <td style={{ fontWeight: 700 }}>
                    <span style={{ color: isOverload ? 'var(--overload-red)' : isStorage ? 'var(--renewable-emerald)' : 'var(--text-primary)' }}>
                      {item.predicted_demand_kw.toFixed(2)} kW
                    </span>
                  </td>
                  <td>
                    {isStorage ? (
                      <span className="badge badge-renewable">
                        <BatteryCharging size={12} />
                        Renewable Storage Mode
                      </span>
                    ) : (
                      <span className="badge badge-grid">
                        <Cpu size={12} />
                        Main Grid Mode
                      </span>
                    )}
                  </td>
                  <td>
                    {isOverload ? (
                      <span className="badge badge-overload">
                        <AlertTriangle size={12} />
                        CRITICAL OVERLOAD
                      </span>
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Nominal</span>
                    )}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {item.reason}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
