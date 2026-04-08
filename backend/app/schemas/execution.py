"""Execution Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ExecuteRequestIn(BaseModel):
    test_code: str
    device_id: str
    requested_by: str = ""
    callback_url: Optional[str] = None


class ExecuteRequestOut(BaseModel):
    execution_id: str
    status: str
    queue_position: int


class ExecutionStatusOut(BaseModel):
    execution_id: str
    status: str
    current_step: Optional[str] = None
    progress: Optional[str] = None
    started_at: Optional[datetime] = None


class StepResultOut(BaseModel):
    name: str
    status: str
    duration_sec: float
    screenshot_url: Optional[str] = None
    log: str = ""
    error_type: Optional[str] = None


class ExecutionSummary(BaseModel):
    total_steps: int
    passed: int
    failed: int
    aborted: bool = False
    abort_reason: Optional[str] = None


class DeviceInfoOut(BaseModel):
    model: str
    android_version: str
    resolution: str


class ExecutionResultCallback(BaseModel):
    execution_id: str
    status: str
    device_id: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    total_duration_sec: Optional[float] = None
    summary: ExecutionSummary
    steps: list[StepResultOut]
    crash_logs: list[str] = []
    device_info: DeviceInfoOut
