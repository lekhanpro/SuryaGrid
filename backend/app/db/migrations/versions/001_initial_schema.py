"""Initial schema (owners, consumers, sites, readings, forecasts, settlements, training_runs)

Revision ID: 001
Revises: None
Create Date: 2026-06-26

Note: app startup also runs metadata.create_all (init_db), so this migration is
for PostgreSQL/TimescaleDB deployments that manage schema via Alembic. The GUID
type maps to native UUID on PostgreSQL and CHAR(36) elsewhere.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.types import GUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "owners",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "consumers",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("profile", sa.String(50), server_default="commercial"),
        sa.Column("base_load_kw", sa.Float, server_default="50.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "sites",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("owner_id", GUID(), sa.ForeignKey("owners.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("timezone", sa.String(50), server_default="Asia/Kolkata"),
        sa.Column("capacity_mw", sa.Float, nullable=False),
        sa.Column("tilt", sa.Float, server_default="20.0"),
        sa.Column("azimuth", sa.Float, server_default="180.0"),
        sa.Column("altitude", sa.Float, server_default="0.0"),
        sa.Column("allowed_dsm_threshold_percent", sa.Float, server_default="10.0"),
        sa.Column("penalty_rate_per_mwh", sa.Float, server_default="12000.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "readings",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("site_id", GUID(), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ghi", sa.Float, nullable=False),
        sa.Column("dni", sa.Float, server_default="0.0"),
        sa.Column("dhi", sa.Float, server_default="0.0"),
        sa.Column("temp", sa.Float, nullable=False),
        sa.Column("cloud_cover", sa.Float, nullable=False),
        sa.Column("wind", sa.Float, server_default="2.0"),
        sa.Column("source", sa.String(50), server_default="open-meteo"),
        sa.Column("quality_flag", sa.Integer, server_default="1"),
    )
    op.create_table(
        "forecasts",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("site_id", GUID(), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_kw", sa.Float, nullable=False),
        sa.Column("clearsky_kw", sa.Float, server_default="0.0"),
        sa.Column("confidence", sa.Float, server_default="0.8"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "settlements",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("site_id", GUID(), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("consumer_id", GUID(), sa.ForeignKey("consumers.id"), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("target_kw", sa.Float, nullable=False),
        sa.Column("actual_kw", sa.Float, nullable=False),
        sa.Column("penalty", sa.Float, server_default="0.0"),
        sa.Column("bonus", sa.Float, server_default="0.0"),
        sa.Column("discount", sa.Float, server_default="0.0"),
        sa.Column("net_owner", sa.Float, server_default="0.0"),
        sa.Column("penalty_rate", sa.Float, server_default="0.0"),
        sa.Column("bonus_rate", sa.Float, server_default="0.0"),
        sa.Column("discount_rate", sa.Float, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "training_runs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("algorithm", sa.String(50), server_default="REINFORCE"),
        sa.Column("episodes", sa.Integer, nullable=False),
        sa.Column("data_source", sa.String(50), server_default="open-meteo-archive"),
        sa.Column("best_reward", sa.Float, nullable=False),
        sa.Column("mean_reward", sa.Float, server_default="0.0"),
        sa.Column("final_rates", sa.JSON, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", GUID(), nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_readings_site_ts", "readings", ["site_id", "ts"])
    op.create_index("ix_forecasts_site_ts", "forecasts", ["site_id", "ts"])
    op.create_index("ix_settlements_site_ts", "settlements", ["site_id", "window_start"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("training_runs")
    op.drop_table("settlements")
    op.drop_table("forecasts")
    op.drop_table("readings")
    op.drop_table("sites")
    op.drop_table("consumers")
    op.drop_table("owners")
