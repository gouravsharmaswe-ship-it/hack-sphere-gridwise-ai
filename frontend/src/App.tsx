import React, { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { MetricCards } from './components/MetricCards';
import { ForecastChart } from './components/ForecastChart';
import { DispatchTimeline } from './components/DispatchTimeline';
import { AlertBanner } from './components/AlertBanner';
import { ForecastControls } from './components/ForecastControls';
import { TelemetryUploadModal } from './components/TelemetryUploadModal';
import { HistoryDrawer } from './components/HistoryDrawer';
import {
  fetchForecastById,
  fetchHistory,
  fetchModelStatus,
  request24hForecast,
} from './services/api';
import { ForecastResponse, HistoryItem, ModelStatus } from './types';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [historyList, setHistoryList] = useState<HistoryItem[]>([]);
  const [isForecasting, setIsForecasting] = useState<boolean>(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState<boolean>(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const loadInitialData = async () => {
    try {
      const [status, hist] = await Promise.all([
        fetchModelStatus().catch(() => null),
        fetchHistory().catch(() => []),
      ]);
      if (status) setModelStatus(status);
      if (hist) setHistoryList(hist);

      // Run initial forecast
      await handleRunForecast({});
    } catch (err: any) {
      setApiError(err.message || 'Initialization failed');
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const handleRunForecast = async (params: {
    scenario_type?: string;
    start_time?: string;
    base_temp_c?: number;
    base_humidity_pct?: number;
  }) => {
    setIsForecasting(true);
    setApiError(null);
    try {
      const result = await request24hForecast(params);
      setForecast(result);

      // Refresh history
      const updatedHistory = await fetchHistory().catch(() => []);
      setHistoryList(updatedHistory);
    } catch (err: any) {
      setApiError(err.message || 'Forecast execution failed');
    } finally {
      setIsForecasting(false);
    }
  };

  const handleSelectHistoricalRun = async (id: string) => {
    setIsForecasting(true);
    setApiError(null);
    try {
      const runDetails = await fetchForecastById(id);
      setForecast(runDetails);
    } catch (err: any) {
      setApiError(err.message || 'Failed to load historical forecast');
    } finally {
      setIsForecasting(false);
    }
  };

  return (
    <div className="app-container">
      <Navbar
        modelStatus={modelStatus}
        onOpenUpload={() => setIsUploadModalOpen(true)}
        onOpenHistory={() => setIsHistoryDrawerOpen(true)}
        onRunForecast={() => handleRunForecast({})}
        isForecasting={isForecasting}
      />

      <main className="main-content">
        {apiError && (
          <div
            style={{
              padding: '0.85rem 1.25rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--overload-bg)',
              color: 'var(--overload-text)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
            }}
          >
            <AlertCircle size={18} />
            <span>{apiError}</span>
          </div>
        )}

        {/* Independent Critical Overload Banner */}
        {forecast && <AlertBanner data={forecast.data} />}

        {/* Operational Overview Metrics */}
        <MetricCards
          summary={forecast?.summary ?? null}
          modelStatus={modelStatus}
          horizonHours={forecast?.horizon_hours ?? 24}
        />

        {/* Forecasting Horizon Controls */}
        <ForecastControls
          onRunForecast={handleRunForecast}
          forecastId={forecast?.forecast_id ?? null}
          isForecasting={isForecasting}
        />

        {/* Main 24-Hour Energy Demand Chart */}
        {forecast && (
          <ForecastChart
            data={forecast.data}
            isDemoMode={forecast.is_demo_mode}
          />
        )}

        {/* Dispatch Timeline & Recommendations Table */}
        {forecast && <DispatchTimeline data={forecast.data} />}
      </main>

      <footer className="footer">
        <div style={{ maxWidth: 1400, margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <strong>Gridwise AI</strong> — HackSphere 3.0 Microgrid Demand Forecasting Engine
          </div>
          <div style={{ fontSize: '0.75rem' }}>
            Deployed with Zoho Catalyst AppSail & Slate Architecture &bull; Decision Support Only
          </div>
        </div>
      </footer>

      {/* Modals */}
      <TelemetryUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onApplyUploadedData={() => handleRunForecast({})}
      />

      <HistoryDrawer
        isOpen={isHistoryDrawerOpen}
        onClose={() => setIsHistoryDrawerOpen(false)}
        historyList={historyList}
        onSelectRun={handleSelectHistoricalRun}
      />
    </div>
  );
};

export default App;
