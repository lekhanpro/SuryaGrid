export interface SolarSite {
  label: string;
  latitude: number;
  longitude: number;
  capacity_mw: number;
  tilt: number;
}

export const LOCATIONS: SolarSite[] = [
  { label: "Bhadla, Rajasthan", latitude: 27.53, longitude: 71.91, capacity_mw: 100, tilt: 27 },
  { label: "Pavagada, Karnataka", latitude: 14.1, longitude: 77.28, capacity_mw: 100, tilt: 14 },
  { label: "Kurnool, Andhra Pradesh", latitude: 15.68, longitude: 78.28, capacity_mw: 50, tilt: 16 },
  { label: "New Delhi", latitude: 28.61, longitude: 77.21, capacity_mw: 50, tilt: 28 },
];

export const CONSUMPTION_PROFILES = ["residential", "commercial", "industrial"] as const;
