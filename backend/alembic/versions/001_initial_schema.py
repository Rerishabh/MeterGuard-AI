"""Initial schema: meters, hardware_readings, consumption_sequences, anomaly_alerts, investigation_reports

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-16 01:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Meters table
    op.create_table(
        "meters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("meter_id", sa.String(length=64), nullable=False),
        sa.Column("location_name", sa.String(length=128), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="MONITORING"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="LOW"),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_seen", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meter_id"),
    )
    op.create_index("ix_meters_id", "meters", ["id"], unique=False)
    op.create_index("ix_meters_meter_id", "meters", ["meter_id"], unique=True)

    # 2. Hardware Readings table
    op.create_table(
        "hardware_readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("meter_id", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("t1_cs", sa.Float(), nullable=True),
        sa.Column("t1_vs", sa.Float(), nullable=True),
        sa.Column("t2_cs", sa.Float(), nullable=True),
        sa.Column("t2_vs", sa.Float(), nullable=True),
        sa.Column("h1_cs", sa.Float(), nullable=True),
        sa.Column("h1_vs", sa.Float(), nullable=True),
        sa.Column("voltage_v", sa.Float(), nullable=True),
        sa.Column("current_a", sa.Float(), nullable=True),
        sa.Column("power_w", sa.Float(), nullable=True),
        sa.Column("model1_status", sa.String(length=32), nullable=True),
        sa.Column("model2_status", sa.String(length=32), nullable=True),
        sa.Column("final_status", sa.String(length=32), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["meter_id"], ["meters.meter_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hardware_readings_id", "hardware_readings", ["id"], unique=False)
    op.create_index("ix_hardware_readings_meter_id", "hardware_readings", ["meter_id"], unique=False)
    op.create_index("ix_hardware_readings_timestamp", "hardware_readings", ["timestamp"], unique=False)
    op.create_index("idx_hw_meter_timestamp", "hardware_readings", ["meter_id", "timestamp"], unique=False)

    # 3. Consumption Sequences table
    op.create_table(
        "consumption_sequences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("meter_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_type", sa.String(length=16), nullable=False),
        sa.Column("sequence_length", sa.Integer(), nullable=False),
        sa.Column("consumption_json", sa.Text(), nullable=False),
        sa.Column("reconstruction_error", sa.Float(), nullable=True),
        sa.Column("threshold_used", sa.Float(), nullable=True),
        sa.Column("threshold_99", sa.Float(), nullable=True),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="NORMAL"),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("analyzed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["meter_id"], ["meters.meter_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consumption_sequences_id", "consumption_sequences", ["id"], unique=False)
    op.create_index("ix_consumption_sequences_meter_id", "consumption_sequences", ["meter_id"], unique=False)
    op.create_index("ix_consumption_sequences_analyzed_at", "consumption_sequences", ["analyzed_at"], unique=False)
    op.create_index("idx_seq_meter_type", "consumption_sequences", ["meter_id", "sequence_type"], unique=False)

    # 4. Anomaly Alerts table
    op.create_table(
        "anomaly_alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("meter_id", sa.String(length=64), nullable=False),
        sa.Column("source_model", sa.String(length=64), nullable=False),
        sa.Column("fault_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["meter_id"], ["meters.meter_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anomaly_alerts_id", "anomaly_alerts", ["id"], unique=False)
    op.create_index("ix_anomaly_alerts_meter_id", "anomaly_alerts", ["meter_id"], unique=False)
    op.create_index("ix_anomaly_alerts_created_at", "anomaly_alerts", ["created_at"], unique=False)
    op.create_index("idx_alert_meter_severity", "anomaly_alerts", ["meter_id", "severity", "is_resolved"], unique=False)

    # 5. Investigation Reports table
    op.create_table(
        "investigation_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=True),
        sa.Column("meter_id", sa.String(length=64), nullable=False),
        sa.Column("report_markdown", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(length=64), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["alert_id"], ["anomaly_alerts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["meter_id"], ["meters.meter_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_investigation_reports_id", "investigation_reports", ["id"], unique=False)
    op.create_index("ix_investigation_reports_alert_id", "investigation_reports", ["alert_id"], unique=False)
    op.create_index("ix_investigation_reports_meter_id", "investigation_reports", ["meter_id"], unique=False)
    op.create_index("ix_investigation_reports_created_at", "investigation_reports", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("investigation_reports")
    op.drop_table("anomaly_alerts")
    op.drop_table("consumption_sequences")
    op.drop_table("hardware_readings")
    op.drop_table("meters")
