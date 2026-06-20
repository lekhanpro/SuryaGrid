# Agent Architecture - Suryagrid AI Phase 1

## Agents

1. **OrchestratorAgent** - Coordinates all agents in sequence
2. **ToyDataAgent** - Generates synthetic weather/cloud/irradiance data
3. **ForecastAgent** - Predicts solar generation using toy formula
4. **DSMClassifierAgent** - Calculates deviation and penalty status
5. **FuzzyRiskAgent** - Assigns risk level (LOW/MEDIUM/HIGH/CRITICAL)
6. **ExplanationAgent** - Generates human-readable explanations
7. **APIManagementAgent** - Rate limiting, provider selection
8. **SecurityAgent** - JWT auth, RBAC, audit logging

## Flow

ToyData -> Forecast -> DSMClassifier -> FuzzyRisk -> Explanation

Orchestrator coordinates. Security validates upfront.
