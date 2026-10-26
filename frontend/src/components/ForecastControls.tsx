import React, { useState } from 'react';
import { Sliders, Download, Play, RefreshCw, Sparkles } from 'lucide-react';
import { getExportCsvUrl } from '../services/api';

interface ForecastControlsProps {
  onRunForecast: (params: {
    scenario_type?: string;
    base_temp_c?: number;
    base_humidity_pct?: number;
  }) => void;
  forecastId: string | null;
  isForecasting: boolean;
}

export const ForecastControls: React.FC<ForecastControlsProps> = ({
  onRunForecast,
  forecastId,
  isForecasting,
}) => {
  const [selectedScenario, setSelectedScenario] = useState<string>('historical_sample');
  const [customTemp, setCustomTemp] = useState<number>(32);
  const [customHum, setCustomHum] = useState<number>(55);
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedScenario === 'historical_sample') {
      onRunForecast({});
    } else {
      onRunForecast({
        scenario_type: selectedScenario,
        base_temp_c: customTemp,
        base_humidity_pct: customHum,
      });
    }
  };

  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '0.85rem' }}>
        <div>
          <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sliders size={18} />
            Forecast Configuration & Scenarios
          </h2>
          <p className="card-subtitle">
            Execute 24-hour inference over historical telemetry or simulated meteorological scenarios.
          </p>
        </div>

        {forecastId && (
          <a
            href={getExportCsvUrl(forecastId)}
            className="btn btn-outline btn-sm"
            download
            title="Download predictions adhering to official HackSphere format"
          >
            <Download size={14} />
            Export predictions.csv
          </a>
        )}
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', alignItems: 'flex-end' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
              Select Forecast Input Mode
            </label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              style={{
                width: '100%',
                padding: '0.6rem 0.85rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-strong)',
                background: 'var(--bg-surface)',
                fontFamily: 'var(--font-sans)',
                fontSize: '0.85rem',
                color: 'var(--text-primary)',
              }}
            >
              <option value="historical_sample">
                Verified Historical Telemetry (sample_test_input.csv segment)
              </option>
              <option value="summer_peak">
                Simulated Scenario: High Summer Heatwave (High Cooling Demand)
              </option>
              <option value="moderate_spring">
                Simulated Scenario: Moderate Spring Day (Baseline Grid Load)
              </option>
              <option value="heatwave_overload">
                Simulated Scenario: Extreme Overload Stress Test (&ge;200 kW Overload)
              </option>
            </select>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isForecasting}
              style={{ flex: 1 }}
            >
              {isForecasting ? (
                <>
                  <RefreshCw size={16} className="spin-animation" />
                  Running Inference...
                </>
              ) : (
                <>
                  <Play size={16} />
                  Generate 24h Horizon
                </>
              )}
            </button>

            <button
              type="button"
              className="btn btn-outline"
              onClick={() => setShowAdvanced(!showAdvanced)}
              style={{ whiteSpace: 'nowrap' }}
            >
              {showAdvanced ? 'Hide Tuning' : 'Tune Weather'}
            </button>
          </div>
        </div>

        {/* Optional Weather Tuning parameters */}
        {showAdvanced && (
          <div
            style={{
              marginTop: '1rem',
              paddingTop: '1rem',
              borderTop: '1px solid var(--border-subtle)',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
            }}
          >
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Base Ambient Temperature: {customTemp}°C
              </label>
              <input
                type="range"
                min="10"
                max="45"
                step="0.5"
                value={customTemp}
                onChange={(e) => setCustomTemp(parseFloat(e.target.value))}
                style={{ width: '100%', marginTop: '0.35rem' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Relative Humidity: {customHum}%
              </label>
              <input
                type="range"
                min="20"
                max="95"
                step="1"
                value={customHum}
                onChange={(e) => setCustomHum(parseFloat(e.target.value))}
                style={{ width: '100%', marginTop: '0.35rem' }}
              />
            </div>
          </div>
        )}
      </form>
    </div>
  );
};
