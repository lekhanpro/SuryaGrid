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
  panel_efficiency: number;
  created_at: string;
}

export interface PredictRequest {
  site_id: string;
  solar_capacity_mw: number;
  irradiance_w_m2: number;
  cloud_cover_percent: number;
  temperature_c: number;
  scheduled_generation_mw: number;
  allowed_dsm_threshold_percent: number;
  penalty_rate_per_mw: number;
}

export interface PredictResult {
  site_id: string;
  predicted_generation_mw: number;
  scheduled_generation_mw: number;
  deviation_mw: number;
  deviation_percent: number;
  allowed_dsm_threshold_percent: number;
  penalty_status: string;
  estimated_penalty_cost: number;
  fuzzy_risk_score: number;
  fuzzy_risk_level: string;
  confidence_score: number;
  explanation: string;
}

export interface TimelineEntry {
  timestamp: string;
  irradiance_w_m2: number;
  cloud_cover_percent: number;
  temperature_c: number;
  predicted_generation_mw: number;
  scheduled_generation_mw: number;
  deviation_mw: number;
  deviation_percent: number;
  penalty_status: string;
  fuzzy_risk_level: string;
}

export interface TimelineData {
  site_id: string;
  date: string;
  timeline: TimelineEntry[];
}

export interface SummaryData {
  site_id: string;
  date: string;
  total_intervals: number;
  total_predicted_mw: number;
  total_scheduled_mw: number;
  penalty_intervals: number;
  max_deviation_percent: number;
  capacity_mw: number;
}
