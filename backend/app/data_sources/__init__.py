"""Real data-source architecture for SuryaGrid AI Phase 1.5.

Providers implement a common status contract (base_provider.DataProvider) and are
catalogued in source_registry. No provider silently substitutes another: every
provider reports availability/loaded state so the API can surface real status.
"""
