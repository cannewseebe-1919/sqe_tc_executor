"""Initial tables — devices, executions, execution_steps.

Revision ID: 001
Revises: None
Create Date: 2026-04-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.String(64), primary_key=True, comment="ADB serial number"),
        sa.Column("name", sa.String(128), server_default=""),
        sa.Column("model", sa.String(128), server_default=""),
        sa.Column("android_version", sa.String(16), server_default=""),
        sa.Column("resolution", sa.String(32), server_default=""),
        sa.Column("status", sa.String(16), server_default="CONNECTED"),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("test_code", sa.Text(), nullable=False),
        sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("requested_by", sa.String(256), server_default=""),
        sa.Column("callback_url", sa.String(512), nullable=True),
        sa.Column("status", sa.String(16), server_default="QUEUED"),
        sa.Column("queue_position", sa.Integer(), server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_duration_sec", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "execution_steps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("execution_id", sa.String(36), sa.ForeignKey("executions.id"), nullable=False),
        sa.Column("step_name", sa.String(256), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), server_default="PENDING"),
        sa.Column("duration_sec", sa.Float(), server_default="0.0"),
        sa.Column("screenshot_path", sa.String(512), nullable=True),
        sa.Column("log", sa.Text(), server_default=""),
        sa.Column("error_type", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("execution_steps")
    op.drop_table("executions")
    op.drop_table("devices")
