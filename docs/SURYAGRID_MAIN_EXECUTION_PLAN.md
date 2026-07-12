# SuryaGrid AI - Main Plan Execution Roadmap

Version 1.0 | 9 July 2026 | Planning baseline: current repository at commit `5bed3cd`

## 1. Purpose

This is the execution plan for the **complete handwritten main plan**, not only the later
substation/DSM feature. It connects the original four levels, the handwritten Phase 1 loop, and
the code that has been implemented since.

The target outcome is a controlled solar decision-support platform that can answer:

1. How much power can each DG/solar station generate over time?
2. How does that compare with schedule, request, or demand?
3. What is the resulting energy gap and DSM/reward/penalty state?
4. What action should an operator consider, with complete source and calculation trace?
5. When sufficient evidence exists, can a constrained RL policy improve recommendations without
   controlling money or equipment unsafely?

## 2. Scope alignment

### Main four-level plan

| Level | Main-plan meaning | Execution interpretation |
|---|---|---|
| L1 | API / Solcast and data inputs | Provider-neutral solar, weather, station, schedule, load, and telemetry foundation |
| L2 | Cloud/weather, S/M, ML, station generation | Data quality, solar/cloud/load forecasts, pvlib energy math, uncertainty |
| L3 | Cost, incentive, penalty, reward, discount, RL | Approved deterministic policy first; RL only after real economics and telemetry |
| L4 | Workflow | Six logical agents, APIs/tools, QA, dashboard, alerts, audit, later hardware/SCADA |

### Phase reconciliation

The handwritten Phase 1 note defines a useful first loop: irradiance nowcast -> solar generation
timeline -> schedule/agreement comparison -> DSM threshold -> penalty/no-penalty risk. The old
Phase 1 specification implemented a toy-data version. The repository now goes further with real
weather, physics/ML, source provenance, substations, APIs, UI, and deployment assets.

For planning, use:

- **Completed foundation:** historical toy/formula MVP plus present real-data prototype.
- **Current state:** decision-support prototype; not a settlement system and not a control system.
- **Next release:** live/shadow pilot for 1-3 sites.
- **Later release:** validated reward policy, conditional RL, and read-only plant integration.

## 3. Current implementation checkpoint

Status was verified on 9 July 2026.

| Capability | Status | Evidence / limitation |
|---|---|---|
| FastAPI backend and REST APIs | Implemented | 61 `/api/v1` routes |
| Automated backend verification | Implemented | 118 tests passed; Ruff passed |
| Next.js operator interface | Implemented prototype | Production build passed; 14 application routes |
| Live weather | Partial | Open-Meteo works; Solcast/NASA live failover not wired |
| Solar generation forecast | Strong prototype | pvlib plus ML; output is estimated, not measured |
| Cloud-risk forecast | Implemented prototype | Model cards and inference path exist |
| Substation context | Implemented prototype | 344 OSM substations; capacity absent, voltage incomplete |
| DSM classification | Decision-support only | Official monetary tariffs are pending |
| Reward/discount settlement | Not approved | Code defaults are illustrative and must be quarantined |
| RL | Research stub only | Production card blocked for insufficient real environment data |
| Authentication and tenancy | Gap | Plan/settings exist; enforcement not complete |
| SCADA/plant telemetry | Gap | No real connector or measured local PV/load |
| Deployment | Partial | Docker/single-instance path exists; managed AWS is unverified code |
| Production operations | Gap | HTTPS, SLOs, monitoring, backup/restore need verification |

## 4. Target operating workflow

### Trigger and context

1. A scheduler or operator selects a station, horizon, schedule/request, and operating mode.
2. The Orchestrator creates a trace ID and resolves station metadata, timezone, units, nameplate,
   permissions, and applicable policy version.
3. Missing required inputs are marked and block dependent calculations.

### Data acquisition and quality

4. The Source/API Agent requests live solar/weather data and retrieves recent actuals.
5. Provider responses are normalized to a canonical interval schema.
6. Quality gates check freshness, completeness, unit range, timestamp alignment, location, source,
   duplicate records, and fallback status.
7. Raw payloads and normalized records are stored with immutable lineage.

### Forecast and deterministic calculation

8. The Forecast Agent produces irradiance, PV generation, and - when local data permits - load
   forecasts with confidence intervals.
9. The Cloud/Weather Risk Agent provides cloud-regime and drop-risk probabilities.
10. The Logic/Calculation Agent uses versioned pvlib/energy formulas to calculate interval energy,
    scheduled-versus-expected gap, and operational limits.
11. If measured actual generation is available, the system computes forecast error separately
    from the schedule deviation. Predicted values must never be described as measured actuals.

### Policy, QA, and publication

12. The Reward/Policy Agent applies the effective-dated, approved deterministic DSM or incentive
    policy. Until approval, only risk/band output is permitted; rupee values remain disabled.
13. A policy or RL recommendation is advisory, bounded, explainable, and human-approved.
14. QA checks data quality, model version, formula bounds, confidence, policy version, and
    calculation trace. Failed checks route to refetch, recompute, manual review, or blocked state.
15. Results are persisted and exposed to the API, operator dashboard, timeline, alerts, and audit
    log.
16. Actual outcomes return later for monitoring, forecast evaluation, and - only after the
    research gate - offline RL learning.

## 5. Six logical agent contracts

| Agent | Required input | Output | Failure behavior | Initial release rule |
|---|---|---|---|---|
| Orchestrator | station, horizon, schedule, mode | state, trace, final result | retry bounded; block honestly | no hidden agent decisions |
| Source/API | source config, coordinates, interval | normalized series + provenance | failover or unavailable | two live providers before pilot |
| Forecast | quality-approved features | GHI/PV/load forecast + interval | formula fallback, labelled | site validation required |
| Cloud/Weather Risk | weather and irradiance features | cloud risk + confidence | unknown risk state | no invented camera input |
| Logic/Calculation | forecast, schedule, constraints | energy and gap calculations | block missing dependencies | deterministic/versioned |
| Reward/Policy | gap, policy, approved economics | band/reward/penalty proposal | no-money blocked state | RL advisory only |

Specialized code modules may remain separate; these six contracts are the product-level ownership
model.

## 6. Workstreams and detailed execution

### Workstream A - Scope, policy, and evidence lock

**When:** Weeks 0-1  
**Owner:** Product lead + energy-domain lead + technical lead  
**Depends on:** none

Tasks:

- Approve the four-level scope and name each unclear handwritten concept.
- Define the first 1-3 pilot sites, personas, settlement interval, schedule source, and decision
  boundary.
- Reclassify all current monetary outputs as illustrative; disable unsupported rupee values in
  user-facing paths.
- Freeze the canonical provenance labels and missing-data behavior.
- Baseline the API inventory, model cards, test results, security gaps, and deployment topology.

Exit gate:

- Signed scope/assumption register.
- No unapproved money value appears as regulatory truth.
- Pilot success metrics and blocked states are agreed.

### Workstream B - Official data and regulatory access

**When:** Weeks 2-5; external lead time may add 4-8+ weeks  
**Owner:** Product/domain lead + data engineer  
**Depends on:** Workstream A

Tasks:

- Obtain applicable KERC/CERC/BESCOM DSM/tariff orders and legal review.
- Secure KPTCL/BESCOM/SLDC or pilot-site access to station capacity, voltage, schedule, load, and
  interval actuals.
- Obtain plant nameplate, tilt/azimuth, inverter limits, meter definitions, interval and timezone.
- Define licensing, consent, retention, data-sharing, and incident contacts.
- Write effective-dated source contracts and regulatory test cases.

Exit gate:

- Approved regulatory source or an explicit "decision-support only/no-money" scope.
- At least one pilot site can supply measured PV and schedule data.
- Data owners, refresh frequency, quality threshold, and retention are recorded.

### Workstream C - L1 production data foundation

**When:** Weeks 3-7  
**Owner:** Backend/data team  
**Depends on:** Workstream A; runs alongside B

Tasks:

- Add a second live provider; integrate Solcast if contractually required.
- Implement provider health, quota persistence, bounded retries, circuit breaking, and failover.
- Add immutable raw payload archive and idempotent normalized ingestion.
- Add late-data, duplicate, gap, range, timezone, and unit checks with quarantine.
- Schedule backfill and live ingestion under observable jobs.
- Add time-series indexing/retention and source-to-feature lineage.
- Create station, schedule, actual-generation, load, and policy-version contracts.

Exit gate:

- Thirty consecutive days of pilot-feed operation or an agreed accelerated reliability window.
- Measured completeness >= 98%, documented freshness target, zero silent synthetic fallback.
- Every value resolves to provider, timestamp, location, unit, and transformation version.

### Workstream D - L2 forecast and calculation validation

**When:** Weeks 6-11  
**Owner:** ML/energy team  
**Depends on:** B for measured truth; C for reliable ingestion

Tasks:

- Backtest irradiance and PV generation by site and season with time-based splits.
- Calibrate uncertainty and define operating thresholds for MAE/RMSE/bias/coverage.
- Validate cloud-risk predictions and link risk to forecast confidence.
- Build local load forecast only when local load truth exists; keep India-wide models non-production.
- Separate predicted generation, measured actual generation, schedule, and demand.
- Version pvlib assumptions, loss factors, inverter limits, and all formula inputs.
- Add drift, missing-feature, bounds, model rollback, and champion/challenger tests.

Exit gate:

- Signed site-level model validation report.
- Prediction intervals and known limits are visible in API/UI.
- A deterministic fallback produces labelled output or blocks; it never fabricates actuals.

### Workstream E - L3 deterministic DSM and incentive policy

**When:** Weeks 8-12  
**Owner:** Energy-domain lead + backend engineer + compliance reviewer  
**Depends on:** B and D

Tasks:

- Encode effective-dated rule profiles with regulator, region, denominator, interval, slab, and
  source citation.
- Test boundary values, over/under generation treatment, time aggregation, and unit conversion.
- Separate forecasted DSM risk from settlement based on measured actuals.
- Define owner reward and consumer discount only after legal/business approval.
- Produce an immutable calculation trace and a manual recomputation worksheet.
- Add dual approval for rule publication and immediate rollback.

Exit gate:

- Golden regulatory test suite passes.
- Independent reviewer reproduces sample results.
- Unapproved profiles emit risk/band only and never emit currency.

### Workstream F - L4 secure operator workflow and integration

**When:** Weeks 10-14  
**Owner:** Frontend/backend/platform team  
**Depends on:** C; validated results from D/E for final acceptance

Tasks:

- Implement JWT/OIDC, RBAC, tenant/site isolation, audit logs, and enforced rate limits.
- Make a single station selection drive weather, solar, cloud, generation, DSM, source, and trace
  views.
- Add measured-versus-predicted distinction, missing-data panels, confidence, and blocked reasons.
- Add alerts/reports with acknowledgment and escalation state.
- Implement one read-only pilot connector (file/API/Modbus/MQTT gateway as the site permits).
- Keep all control commands disabled in the first pilot.

Exit gate:

- Operator UAT passes for normal, fallback, stale, missing, and policy-blocked scenarios.
- Security tests prove site isolation and role enforcement.
- Read-only connector can replay data without affecting plant operation.

### Workstream G - Safe RL research gate

**When:** Weeks 12-17, conditional  
**Owner:** ML/research lead + energy-domain reviewer  
**Depends on:** measured PV/load, approved economics, validated deterministic baseline

Tasks:

- Define state, action, constraints, reward, counterfactual simulator, and forbidden actions.
- Train only on approved historical/simulated data with leakage checks.
- Compare against no-action and deterministic policy baselines.
- Run stress tests for rare weather, missing data, price extremes, and policy changes.
- Expose recommendations only in shadow mode with reason, bounds, confidence, and rollback.
- Record every proposal, human decision, actual outcome, and policy/model version.

Exit gate:

- Offline policy beats the deterministic baseline on agreed metrics without safety violations.
- Domain and risk reviewers sign off.
- RL remains advisory during the pilot; it cannot set tariffs, money, or dispatch.

If dependencies are absent at Week 12, pause this workstream without delaying the decision-support
pilot.

### Workstream H - Platform hardening and controlled pilot

**When:** Hardening Weeks 14-18; pilot Weeks 19-22  
**Owner:** Platform/SRE + QA + pilot owner  
**Depends on:** C-F; G only for RL-assisted pilot

Tasks:

- Verify HTTPS/domain, secret storage, dependency scanning, CI/CD, and environment separation.
- Add logs, metrics, traces, data-quality alerts, model drift alerts, and SLO dashboards.
- Test backups, restore, failover, provider outage, rollback, and incident response.
- Run load/performance tests and define API freshness/availability targets.
- Conduct 2-4 weeks of shadow operation; compare predictions to actuals and review every blocked
  state and policy proposal.
- Hold production-readiness review and document accepted residual risks.

Exit gate:

- No unresolved critical security issue.
- Restore and rollback drills pass.
- Pilot metrics and operator sign-off pass.
- Production, extended shadow, or stop decision is recorded.

## 7. Integrated timeline

Assumption: a cross-functional team of 3-5 engineers plus part-time product/domain/compliance
support. The dates are relative to kickoff because external data agreements are not yet dated.

| Week | Main work | Parallel work | Gate |
|---|---|---|---|
| 0-1 | Scope and evidence lock | Quarantine unsupported money | G0 scope approved |
| 2-5 | Official rules and telemetry access | Provider/data contract design | G1 source decision |
| 3-7 | L1 ingestion, quality, lineage | Security foundation | G2 reliable data |
| 6-11 | L2 site forecast validation | UI trace/provenance | G3 model validation |
| 8-12 | L3 deterministic policy | Operator workflow | G4 regulatory validation |
| 10-14 | L4 auth, UI, read-only connector | Alerts and UAT | G5 pilot ready |
| 12-17 | Conditional RL research | Hardening | G6 RL shadow approval |
| 14-18 | SRE/security hardening | Incident and restore drills | G7 operational readiness |
| 19-22 | Controlled 1-3-site shadow pilot | Drift and operator review | G8 go/extend/stop |

Expected outcomes:

- **Week 14-18:** minimum credible decision-support pilot, if measured site data is available.
- **Week 20-24:** RL-assisted gated pilot, if economics and telemetry pass the research gate.
- **Schedule risk:** add at least 4-8 weeks if official data, tariff, or site access is delayed.

## 8. Critical path and dependency rules

Critical path:

`official rules + measured telemetry -> reliable data -> site validation -> deterministic DSM ->
secure operator workflow -> shadow pilot`

RL path:

`validated deterministic baseline + measured outcomes + approved economics -> offline RL ->
stress/safety review -> advisory shadow mode`

Rules:

- Frontend polish cannot compensate for missing source truth.
- Reward/discount and currency cannot precede approved policy.
- RL cannot precede measured outcomes and a deterministic baseline.
- Control integration cannot precede read-only validation, security, audit, and human approval.
- A blocked dependency creates a smaller honest release; it does not permit fabricated data.

## 9. Acceptance scorecard

| Area | Pilot acceptance |
|---|---|
| Data | >= 98% completeness in agreed window; freshness SLO met; provenance on 100% of outputs |
| Forecast | Site/season metrics meet signed thresholds; uncertainty calibrated and visible |
| Calculation | Golden energy/DSM cases reproducible; units and policy version explicit |
| Safety | No unsupported rupee output; no autonomous dispatch; all missing inputs block honestly |
| Security | Auth, RBAC, site isolation, rate limit, secrets, audit, HTTPS verified |
| Reliability | Provider outage, retry, backup/restore, rollback, and stale-data tests pass |
| UX | Operator completes selection-to-decision workflow and understands confidence/limitations |
| RL | Optional: offline improvement plus zero constraint violation; advisory-only shadow mode |

## 10. Risks and responses

| Risk | Effect | Response |
|---|---|---|
| Official tariff/rules delayed | No real monetary settlement | Keep risk bands only; decision-support release |
| Measured PV/load unavailable | Forecast/RL cannot be locally validated | Pilot data agreement is the top commercial task |
| Solcast unavailable or costly | Source gap/quota risk | Provider-neutral contract; second live fallback |
| OSM station fields incomplete | Loading/voltage calculations blocked | Obtain official capacity/voltage; preserve nulls |
| Domain shift in India-wide models | Misleading local output | Keep non-production; train on pilot-site truth |
| Hard-coded money leaks to UI | Regulatory/credibility harm | Quarantine, label, tests that forbid unsupported currency |
| RL optimizes unsafe proxy | Financial/operational harm | constrained actions, baselines, shadow mode, human approval |
| Security remains aspirational | Cross-site data exposure | enforcement tests are a pilot gate |
| Deployment differs from IaC claims | Reliability gap | verify actual topology; document code-only assets |
| Ambiguous handwritten terms | Wrong product decomposition | assumption register and owner confirmation |

## 11. Deliverables

1. Approved scope and assumption register.
2. Data-source, station, schedule, actual, load, and policy contracts.
3. Reliable multi-provider ingestion with raw archive, quality gates, and lineage.
4. Site-validated solar/load forecasts with model cards and uncertainty.
5. Versioned deterministic energy and DSM calculation library with golden tests.
6. Secure operator dashboard, alerting, audit, and read-only connector.
7. Operations package: CI/CD, observability, SLOs, backup/restore, rollback, incident runbook.
8. Shadow-pilot report with data quality, forecast accuracy, operator findings, and go/stop decision.
9. Conditional RL evaluation report and advisory shadow policy.

## 12. Immediate next 10 working days

1. Approve this plan and the permanent context prompt.
2. Confirm the unclear cloud role, S/M term, applicable regulator, settlement interval, and pilot
   decision boundary.
3. Select 1-3 pilot sites and request nameplate, schedule, meter, PV actual, and load samples.
4. Disable or clearly isolate unsupported rupee outputs.
5. Make a single frontend station selection drive the complete agent result and source trace.
6. Verify the current hosted topology, HTTPS, production database content, and backup status.
7. Draft provider and telemetry contracts plus the official-rule evidence checklist.
8. Open the regulatory/data-access workstream; it is the longest external dependency.

## 13. Source and uncertainty note

This plan is based on the two handwritten images, current code, tests, model cards, README, and
the repository evidence matrix. The main image is partially illegible. "Cloud/Weather Agent" is
therefore a safe functional label, not a claim that the note says "Cloudinary." S/M and one
station-system acronym remain unresolved. Handwritten values such as 25 and 15% discount are not
approved requirements. All durations are planning estimates, not commitments, and must be
re-baselined after pilot data and regulatory access are confirmed.
