"""Execution API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.device import Device
from app.models.execution import Execution, ExecutionStep
from app.schemas.execution import (
    ExecuteRequestIn,
    ExecuteRequestOut,
    ExecutionStatusOut,
    ExecutionResultCallback,
    ExecutionSummary,
    StepResultOut,
    DeviceInfoOut,
)
from app.services.scheduler import scheduler
from app.services.test_runner import test_runner

router = APIRouter(prefix="/api/execute", tags=["execution"])


@router.post("", response_model=ExecuteRequestOut)
async def create_execution(req: ExecuteRequestIn, db: AsyncSession = Depends(get_db)):
    """Submit a test execution request."""
    # Lock device row to prevent race condition on concurrent requests
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

    # Enqueue — use SELECT FOR UPDATE to prevent two requests
    # from both seeing CONNECTED and both starting immediately
    if device.status == "CONNECTED":
        device.status = "TESTING"
        execution.status = "RUNNING"
        execution.queue_position = 0
        await db.commit()
        await test_runner.execute(execution.id)
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


@router.get("/{execution_id}/status", response_model=ExecutionStatusOut)
async def get_execution_status(execution_id: str, db: AsyncSession = Depends(get_db)):
    """Get current execution status."""
    execution = await db.get(Execution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Determine current step
    current_step = None
    progress = None
    if execution.status == "RUNNING":
        result = await db.execute(
            select(ExecutionStep)
            .where(ExecutionStep.execution_id == execution_id)
            .order_by(ExecutionStep.step_order.desc())
        )
        steps = result.scalars().all()
        total_steps = len(steps)
        if steps:
            current_step = steps[0].step_name
            completed = sum(1 for s in steps if s.status in ("PASSED", "FAILED"))
            progress = f"{completed}/{total_steps}"

    return ExecutionStatusOut(
        execution_id=execution.id,
        status=execution.status,
        current_step=current_step,
        progress=progress,
        started_at=execution.started_at,
    )


@router.get("/{execution_id}/result", response_model=ExecutionResultCallback)
async def get_execution_result(execution_id: str, db: AsyncSession = Depends(get_db)):
    """Get full execution result."""
    execution = await db.get(Execution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.status in ("QUEUED", "RUNNING"):
        raise HTTPException(status_code=400, detail="Execution not yet complete")

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
                name=s.step_name,
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
