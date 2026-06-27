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

export interface EnergyInterval {
  hour: number;
  production_kw: number;
  consumption_kw: number;
  surplus_kw: number;
  deficit_kw: number;
  self_consumed_kw: number;
  grid_export_kw: number;
  grid_import_kw: number;
}

export interface EnergyBalance {
  site_id?: string;
  capacity_mw?: number;
  provider?: string;
  consumption_profile?: string;
  intervals: number;
  total_production_kwh: number;
  total_consumption_kwh: number;
  total_surplus_kwh: number;
  total_deficit_kwh: number;
  total_self_consumed_kwh: number;
  total_grid_export_kwh: number;
  total_grid_import_kwh: number;
  self_consumption_percent: number;
  breakdown: EnergyInterval[];
}

export interface SettlementInterval {
  target_kw: number;
  actual_kw: number;
  shortfall_kw: number;
  surplus_kw: number;
  penalty: number;
  bonus: number;
  discount: number;
  net_owner: number;
}

export interface SettlementDay {
  site_id?: string;
  capacity_mw?: number;
  consumption_profile?: string;
  intervals: number;
  total_penalty: number;
  total_bonus: number;
  total_discount: number;
  net_owner: number;
  total_shortfall_kwh: number;
  total_surplus_kwh: number;
  rl_rates?: RLRates | null;
  settlements: SettlementInterval[];
}

export interface RLRates {
  penalty_rate: number;
  bonus_rate: number;
  discount_rate: number;
  policy_trained: boolean;
}

export interface TrainingRun {
  id: string;
  algorithm: string;
  episodes: number;
  data_source: string;
  best_reward: number;
  mean_reward: number;
  final_rates: RLRates | null;
  created_at: string;
}

export interface KarnatakaRegion {
  name: string;
  capacity_mw: number;
  discom: string;
}

export interface KarnatakaRegions {
  total_capacity_mw: number;
  dsm_band_percent: number;
  regions: Record<string, KarnatakaRegion[]>;
}

export interface BescomStatus {
  connector: {
    operator: string;
    mode: string;
    is_live: boolean;
    note: string;
  };
  kerc_solar_band_percent: number;
  slabs: { range_percent: string; rate_inr_per_kwh: number }[];
}

export interface CurrentWeather {
  site_id: string;
  provider: string;
  timestamp: string;
  ghi_w_m2: number;
  dni_w_m2: number;
  dhi_w_m2: number;
  temperature_c: number;
  cloud_cover_percent: number;
  wind_speed_mps: number;
}
