"""Phase 1.5 schema: locations, substations, weather points, DSM profiles/bands/results

Revision ID: 002
Revises: 001
Create Date: 2026-07-05

Note: app startup runs metadata.create_all (init_db), so these tables are created
automatically at runtime on SQLite and PostgreSQL alike. This migration is for
PostgreSQL deployments that manage schema changes via Alembic.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.types import GUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location_type", sa.String(50), server_default="site"),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_confidence", sa.Float, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "substations",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("voltage_level", sa.String(50), nullable=True),
        sa.Column("operator", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("district", sa.String(120), nullable=True),
        sa.Column("state", sa.String(120), nullable=True),
        sa.Column("country", sa.String(120), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("source_confidence", sa.Float, server_default="0.6"),
        sa.Column("osm_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "weather_provider_locations",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("provider", sa.String(50), server_default="open-meteo"),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "site_substation_map",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("site_id", GUID(), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("substation_id", GUID(), sa.ForeignKey("substations.id"), nullable=False),
        sa.Column("distance_km", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "dsm_rule_profiles",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("region", sa.String(120), nullable=True),
        sa.Column("regulator", sa.String(120), nullable=True),
        sa.Column("denominator", sa.String(40), server_default="available_capacity"),
        sa.Column("tolerance_percent", sa.Float, server_default="10.0"),
        sa.Column("time_block_minutes", sa.Integer, server_default="15"),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("source_status", sa.String(60), server_default="USER_CONFIGURABLE"),
        sa.Column("effective_from", sa.String(40), nullable=True),
        sa.Column("effective_to", sa.String(40), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "dsm_rule_bands",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("profile_id", GUID(), sa.ForeignKey("dsm_rule_profiles.id"), nullable=False),
        sa.Column("min_deviation_percent", sa.Float, nullable=False),
        sa.Column("max_deviation_percent", sa.Float, nullable=False),
        sa.Column("direction", sa.String(20), server_default="BOTH"),
        sa.Column("charge_formula", sa.String(255), nullable=True),
        sa.Column("charge_rate", sa.Float, server_default="0.0"),
        sa.Column("unit", sa.String(20), server_default="INR/kWh"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("source_reference", sa.String(120), nullable=True),
    )
    op.create_table(
        "dsm_results",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("site_id", GUID(), sa.ForeignKey("sites.id"), nullable=True),
        sa.Column("profile_id", GUID(), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("scheduled_generation_mw", sa.Float, server_default="0.0"),
        sa.Column("predicted_generation_mw", sa.Float, server_default="0.0"),
        sa.Column("actual_generation_mw", sa.Float, nullable=True),
        sa.Column("installed_capacity_mw", sa.Float, server_default="0.0"),
        sa.Column("deviation_mw", sa.Float, server_default="0.0"),
        sa.Column("deviation_percent", sa.Float, server_default="0.0"),
        sa.Column("deviation_direction", sa.String(20), server_default="WITHIN_LIMIT"),
        sa.Column("dsm_band", sa.String(60), nullable=True),
        sa.Column("penalty_status", sa.String(30), server_default="NO_PENALTY"),
        sa.Column("charge_rate", sa.Float, server_default="0.0"),
        sa.Column("estimated_dsm_charge", sa.Float, server_default="0.0"),
        sa.Column("rule_source", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_substations_lat_lon", "substations", ["latitude", "longitude"])
    op.create_index("ix_dsm_results_site_ts", "dsm_results", ["site_id", "ts"])


def downgrade() -> None:
    op.drop_table("dsm_results")
    op.drop_table("dsm_rule_bands")
    op.drop_table("dsm_rule_profiles")
    op.drop_table("site_substation_map")
    op.drop_table("weather_provider_locations")
    op.drop_table("substations")
    op.drop_table("locations")
