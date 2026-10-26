import { DispatchEvaluation, DispatchMode } from '../types';

export const RENEWABLE_STORAGE_THRESHOLD_KW = 160.0;
export const CRITICAL_OVERLOAD_THRESHOLD_KW = 200.0;
export const PEAK_HOURS_START = 18;
export const PEAK_HOURS_END = 22;

export function evaluateDispatchRule(
  predictedDemandKw: number,
  timestampStr: string
): DispatchEvaluation {
  const demand = Number(predictedDemandKw);

  // Extract hour
  let hour = 0;
  try {
    // Handle formats: '2024-01-01 18:00:00' or ISO
    const clean = timestampStr.trim().replace('T', ' ');
    if (clean.includes(' ')) {
      const timePart = clean.split(' ')[1];
      hour = parseInt(timePart.split(':')[0], 10);
    } else {
      const dt = new Date(timestampStr);
      hour = dt.getUTCHours();
    }
  } catch {
    hour = 0;
  }

  const isPeak = hour >= PEAK_HOURS_START && hour <= PEAK_HOURS_END;
  const isDemandHigh = demand > RENEWABLE_STORAGE_THRESHOLD_KW;
  const isOverload = demand >= CRITICAL_OVERLOAD_THRESHOLD_KW;

  let dispatchMode: DispatchMode;
  const reasons: string[] = [];

  if (isDemandHigh && isPeak) {
    dispatchMode = 'Renewable Storage Mode';
    reasons.push(`Demand (${demand.toFixed(1)} kW > 160 kW) and Peak Hours (${hour}:00 in 18-22)`);
  } else if (isDemandHigh) {
    dispatchMode = 'Renewable Storage Mode';
    reasons.push(`High demand (${demand.toFixed(1)} kW > 160 kW)`);
  } else if (isPeak) {
    dispatchMode = 'Renewable Storage Mode';
    reasons.push(`Peak evening grid window (${hour}:00 in 18:00–22:00)`);
  } else {
    dispatchMode = 'Main Grid Mode';
    reasons.push(`Nominal load (${demand.toFixed(1)} kW <= 160 kW) outside peak hours`);
  }

  if (isOverload) {
    reasons.push(`CRITICAL OVERLOAD ALERT: Predicted load ${demand.toFixed(1)} kW >= 200 kW`);
  }

  return {
    timestamp: timestampStr,
    local_hour: hour,
    predicted_demand_kw: demand,
    dispatch_mode: dispatchMode,
    is_peak_hour: isPeak,
    is_demand_exceeding_160: isDemandHigh,
    is_critical_overload: isOverload,
    reason: reasons.join('; '),
  };
}
