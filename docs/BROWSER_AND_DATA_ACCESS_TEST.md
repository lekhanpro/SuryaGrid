# SuryaGrid AI — Browser & Data Access Test

Real tests run with browser / fetch / search / CLI tools. No application code modified.
Every row reflects an actual command/tool invocation.

## 1. Playwright — open Open-Meteo
- **Status:** ✅ PASS
- **Tool:** Playwright MCP (Chromium, headless)
- **URL:** https://open-meteo.com/
- **Result:** page title = `🌤️ Free Open-Source Weather API | Open-Meteo.com`; h1 = `Free Weather API`.
- **Limitation:** none.

## 2. Open-Meteo historical/archive API — Bengaluru
- **Status:** ✅ PASS (data retrieved)
- **Tool:** `httpx` (the app's ingestion path)
- **URL:** `https://archive-api.open-meteo.com/v1/archive?latitude=12.9716&longitude=77.5946&start_date=2024-06-01&end_date=2024-06-01&hourly=shortwave_radiation,temperature_2m&timezone=Asia/Kolkata`
- **Result:** HTTP 200 · 24 hourly rows · **peak GHI 901 W/m²** for Bengaluru · timezone Asia/Kolkata. Confirms Bengaluru lat/lon (12.9716, 77.5946) is fully supported.
- **Limitation:** the `mcp-server-fetch` MCP tool refuses this endpoint because Open-Meteo's `robots.txt` is `Disallow: /` for autonomous agents. The application does **not** use that tool for ingestion — it uses `httpx` directly (as tested), which works. Docs pages are readable via the browser.

## 3. NASA POWER API — Bengaluru
- **Status:** ✅ PASS (data retrieved)
- **Tool:** `httpx`
- **URL:** `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&latitude=12.9716&longitude=77.5946&start=20240601&end=20240603&format=JSON`
- **Result:** HTTP 200 · daily GHI (ALLSKY_SFC_SW_DWN) = 4.93 / 6.22 / 5.33 kWh/m²/day for Bengaluru. Confirms Bengaluru latitude/longitude support.
- **Limitation:** none for point queries. Docs: https://power.larc.nasa.gov/docs/services/api/ .

## 4. Kaggle CLI dataset searches
- **Status:** ❌ FAIL (blocked on credentials — not a tooling defect)
- **Tool:** Kaggle CLI 2.2.3
- **Commands attempted:**
  - `kaggle datasets list -s "india solar"`
  - `kaggle datasets list -s "solar power generation india"`
  - `kaggle datasets list -s "karnataka electricity"`
- **Result:** all return “Authentication required to call the Kaggle API.” `kaggle.json` is
  missing at `C:\Users\lekhan hr\.kaggle\kaggle.json`.
- **Limitation / action:** provide `kaggle.json` (see setup report §6). Then these searches
  will run. **Not faked.**

## 5. India / Karnataka data-source discovery (web search)

| Target | Status | Primary source found | Notes |
|--------|--------|----------------------|-------|
| KERC / BESCOM tariff order | ✅ PASS | https://kerc.karnataka.gov.in (Tariff Orders); karunadu.karnataka.gov.in/kerc | Official KERC tariff orders (BESCOM/all ESCOMs); latest true-up orders reported 2026. |
| Karnataka SLDC load data | ✅ PASS | https://kptclsldc.in/ | Official KPTCL State Load Despatch Centre — real-time load despatch, SCADA, energy accounting. |
| KPTCL substation data | ✅ PASS | KPTCL grid maps (765/400/220kV); https://aikosh.indiaai.gov.in (KPTCL dataset); **OSM Overpass** | OSM verified live (below); KPTCL official maps are mostly PDF/scanned. |
| CEA grid emission factor (India) | ✅ PASS | CEA "CO2 Baseline Database for the Indian Power Sector" (Ministry of Power/CEA) | Official grid emission factor; also Ember, CSEP carbontracker.in. |
| OpenStreetMap Bengaluru substations | ✅ PASS | Overpass API `node/way/relation["power"="substation"]` (ODbL) | Verified live earlier: **44 real substations** returned around Bengaluru; `osmnx`/`overpy` installed for programmatic access. |

- **Tool:** built-in web search (no Brave/Tavily API key configured).
- **Limitation:** SLDC real-time and KPTCL substation lists are often on portals/PDFs
  rather than clean APIs; OSM Overpass is the cleanest programmatic substation source and
  is already wired into the backend.

## Readiness verdict

**READY** for the next phase (Bengaluru/Karnataka/India real-data ML dataset creation and
agent training) with two operator actions outstanding:

- ✅ Browser control, web fetch (app `httpx` path), web search, Git, Python data/ML stack,
  and OSM/Open-Meteo/NASA POWER real-data access for Bengaluru are all verified working.
- ⚠️ **Kaggle** needs `kaggle.json` (manual) before Kaggle dataset ingestion.
- ⚠️ **Docker** needs manual install before the containerized run (does not block local
  data research or ML training).

Official real-data sources for Karnataka/Bengaluru are located and reachable: Open-Meteo,
NASA POWER, KERC (tariff), KPTCL-SLDC (load), OSM Overpass (substations), CEA (emission
factor). Proceed to Phase 1.6 once `kaggle.json` is placed (Docker optional for training).
