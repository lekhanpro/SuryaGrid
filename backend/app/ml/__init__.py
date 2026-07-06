"""ML pipeline for SuryaGrid AI Phase 1.5.

Augmented dataset construction, feature engineering, data-quality validation,
model training (scikit-learn), a model registry, and prediction. The target is
solar irradiance (the Kaggle dataset provides irradiance, not plant generation);
irradiance is converted to generation via the pvlib pipeline. See docs/ML_PIPELINE.md.
"""
