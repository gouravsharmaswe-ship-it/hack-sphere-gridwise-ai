import React from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { DispatchEvaluation } from '../types';

interface ForecastChartProps {
  data: DispatchEvaluation[];
  isDemoMode?: boolean;
}

export const ForecastChart: React.FC<ForecastChartProps> = ({ data, isDemoMode }) => {
  if (!data || data.length === 0) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-muted)' }}>No forecast data available. Click "Run 24h Forecast" to begin.</p>
      </div>
    );
  }

  // Format data for chart
  const chartData = data.map((item) => {
    // Format timestamp label: HH:00
    const timeStr = item.timestamp.split(' ')[1] || item.timestamp;
    const hourLabel = timeStr.substring(0, 5);

    return {
      hourLabel,
      fullTimestamp: item.timestamp,
      predicted_demand_kw: item.predicted_demand_kw,
      dispatch_mode: item.dispatch_mode,
      is_critical_overload: item.is_critical_overload,
      is_peak_hour: item.is_peak_hour,
      local_hour: item.local_hour,
    };
  });

  const maxVal = Math.max(...data.map((d) => d.predicted_demand_kw), 220);
  const minVal = Math.min(...data.map((d) => d.predicted_demand_kw), 70);

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title-group">
            <h2 className="card-title">24-Hour Energy Demand Forecast & Thresholds</h2>
            {isDemoMode && (
              <span className="badge badge-demo" title="Data generated from user scenario or simulation fixture">
                Simulation Scenario
              </span>
            )}
          </div>
          <p className="card-subtitle">
            Dynamic load curve with automated 160 kW Renewable Storage threshold and 200 kW Critical Overload Alert line.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 12, height: 12, background: 'var(--renewable-emerald)', borderRadius: 2 }} />
            <span>&gt;160 kW Storage Mode</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 12, height: 12, background: 'var(--overload-red)', borderRadius: 2 }} />
            <span>&ge;200 kW Overload Alert</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 12, height: 12, background: '#fef3c7', border: '1px solid #fde68a', borderRadius: 2 }} />
            <span>18–22 Peak Evening Window</span>
          </div>
        </div>
      </div>

      <div style={{ width: '100%', height: 360 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 15, right: 25, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="demandGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0284c7" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#0284c7" stopOpacity={0.02} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />

            <XAxis
              dataKey="hourLabel"
              tick={{ fill: '#64748b', fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
            />
            <YAxis
              domain={[Math.floor(minVal - 10), Math.ceil(maxVal + 15)]}
              tick={{ fill: '#64748b', fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              unit=" kW"
            />

            {/* Reference Line for 160 kW (Renewable Storage Mode threshold) */}
            <ReferenceLine
              y={160.0}
              stroke="#059669"
              strokeDasharray="4 4"
              strokeWidth={2}
              label={{
                value: '160 kW (Storage Mode Threshold)',
                fill: '#059669',
                fontSize: 11,
                position: 'right',
                fontWeight: 600,
              }}
            />

            {/* Reference Line for 200 kW (Critical Overload Alert threshold) */}
            <ReferenceLine
              y={200.0}
              stroke="#dc2626"
              strokeDasharray="4 4"
              strokeWidth={2}
              label={{
                value: '200 kW (Critical Overload Alert)',
                fill: '#dc2626',
                fontSize: 11,
                position: 'right',
                fontWeight: 600,
              }}
            />

            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null;
                const d = payload[0].payload;
                return (
                  <div
                    style={{
                      background: 'rgba(255, 255, 255, 0.96)',
                      padding: '0.75rem 1rem',
                      borderRadius: '8px',
                      boxShadow: '0 4px 14px rgba(0,0,0,0.12)',
                      border: '1px solid #e2e8f0',
                      fontSize: '0.8rem',
                    }}
                  >
                    <p style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                      {d.fullTimestamp}
                    </p>
                    <p style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0284c7' }}>
                      {d.predicted_demand_kw.toFixed(2)} kW
                    </p>
                    <div style={{ marginTop: '0.35rem', display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                      <span
                        className={`badge ${
                          d.dispatch_mode === 'Renewable Storage Mode' ? 'badge-renewable' : 'badge-grid'
                        }`}
                      >
                        {d.dispatch_mode}
                      </span>
                      {d.is_critical_overload && (
                        <span className="badge badge-overload">CRITICAL OVERLOAD &ge; 200 kW</span>
                      )}
                      {d.is_peak_hour && <span className="badge badge-peak">Peak 18–22h</span>}
                    </div>
                  </div>
                );
              }}
            />

            <Area
              type="monotone"
              dataKey="predicted_demand_kw"
              stroke="#0284c7"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#demandGradient)"
              activeDot={{ r: 6, fill: '#0284c7', stroke: '#ffffff', strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
