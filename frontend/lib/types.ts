export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  error?: string;
  data: T;
}

export interface Site {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  timezone: string;
  capacity_mw: number;
  tilt: number;
  azimuth: number;
  altitude: number;
  allowed_dsm_threshold_percent: number;
  penalty_rate_per_mwh: number;
  created_at: string;
}

export interface PredictRequest {
  capacity_mw: number;
  latitude?: number;
  longitude?: number;
  timezone?: string;
  tilt?: number;
  azimuth?: number;
  ghi_w_m2: number;
  dni_w_m2?: number;
  dhi_w_m2?: number;
  cloud_cover_percent: number;
  temperature_c: number;
  wind_speed_mps?: number;
  scheduled_generation_mw: number;
  allowed_dsm_threshold_percent: number;
  penalty_rate_per_mwh: number;
}

export interface PredictResult {
  timestamp: string;
  ghi_w_m2: number;
  poa_w_m2: number;
  cloud_cover_percent: number;
  temperature_c: number;
  predicted_generation_mw: number;
  energy_mwh: number;
  scheduled_generation_mw: number;
  deviation_mw: number;
  deviation_percent: number;
  allowed_dsm_threshold_percent: number;
  penalty_status: string;
  estimated_penalty_cost: number;
  risk_score: number;
  risk_level: string;
  confidence_score: number;
  explanation: string;
  capacity_mw?: number;
}

export interface TimelineEntry {
  timestamp: string;
  ghi_w_m2: number;
  poa_w_m2: number;
  cloud_cover_percent: number;
  temperature_c: number;
  predicted_generation_mw: number;
  energy_mwh: number;
  scheduled_generation_mw: number;
  deviation_mw: number;
  deviation_percent: number;
  allowed_dsm_threshold_percent: number;
  penalty_status: string;
  estimated_penalty_cost: number;
  risk_score: number;
  risk_level: string;
  confidence_score: number;
  explanation: string;
}

export interface SummaryData {
  site_id?: string;
  capacity_mw?: number;
  provider?: string;
  intervals: number;
  daylight_intervals: number;
  predicted_energy_mwh: number;
  scheduled_energy_mwh: number;
  peak_generation_mw: number;
  penalty_intervals: number;
  total_penalty_cost: number;
  max_deviation_percent: number;
}

export interface TimelineData {
  site_id: string;
  capacity_mw: number;
  provider: string;
  summary: SummaryData;
  timeline: TimelineEntry[];
}

export interface WeatherReading {
  timestamp: string;
  ghi_w_m2: number;
  dni_w_m2: number;
  dhi_w_m2: number;
  temperature_c: number;
  cloud_cover_percent: number;
  wind_speed_mps: number;
}

export interface WeatherData {
  site_id: string;
  provider: string;
  latitude: number;
  longitude: number;
  timezone: string;
  readings_count: number;
  readings: WeatherReading[];
}
