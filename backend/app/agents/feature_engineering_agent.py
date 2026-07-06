"""FeatureEngineeringAgent - build the augmented dataset with quality checks.

Coordinator over app.ml.dataset_builder and app.ml.data_quality.
See docs/ML_PIPELINE.md.
"""

from __future__ import annotations

import pandas as pd

from app.ml import data_quality, dataset_builder


class FeatureEngineeringAgent:
    def build(self, source_df: pd.DataFrame, **context) -> tuple[pd.DataFrame, dict]:
        return dataset_builder.build_augmented(source_df, **context)

    def build_from_weather(self, weather_points, source_provider="open-meteo", **context):
        src = dataset_builder.weather_points_to_frame(weather_points, source_provider)
        return dataset_builder.build_augmented(src, **context)

    def quality_report(self, df: pd.DataFrame, capacity_mw: float | None = None) -> dict:
        return data_quality.run_quality_checks(df, capacity_mw)

    def save(self, df: pd.DataFrame):
        return dataset_builder.save_augmented(df)
