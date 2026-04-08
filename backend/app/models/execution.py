"""Execution & ExecutionStep DB models."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    test_code: Mapped[str] = mapped_column(Text, comment="Python TC source code")
    device_id: Mapped[str] = mapped_column(String(64), ForeignKey("devices.id"))
    requested_by: Mapped[str] = mapped_column(String(256), default="")
    callback_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="QUEUED")
    queue_position: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    steps: Mapped[list["ExecutionStep"]] = relationship(
        back_populates="execution", order_by="ExecutionStep.step_order"
    )


class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("executions.id"))
    step_name: Mapped[str] = mapped_column(String(256))
    step_order: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    duration_sec: Mapped[float] = mapped_column(Float, default=0.0)
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    log: Mapped[str] = mapped_column(Text, default="")
    error_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    execution: Mapped["Execution"] = relationship(back_populates="steps")
