# Bengaluru / Karnataka / India — Data Source Research (Phase 1.7)

Research of the closest real data sources for a **Bengaluru/Karnataka/India** solar-DSM
platform. Each source is assessed for ML usability. Verified live where marked
"probed". Content paraphrased for licensing compliance; links are attributions.

Status legend: `READY` · `NEEDS_KEY` · `NEEDS_MANUAL_DOWNLOAD` · `NOT_USABLE` ·
`DOCUMENTATION_ONLY`.

Bengaluru reference: lat **12.9716**, lon **77.5946**, tz `Asia/Kolkata`, alt ~920 m.

---

## 1. Open-Meteo Historical Weather Archive  — `READY` ✅ (used)
- **URL:** https://archive-api.open-meteo.com/v1/archive · docs https://open-meteo.com/en/docs/historical-weather-api
- **Provider:** Open-Meteo (ERA5/ERA5-Land reanalysis backend)
- **Geography:** any coordinate → queried at Bengaluru (`REAL_COORDINATE_BASED`)
- **Variables:** temperature_2m, relative_humidity_2m, cloud_cover, shortwave_radiation (GHI), direct_radiation, direct_normal_irradiance (DNI), diffuse_radiation (DHI), wind_speed_10m, surface_pressure, precipitation, weather_code
- **Coverage:** 1940→~5 days ago · **Resolution:** hourly
- **Access:** key-less HTTPS (httpx). **License:** Open-Meteo, CC-BY 4.0 (non-commercial free tier)
- **Machine-readable:** yes (JSON) · **Usable for ML:** yes — **primary weather/solar source**
- **Limitations:** reanalysis at grid cell, not on-site pyranometer; hourly only on free tier
- **Probed:** ✅ 26,304 hourly rows for Bengaluru 2022–2024

## 2. NASA POWER — `READY` ✅ (used, cross-check)
- **URL:** https://power.larc.nasa.gov/api/temporal/hourly/point · daily .../daily/point · docs https://power.larc.nasa.gov/docs/services/api/
- **Provider:** NASA Langley (POWER project) · **Geography:** coordinate → Bengaluru (`REAL_COORDINATE_BASED`)
- **Variables:** ALLSKY_SFC_SW_DWN (GHI), ALLSKY_SFC_SW_DIFF, T2M, RH2M, WS10M, PS
- **Coverage:** 1981→ (daily), 2001→ (hourly) · **Resolution:** hourly / daily
- **Access:** key-less HTTPS · **License:** NASA open data (free)
- **Machine-readable:** yes (JSON) · **Usable for ML:** yes — **second-source GHI validation**
- **Limitations:** ~0.5° satellite grid (coarser than Open-Meteo); LST time base
- **Probed:** ✅ daily GHI vs Open-Meteo r ≈ 0.87 over 1,096 days

## 3. Kaggle — India solar / PV generation — `READY` ✅ (searched)
- **URL:** https://www.kaggle.com/datasets · e.g. `anikannal/solar-power-generation-data` (Indian plants, 34-day PV), `nekonyaa/india-re-generation-by-state-20172023`
- **Provider:** Kaggle community · **Geography:** `REAL_INDIA` (specific plants/states)
- **Variables:** plant AC/DC power, inverter, irradiation (varies by dataset)
- **Coverage:** dataset-specific (e.g. 34 days) · **Resolution:** 15-min/hourly
- **Access:** Kaggle API (token present) · **License:** per-dataset (check each)
- **Machine-readable:** yes (CSV) · **Usable for ML:** PV = short window / not Bengaluru → **PRETRAINING_ONLY** for PV
- **Limitations:** no Bengaluru-local PV plant with long history found → PV output not trained
- **Probed:** ✅ search returns results

## 4. Kaggle — India electricity / load / smart-meter — `READY` ✅ (used for load)
- **URL:** `smarthkaushal/energy-demand-profile` (India national hourly demand), `unseemlycoder/smart-energy-meters-in-bangalore-india` (~1 GB), `shubhamvashisht/hourly-load-india`
- **Provider:** Kaggle community · **Geography:** `REAL_INDIA` (national) / Bengaluru smart-meter (unverified schema)
- **Variables:** Hourly Demand Met (MW); smart-meter kWh
- **Coverage:** 2023–2024 (national demand) · **Resolution:** hourly
- **Access:** Kaggle API · **License:** per-dataset
- **Machine-readable:** yes · **Usable for ML:** national demand = **REAL_INDIA baseline**, `DOMAIN_SHIFT_RISK_HIGH` for Bengaluru
- **Limitations:** national aggregate ≠ Bengaluru feeder; Bengaluru smart-meter set is large + schema unverified
- **Probed:** ✅ used `smarthkaushal/energy-demand-profile` → 11,664 valid hourly rows

## 5. Karnataka SLDC (KPTCL) — `DOCUMENTATION_ONLY` / `NEEDS_MANUAL_DOWNLOAD`
- **URL:** https://kptclsldc.in/ · **Provider:** KPTCL State Load Despatch Centre (official, Karnataka)
- **Geography:** `REAL_KARNATAKA` (state real-time load) · **Variables:** real-time load, SCADA, energy accounting, DSM
- **Coverage:** real-time + archives · **Resolution:** block/real-time
- **Access:** web portal (reports/PDF/ASP pages), **no clean public REST API**
- **License:** government portal (terms not machine-stated) · **Machine-readable:** partial (portal/PDF)
- **Usable for ML:** the authoritative Karnataka load source, **but requires manual/scraped download** — not wired
- **Limitations:** no documented open API; would need scraping + permission → deferred (`NEEDS_OFFICIAL_SOURCE` for local load)

## 6. Grid India / POSOCO — `NEEDS_MANUAL_DOWNLOAD` / `DOCUMENTATION_ONLY`
- **URL:** https://grid-india.in/ · National Power Portal https://npp.gov.in/ (unified) · https://npp.gov.in/publishedReports
- **Provider:** Grid Controller of India (formerly POSOCO) / CEA · **Geography:** `REAL_INDIA` (national/regional, incl. Southern Region)
- **Variables:** demand met, frequency, regional supply position, DSM accounts
- **Coverage:** daily reports, historical archives · **Resolution:** daily / 15-min block (in PDFs)
- **Access:** PDF/XLS reports on portals; **no clean open REST API** · **License:** government
- **Machine-readable:** partial (XLS on NPP) · **Usable for ML:** regional demand possible via manual XLS ingestion
- **Limitations:** report-oriented, not API; Southern Region ≠ Karnataka-only

## 7. CEA — load/generation/emission — `NEEDS_MANUAL_DOWNLOAD` / `DOCUMENTATION_ONLY`
- **URL:** https://cea.nic.in/ · CO2 Baseline Database (Ministry of Power/CEA) · Open Govt Data https://www.data.gov.in/ (Power Supply Position) · NITI ICED https://iced.niti.gov.in/
- **Provider:** Central Electricity Authority · **Geography:** `REAL_INDIA` (state-wise available)
- **Variables:** power supply position (state demand/availability), generation, **grid CO2 emission factor**
- **Coverage:** monthly/annual · **Resolution:** monthly (supply position), annual (emission factor)
- **Access:** PDF/XLS; data.gov.in has some CSV · **License:** government open data
- **Machine-readable:** partial · **Usable for ML:** emission factor = single official value; monthly demand too coarse for hourly ML
- **Related machine-readable:** Ember India electricity data (https://ember-energy.org/data/india-electricity-data/) — state monthly generation/emissions 2019+ (CC-BY)

## 8. KERC / BESCOM tariff orders — `DOCUMENTATION_ONLY` (`NEEDS_OFFICIAL_TARIFF_SOURCE`)
- **URL:** https://kerc.karnataka.gov.in/ (Tariff Orders) · https://bescom.karnataka.gov.in/
- **Provider:** Karnataka Electricity Regulatory Commission / BESCOM · **Geography:** `REAL_KARNATAKA`
- **Variables:** retail slab tariffs (INR/kWh), fixed charges, RE framework
- **Coverage:** annual orders · **Access:** PDF orders · **License:** government
- **Machine-readable:** no (PDF) · **Usable for ML:** rates not auto-parsed → **framework-only**, rupee values `NEEDS_OFFICIAL_TARIFF_SOURCE`
- **Limitations:** slab rates change per annual order; PDF parsing not done (would risk stale values)

## 9. CERC DSM regulations — `DOCUMENTATION_ONLY` (`NEEDS_OFFICIAL_TARIFF_SOURCE`)
- **URL:** https://cercind.gov.in/ · verified: CERC (Deviation Settlement Mechanism and Related Matters) Regulations, 2024 (replaced 2022)
- **Provider:** Central Electricity Regulatory Commission · **Geography:** `REAL_INDIA` (central framework)
- **Variables:** deviation = actual − scheduled injection; charges **market-price-linked**; solar "X" band set by CERC order
- **Coverage:** 2024 regulation + 2026 "X" order · **Access:** PDF · **License:** government
- **Machine-readable:** no · **Usable for ML:** framework structure only; **no fixed rupee rate** (market-linked + under Karnataka HC litigation)
- **Limitations:** rupee DSM charge cannot be honestly hardcoded → deviation-band framework only

## 10. KPTCL / BESCOM substation & feeder — `NEEDS_MANUAL_DOWNLOAD` / `NEEDS_OFFICIAL_SOURCE`
- **URL:** KPTCL grid maps (765/400/220 kV, PDF), https://kptcl.karnataka.gov.in/ · aikosh.indiaai.gov.in (some KPTCL datasets)
- **Provider:** KPTCL/BESCOM · **Geography:** `REAL_KARNATAKA`
- **Variables:** substation capacity (MVA), voltage, feeder load
- **Access:** mostly scanned PDF maps · **Machine-readable:** no
- **Usable for ML:** substation **capacity/feeder load unavailable** in clean form → `NEEDS_OFFICIAL_SOURCE`; substation-level DSM disabled

## 11. OpenStreetMap / Overpass substations — `READY` ✅ (used)
- **URL:** https://overpass-api.de/api/interpreter (tag `power=substation`) · https://www.openstreetmap.org
- **Provider:** OpenStreetMap contributors · **Geography:** `REAL_LOCAL`/`REAL_BENGALURU`/`REAL_KARNATAKA`
- **Variables:** name, coordinates, voltage (tag, often missing), operator (often missing); **no capacity**
- **Coverage:** current snapshot · **Resolution:** point/way/relation
- **Access:** open HTTPS · **License:** **ODbL 1.0** (attribution © OpenStreetMap contributors)
- **Machine-readable:** yes (JSON) · **Usable for ML:** yes for locations + geometry features
- **Limitations:** capacity never present (kept null); ~41% have voltage; coordinates trusted as-is
- **Probed:** ✅ 344 substations within 45 km of Bengaluru

---

## Summary — what is actually usable for ML now

| Need | Best real source | Status | Geography label |
|------|------------------|--------|-----------------|
| Weather/solar (irradiance) | Open-Meteo + NASA POWER | READY ✅ | REAL_COORDINATE_BASED |
| Substation locations | OSM Overpass | READY ✅ | REAL_BENGALURU/KARNATAKA |
| Substation capacity/feeder load | KPTCL/BESCOM | NEEDS_OFFICIAL_SOURCE | REAL_KARNATAKA |
| Load (hourly) | Kaggle India national | READY (baseline) ✅ | REAL_INDIA (domain-shift HIGH) |
| Load (Karnataka local) | KPTCL-SLDC / Grid India | NEEDS_MANUAL_DOWNLOAD | REAL_KARNATAKA |
| Tariff / DSM rupees | KERC/BESCOM/CERC | NEEDS_OFFICIAL_TARIFF_SOURCE | REAL_KARNATAKA/INDIA |
| Local PV generation | (none found local) | NOT_AVAILABLE | — |

Conclusion: irradiance + substation locations + India-baseline load are trainable now.
Local load, substation capacity, official tariff rupees, and local PV generation remain
`NEEDS_OFFICIAL_SOURCE` / `NOT_AVAILABLE` — and are treated as such, not faked.
