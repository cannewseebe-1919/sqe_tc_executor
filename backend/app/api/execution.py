"""Execution API endpoints."""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.device import Device
from app.models.execution import Execution, ExecutionStep
from app.schemas.execution import (
    ExecuteRequestIn,
    ExecuteRequestOut,
    ExecutionStatusOut,
    ExecutionSummaryOut,
    ExecutionListOut,
    ExecutionResultCallback,
    ExecutionSummary,
    StepResultOut,
    DeviceInfoOut,
    DeviceQueueOut,
    QueueItemOut,
    QueueListOut,
)
from app.services.scheduler import scheduler
from app.services.test_runner import test_runner

router = APIRouter(tags=["execution"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _build_status_out(
    execution: Execution,
    db: AsyncSession,
    include_steps: bool = True,
) -> ExecutionStatusOut:
    """Build full ExecutionStatusOut from an Execution ORM object."""
    device = await db.get(Device, execution.device_id)
    device_name = device.name if device else None

    steps_out: list[StepResultOut] = []
    current_step = None
    progress = None

    if include_steps and execution.status in ("RUNNING", "COMPLETED", "FAILED", "ABORTED"):
        result = await db.execute(
            select(ExecutionStep)
            .where(ExecutionStep.execution_id == execution.id)
            .order_by(ExecutionStep.step_order)
        )
        steps = result.scalars().all()
        total = len(steps)
        if steps:
            running = [s for s in steps if s.status not in ("PASSED", "FAILED")]
            current_step = running[0].step_name if running else steps[-1].step_name
            completed = sum(1 for s in steps if s.status in ("PASSED", "FAILED"))
            progress = f"{completed}/{total}"
        steps_out = [
            StepResultOut(
                execution_id=execution.id,
                step_name=s.step_name,
                step_order=s.step_order,
                status=s.status,
                duration_sec=s.duration_sec,
                screenshot_url=s.screenshot_path,
                log=s.log,
                error_type=s.error_type,
            )
            for s in steps
        ]

    passed = sum(1 for s in steps_out if s.status == "PASSED")
    failed = sum(1 for s in steps_out if s.status == "FAILED")
    summary = ExecutionSummary(
        total_steps=len(steps_out),
        passed=passed,
        failed=failed,
        aborted=execution.status == "ABORTED",
    ) if steps_out or execution.status in ("COMPLETED", "FAILED", "ABORTED") else None

    device_info = DeviceInfoOut(
        model=device.model if device else "",
        android_version=device.android_version if device else "",
        resolution=device.resolution if device else "",
    ) if device else None

    return ExecutionStatusOut(
        id=execution.id,
        execution_id=execution.id,
        device_id=execution.device_id,
        device_name=device_name,
        requested_by=execution.requested_by,
        status=execution.status,
        queue_position=execution.queue_position,
        current_step=current_step,
        progress=progress,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        total_duration_sec=execution.total_duration_sec,
        steps=steps_out,
        summary=summary,
        device_info=device_info,
    )


# ---------------------------------------------------------------------------
# POST /api/execute — submit test
# ---------------------------------------------------------------------------

@router.post("/api/execute", response_model=ExecuteRequestOut)
async def create_execution(req: ExecuteRequestIn, db: AsyncSession = Depends(get_db)):
    """Submit a test execution request."""
    result = await db.execute(
        select(Device).where(Device.id == req.device_id).with_for_update()
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if device.status == "OFFLINE":
        raise HTTPException(status_code=400, detail="Device is offline")
    if device.status == "ERROR":
        raise HTTPException(status_code=400, detail="Device is in error state")

    execution = Execution(
        test_code=req.test_code,
        device_id=req.device_id,
        requested_by=req.requested_by,
        callback_url=req.callback_url,
        status="QUEUED",
    )
    db.add(execution)
    await db.flush()

    if device.status == "CONNECTED":
        device.status = "TESTING"
        execution.status = "RUNNING"
        execution.queue_position = 0
        await db.commit()
        asyncio.create_task(test_runner.execute(execution.id))
        return ExecuteRequestOut(
            execution_id=execution.id, status="RUNNING", queue_position=0
        )
    else:
        pos = await scheduler.enqueue(device.id, execution.id)
        execution.queue_position = pos
        execution.status = "QUEUED"
        await db.commit()
        return ExecuteRequestOut(
            execution_id=execution.id, status="QUEUED", queue_position=pos
        )


# ---------------------------------------------------------------------------
# GET /api/execute/{id}/status — full execution info (any status)
# ---------------------------------------------------------------------------

@router.get("/api/execute/{execution_id}/status", response_model=ExecutionStatusOut)
async def get_execution_status(execution_id: str, db: AsyncSession = Depends(get_db)):
    """Get current execution status and available step results."""
    execution = await db.get(Execution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return await _build_status_out(execution, db)


# ---------------------------------------------------------------------------
# GET /api/execute/{id}/result — alias to status (no more 400 on QUEUED/RUNNING)
# ---------------------------------------------------------------------------

@router.get("/api/execute/{execution_id}/result", response_model=ExecutionResultCallback)
async def get_execution_result(execution_id: str, db: AsyncSession = Depends(get_db)):
    """Get full execution result. Returns current state even if still running."""
    execution = await db.get(Execution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    device = await db.get(Device, execution.device_id)
    result = await db.execute(
        select(ExecutionStep)
        .where(ExecutionStep.execution_id == execution_id)
        .order_by(ExecutionStep.step_order)
    )
    steps = result.scalars().all()
    passed = sum(1 for s in steps if s.status == "PASSED")
    failed = sum(1 for s in steps if s.status == "FAILED")

    return ExecutionResultCallback(
        execution_id=execution.id,
        status=execution.status,
        device_id=execution.device_id,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        total_duration_sec=execution.total_duration_sec,
        summary=ExecutionSummary(
            total_steps=len(steps),
            passed=passed,
            failed=failed,
            aborted=execution.status == "ABORTED",
        ),
        steps=[
            StepResultOut(
                execution_id=execution.id,
                step_name=s.step_name,
                step_order=s.step_order,
                status=s.status,
                duration_sec=s.duration_sec,
                screenshot_url=s.screenshot_path,
                log=s.log,
                error_type=s.error_type,
            )
            for s in steps
        ],
        crash_logs=[],
        device_info=DeviceInfoOut(
            model=device.model if device else "",
            android_version=device.android_version if device else "",
            resolution=device.resolution if device else "",
        ),
    )


# ---------------------------------------------------------------------------
# GET /api/executions — paginated list
# ---------------------------------------------------------------------------

@router.get("/api/executions", response_model=ExecutionListOut)
async def list_executions(
    device_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List executions with optional filters."""
    q = select(Execution).order_by(Execution.created_at.desc())
    if device_id:
        q = q.where(Execution.device_id == device_id)
    if status:
        q = q.where(Execution.status == status)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(q.offset(offset).limit(limit))
    executions = result.scalars().all()

    # Gather device names in one query
    device_ids = list({e.device_id for e in executions})
    devices_result = await db.execute(select(Device).where(Device.id.in_(device_ids)))
    devices = {d.id: d for d in devices_result.scalars().all()}

    return ExecutionListOut(
        executions=[
            ExecutionSummaryOut(
                id=e.id,
                device_id=e.device_id,
                device_name=devices.get(e.device_id, None) and devices[e.device_id].name,
                requested_by=e.requested_by,
                status=e.status,
                queue_position=e.queue_position,
                started_at=e.started_at,
                finished_at=e.finished_at,
                total_duration_sec=e.total_duration_sec,
            )
            for e in executions
        ],
        total=total,
    )


# ---------------------------------------------------------------------------
# GET /api/queues — queue status per device
# ---------------------------------------------------------------------------

@router.get("/api/queues", response_model=QueueListOut)
async def get_queues(db: AsyncSession = Depends(get_db)):
    """Return queue status for all devices."""
    devices_result = await db.execute(select(Device))
    devices = devices_result.scalars().all()

    queues: list[DeviceQueueOut] = []
    for device in devices:
        # Current running execution
        running_result = await db.execute(
            select(Execution)
            .where(Execution.device_id == device.id, Execution.status == "RUNNING")
            .limit(1)
        )
        running = running_result.scalar_one_or_none()
        current_execution = None
        if running:
            current_execution = ExecutionSummaryOut(
                id=running.id,
                device_id=running.device_id,
                device_name=device.name,
                requested_by=running.requested_by,
                status=running.status,
                queue_position=running.queue_position,
                started_at=running.started_at,
                finished_at=running.finished_at,
                total_duration_sec=running.total_duration_sec,
            )

        # Queued executions (from Redis, ordered)
        queued_ids = await scheduler.get_queue(device.id)
        queue_items: list[QueueItemOut] = []
        if queued_ids:
            queued_result = await db.execute(
                select(Execution).where(Execution.id.in_(queued_ids))
            )
            queued_map = {e.id: e for e in queued_result.scalars().all()}
            for pos, eid in enumerate(queued_ids):
                e = queued_map.get(eid)
                if e:
                    queue_items.append(QueueItemOut(
                        execution_id=e.id,
                        requested_by=e.requested_by,
                        queued_at=e.created_at,
                        position=pos,
                    ))

        queues.append(DeviceQueueOut(
            device_id=device.id,
            device_name=device.name,
            current_execution=current_execution,
            queue=queue_items,
        ))

    return QueueListOut(queues=queues)
