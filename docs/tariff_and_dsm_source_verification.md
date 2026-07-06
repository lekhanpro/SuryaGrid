# Tariff & DSM Source Verification (Phase 1.7)

This document records what was **verified** about the Karnataka/India tariff and
Deviation Settlement Mechanism (DSM) framework, and — crucially — what rupee values
are **deliberately not hardcoded**. Content below was rephrased for compliance with
source licensing.

Machine-readable output: `backend/data/ml/tariff_dsm_rules_official_or_pending.json`.

## Verdict

`overall_status = NEEDS_OFFICIAL_TARIFF_SOURCE`

The regulatory *framework* (which regulators, which regulations, how deviation is
defined) is verified from official/authoritative sources. The *rupee charges* are
**not** hardcoded because they are market-price-linked and under active amendment and
litigation. SuryaGrid therefore emits **framework-only** DSM recommendations (deviation
band + direction) and does **not** compute rupee penalties in Phase 1.7.

## Verified framework references

### Central — CERC
- Regulation: **CERC (Deviation Settlement Mechanism and Related Matters) Regulations, 2024**, which replaced the 2022 DSM regulations. Source: [cercind.gov.in](https://cercind.gov.in/).
- Verified facts (paraphrased):
  - For a seller, deviation is the difference between actual injection and scheduled generation in a time block ([TTA regulatory update](https://tta.in/regulatory-update-deviation-settlement-mechanism-regulations/)).
  - Under the 2024 rules, deviation charges are tied to time-block market prices rather than a single fixed rupee/MWh rate ([S&P Global](https://www.spglobal.com/esg/s1/research-analysis/indias-new-dsm-regulations-wind-plants-may-become-unviable.html)).
  - CERC set the trajectory for the deviation-computation value "X" for wind/solar sellers in a 2026 order ([JSA Law](https://www.jsalaw.com/articles-publications/central-electricity-regulatory-commission-sets-trajectory-for-deviation-computation-in-renewable-energy-sector/)).
  - The Karnataka High Court stayed certain 2024 DSM provisions on a petition by NSEFI ([The Hindu](https://www.thehindu.com/news/national/karnataka/karnataka-high-court-stays-cercs-new-regulations-imposing-higher-penalty-for-deviation-on-renewable-energy-firms/article70916320.ece)).

### State — KERC (Karnataka)
- Regulation: **KERC (Forecasting, Scheduling, Deviation Settlement Mechanism and related matters for Sellers of Wind, Solar and WS-Hybrid Generation Sources) Regulations** — original 2015, with a 2026 final/updated framework. Sources: [KERC Regulations](https://kerc.karnataka.gov.in/info-3/Regulations/en), [KERC (old PRMS) regulations list](http://prms.karnataka.gov.in/kercold/Pages/Regulations-under-Electricity-Act-2003.aspx), and reporting via [EQ Magazine](https://www.eqmagpro.com/kerc-forecasting-scheduling-deviation-settlement-mechanism-and-related-matters-for-sellers-of-wind-solar-and-ws-hybrid-generation-sources-regulations-2026-eq/).
- Retail tariff (BESCOM) slabs are set by annual KERC tariff orders: [kerc.karnataka.gov.in](https://kerc.karnataka.gov.in/) → Tariff Orders.

## What is deliberately NOT hardcoded (and why)

| Value | Status | Reason |
|-------|--------|--------|
| DSM penalty (INR/MWh or INR/kWh) | `NEEDS_OFFICIAL_TARIFF_SOURCE` | CERC 2024 links charges to time-block market prices; value fluctuates and is under litigation. A fixed number would be false. |
| Official solar deviation band "X" (%) | `NEEDS_OFFICIAL_TARIFF_SOURCE` | Set by CERC order; must be read from the current order, not assumed. |
| BESCOM retail energy charge (INR/kWh) | `NEEDS_OFFICIAL_TARIFF_SOURCE` | Changes per annual KERC tariff order; stale values would mislead. |

## Modelling parameter (clearly labelled, not official)

- The `+/-15%` deviation band in `dsm_agent_training.parquet` and the DSM rules engine is a
  **`FALLBACK_DEFAULT` modelling choice** used only to structure the breach-risk classifier
  and recommendations. It is not represented as an official KERC/CERC percentage.

## To make DSM rupee-accurate (operator action)

1. Open the current CERC DSM 2024 order (and any KERC adoption/amendment) and record the
   applicable solar "X" band and the time-block price reference.
2. Enter the verified values into `tariff_dsm_rules_official_or_pending.json`, flip the
   relevant `status` to `OFFICIAL_SOURCE`, and set `emits_rupee_values=true`.
3. Only then will SuryaGrid compute rupee DSM charges; until then it stays framework-only.
