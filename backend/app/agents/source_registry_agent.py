"""SourceRegistryAgent - source records, validation, and formula references.

Thin coordinator over app.data_sources.source_registry. Provides validation
(every source must carry a URL and a valid classification) and lookups used by the
API and by prediction responses to cite sources. See docs/SOURCE_REGISTRY.md.
"""

from __future__ import annotations

from app.data_sources import source_registry as sr


class SourceRegistryAgent:
    def list_sources(self, type_filter: str | None = None) -> list[dict]:
        return [s.to_dict() for s in sr.list_sources(type_filter)]

    def get_source(self, source_id: str) -> dict | None:
        rec = sr.get_source(source_id)
        return rec.to_dict() if rec else None

    def cite(self, *source_ids: str) -> list[dict]:
        return sr.cite(*source_ids)

    def formula_references(self) -> list[dict]:
        return [s.to_dict() for s in sr.list_sources("formula")]

    def validate(self) -> dict:
        """Every source must have a URL and a valid classification."""
        problems: list[str] = []
        for rec in sr.list_sources():
            if not rec.url:
                problems.append(f"{rec.id}: missing url")
            if rec.classification not in sr.VALID_CLASSIFICATIONS:
                problems.append(f"{rec.id}: invalid classification '{rec.classification}'")
        return {"valid": not problems, "count": len(sr.SOURCES), "problems": problems}
