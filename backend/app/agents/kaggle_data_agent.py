"""KaggleDataAgent - download/load and normalize the Kaggle solar dataset.

Coordinator over KaggleSolarProvider. Reports honest status ("Kaggle dataset not
loaded") and never silently substitutes data. See docs/DATA_SOURCE_CATALOG.md #2.
"""

from __future__ import annotations

import pandas as pd

from app.data_sources.kaggle_solar_provider import KaggleSolarProvider


class KaggleDataAgent:
    def __init__(self, provider: KaggleSolarProvider | None = None):
        self.provider = provider or KaggleSolarProvider()

    def status(self) -> dict:
        return self.provider.status().to_dict()

    def is_loaded(self) -> bool:
        return self.provider.is_loaded()

    def ingest(self) -> dict:
        return self.provider.ingest_via_api()

    def load_normalized(self) -> pd.DataFrame:
        """Return the normalized Kaggle dataframe. Raises if not loaded."""
        return self.provider.load_dataframe()
