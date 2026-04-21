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


class StepResultOut(BaseModel):
    execution_id: str = ""
    step_name: str
    step_order: int = 0
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


class ExecutionStatusOut(BaseModel):
    """Full execution info returned by GET /api/execute/{id}/status."""
    id: str
    execution_id: str           # 하위 호환
    test_case_id: str = ""      # 프론트엔드 호환용
    device_id: str
    device_name: Optional[str] = None
    requested_by: str = ""
    status: str
    queue_position: int = 0
    current_step: Optional[str] = None
    progress: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    total_duration_sec: Optional[float] = None
    steps: list[StepResultOut] = []
    crash_logs: list[str] = []
    summary: Optional[ExecutionSummary] = None
    device_info: Optional[DeviceInfoOut] = None


class ExecutionSummaryOut(BaseModel):
    """Lightweight execution info for list endpoints."""
    id: str
    test_case_id: str = ""
    device_id: str
    device_name: Optional[str] = None
    requested_by: str = ""
    status: str
    queue_position: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    total_duration_sec: Optional[float] = None
    current_step: Optional[str] = None
    progress: Optional[str] = None


class ExecutionListOut(BaseModel):
    executions: list[ExecutionSummaryOut]
    total: int


class QueueItemOut(BaseModel):
    execution_id: str
    test_case_id: str = ""
    requested_by: str = ""
    queued_at: Optional[datetime] = None
    position: int


class DeviceQueueOut(BaseModel):
    device_id: str
    device_name: str
    current_execution: Optional[ExecutionSummaryOut] = None
    queue: list[QueueItemOut]


class QueueListOut(BaseModel):
    queues: list[DeviceQueueOut]


class ExecutionResultCallback(BaseModel):
    """Full result payload — used for callback POST and GET /result."""
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
