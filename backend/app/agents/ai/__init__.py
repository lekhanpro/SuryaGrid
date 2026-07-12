"""Agentic AI reasoning layer (Phase 1.5).

Sits BESIDE the deterministic substation orchestrator, never in front of it:
numbers come from the deterministic run; the LLM (any OpenAI-compatible endpoint)
only writes narrative insights over a numeric digest. Every LLM failure degrades
to a deterministic explanation - the platform never depends on an LLM being up.
"""
