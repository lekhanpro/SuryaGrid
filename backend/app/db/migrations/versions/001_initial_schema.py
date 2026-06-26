"""Initial schema

Revision ID: 001
Revises: None
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
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
        "site_access",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
    )

    op.create_table(
        "weather_readings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ghi_w_m2", sa.Float, nullable=False),
        sa.Column("dni_w_m2", sa.Float, server_default="0.0"),
        sa.Column("dhi_w_m2", sa.Float, server_default="0.0"),
        sa.Column("temperature_c", sa.Float, nullable=False),
        sa.Column("cloud_cover_percent", sa.Float, nullable=False),
        sa.Column("wind_speed_mps", sa.Float, server_default="2.0"),
        sa.Column("source", sa.String(50), server_default="open-meteo"),
        sa.Column("quality_flag", sa.Integer, server_default="1"),
    )

    op.create_table(
        "generation_readings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_generation_mw", sa.Float, nullable=True),
        sa.Column("predicted_generation_mw", sa.Float, nullable=True),
        sa.Column("source", sa.String(50), server_default="pvlib"),
    )

    op.create_table(
        "dsm_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("predicted_generation_mw", sa.Float, nullable=False),
        sa.Column("scheduled_generation_mw", sa.Float, nullable=False),
        sa.Column("deviation_mw", sa.Float, nullable=False),
        sa.Column("deviation_percent", sa.Float, nullable=False),
        sa.Column("penalty_status", sa.String(30), nullable=False),
        sa.Column("estimated_penalty_cost", sa.Float, server_default="0.0"),
        sa.Column("risk_score", sa.Float, server_default="0.0"),
        sa.Column("risk_level", sa.String(20), server_default="LOW"),
        sa.Column("confidence_score", sa.Float, server_default="0.8"),
        sa.Column("explanation", sa.Text, nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("details", JSON, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_weather_site_ts", "weather_readings", ["site_id", "ts"])
    op.create_index("ix_generation_site_ts", "generation_readings", ["site_id", "ts"])
    op.create_index("ix_dsm_results_site_ts", "dsm_results", ["site_id", "ts"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("dsm_results")
    op.drop_table("generation_readings")
    op.drop_table("weather_readings")
    op.drop_table("site_access")
    op.drop_table("sites")
    op.drop_table("users")
