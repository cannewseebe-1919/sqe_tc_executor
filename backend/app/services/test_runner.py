"""Test Runner Engine — executes TC Python scripts in subprocess.

SECURITY NOTE: TC scripts run as subprocess with restricted imports.
In production, consider running in Docker container or seccomp sandbox.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session
from app.models.device import Device
from app.models.execution import Execution, ExecutionStep
from app.schemas.execution import (
    ExecutionResultCallback,
    ExecutionSummary,
    StepResultOut,
    DeviceInfoOut,
)
from app.services.crash_detector import CrashDetector, CrashEvent
from app.services.scheduler import scheduler

logger = logging.getLogger(__name__)
settings = get_settings()


class TestRunner:
    """Runs TC .py scripts and collects results."""

    def __init__(self):
        self._active_runs: dict[str, asyncio.Task] = {}

    async def execute(self, execution_id: str):
        """Start execution in background task."""
        task = asyncio.create_task(self._run(execution_id))
        self._active_runs[execution_id] = task

    async def _run(self, execution_id: str):
        crash_detector: Optional[CrashDetector] = None
        abort_reason: Optional[str] = None

        async with async_session() as session:
            execution = await session.get(Execution, execution_id)
            if not execution:
                logger.error("Execution %s not found", execution_id)
                return

            device = await session.get(Device, execution.device_id)
            if not device:
                logger.error("Device %s not found", execution.device_id)
                return

            # Update state
            execution.status = "RUNNING"
            execution.started_at = datetime.now(timezone.utc)
            device.status = "TESTING"
            await session.commit()

            # Start crash detector
            crash_event: Optional[CrashEvent] = None

            async def on_crash(event: CrashEvent):
                nonlocal crash_event, abort_reason
                crash_event = event
                abort_reason = event.event_type

            crash_detector = CrashDetector(device.id, on_crash=on_crash)
            await crash_detector.start()

            # Validate TC code — block dangerous imports/calls
            tc_code = execution.test_code
            dangerous_patterns = [
                r'\bos\.system\s*\(', r'\bsubprocess\b', r'\b__import__\b',
                r'\beval\s*\(', r'\bexec\s*\(', r'\bcompile\s*\(',
                r'\bopen\s*\([^)]*["\']\/etc', r'\bimport\s+ctypes\b',
                r'\bimport\s+socket\b', r'\bfrom\s+os\b',
            ]
            for pattern in dangerous_patterns:
                if re.search(pattern, tc_code):
                    execution.status = "FAILED"
                    execution.finished_at = datetime.now(timezone.utc)
                    device.status = "CONNECTED"
                    await session.commit()
                    logger.warning(
                        "TC code rejected (dangerous pattern: %s) for execution %s",
                        pattern, execution_id,
                    )
                    if execution.callback_url:
                        await self._send_callback(
                            execution, device, [], 0, 0, True,
                            "SECURITY_VIOLATION", [],
                        )
                    return

            # Write TC code to temp file
            tc_dir = tempfile.mkdtemp(prefix="tc_exec_")
            tc_file = os.path.join(tc_dir, "test_case.py")
            with open(tc_file, "w", encoding="utf-8") as f:
                f.write(tc_code)

            # Build env for subprocess
            env = os.environ.copy()
            env["TC_DEVICE_ID"] = device.id
            env["TC_EXECUTION_ID"] = execution_id
            env["TC_BACKEND_PORT"] = str(settings.BACKEND_EXTERNAL_PORT)
            _base = Path(__file__).resolve().parent.parent.parent  # backend/
            screenshot_dir = str(_base / settings.SCREENSHOT_DIR / execution_id)
            env["TC_SCREENSHOT_DIR"] = screenshot_dir
            env["TC_ADB_PATH"] = settings.ADB_PATH
            os.makedirs(screenshot_dir, exist_ok=True)

            # Execute TC in subprocess
            # backend/ 를 PYTHONPATH에 추가해야 app.sdk 및 tc_executor_sdk 모두 import 가능
            backend_path = str(Path(__file__).resolve().parent.parent.parent)
            env["PYTHONPATH"] = backend_path + os.pathsep + env.get("PYTHONPATH", "")
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"

            try:
                proc = await asyncio.create_subprocess_exec(
                    "python", "-X", "utf8", "-u", tc_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    cwd=tc_dir,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=600,  # 10 min max
                )
                output = stdout.decode("utf-8", errors="replace")
                err_output = stderr.decode("utf-8", errors="replace")
                exit_code = proc.returncode
                logger.info(
                    "TC subprocess finished (exit=%d) for execution %s",
                    exit_code, execution_id,
                )
                if err_output.strip():
                    logger.warning(
                        "TC stderr for execution %s:\n%s", execution_id, err_output
                    )
                if exit_code != 0 and not abort_reason:
                    abort_reason = "EXECUTION_ERROR"
            except asyncio.TimeoutError:
                abort_reason = "EXECUTION_TIMEOUT"
                output = ""
                err_output = "Execution timed out after 600 seconds"
                try:
                    proc.kill()
                except Exception:
                    pass
            except Exception as e:
                abort_reason = "EXECUTION_ERROR"
                output = ""
                err_output = str(e)
                logger.error("TC subprocess launch failed for %s: %s", execution_id, e)

            if abort_reason:
                logger.warning(
                    "Execution %s aborted: reason=%s err=%s",
                    execution_id, abort_reason, err_output[:500] if err_output else "",
                )

            # Stop crash detector
            await crash_detector.stop()

            # Parse step results from stdout JSON lines
            steps_data = []
            for line in output.splitlines():
                line = line.strip()
                if line.startswith('{"step_'):
                    try:
                        steps_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
                elif line.startswith("[STEP_RESULT]"):
                    try:
                        steps_data.append(json.loads(line[len("[STEP_RESULT]"):]))
                    except json.JSONDecodeError:
                        pass

            # Save step results to DB
            passed = 0
            failed = 0
            current_step_name = None
            for i, sd in enumerate(steps_data):
                step = ExecutionStep(
                    execution_id=execution_id,
                    step_name=sd.get("name", f"step_{i+1}"),
                    step_order=i + 1,
                    status=sd.get("status", "PASSED"),
                    duration_sec=sd.get("duration_sec", 0),
                    screenshot_path=sd.get("screenshot_path"),
                    log=sd.get("log", ""),
                    error_type=sd.get("error_type"),
                )
                session.add(step)
                if step.status == "PASSED":
                    passed += 1
                else:
                    failed += 1
                current_step_name = step.step_name

            # Finalize execution
            execution.finished_at = datetime.now(timezone.utc)
            if execution.started_at:
                execution.total_duration_sec = (
                    execution.finished_at - execution.started_at
                ).total_seconds()

            aborted = abort_reason is not None
            if aborted:
                execution.status = "ABORTED"
            elif failed > 0:
                execution.status = "FAILED"
            else:
                execution.status = "COMPLETED"

            device.status = "CONNECTED"
            await session.commit()

            # Send callback
            if execution.callback_url:
                await self._send_callback(
                    execution, device, steps_data, passed, failed,
                    aborted, abort_reason, crash_detector.crash_logs,
                )

            # Cleanup temp directory
            try:
                shutil.rmtree(tc_dir, ignore_errors=True)
            except Exception:
                pass

            # Check queue for next execution
            self._active_runs.pop(execution_id, None)
            await self._process_next(device.id)

    def _to_screenshot_url(self, local_path: Optional[str]) -> Optional[str]:
        """로컬 파일 경로를 HTTP URL로 변환."""
        if not local_path:
            return None
        try:
            screenshot_base = Path(__file__).resolve().parent.parent.parent / settings.SCREENSHOT_DIR
            rel = Path(local_path).relative_to(screenshot_base)
            return f"/screenshots/{rel.as_posix()}"
        except ValueError:
            return None

    async def _send_callback(
        self, execution: Execution, device: Device,
        steps_data: list, passed: int, failed: int,
        aborted: bool, abort_reason: Optional[str],
        crash_logs: list[str],
    ):
        steps = [
            StepResultOut(
                execution_id=execution.id,
                step_name=sd.get("name", ""),
                step_order=sd.get("step_order", i + 1),
                status=sd.get("status", "PASSED"),
                duration_sec=sd.get("duration_sec", 0),
                screenshot_url=self._to_screenshot_url(sd.get("screenshot_path")),
                log=sd.get("log", ""),
                error_type=sd.get("error_type"),
            )
            for i, sd in enumerate(steps_data)
        ]
        result = ExecutionResultCallback(
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
                aborted=aborted,
                abort_reason=abort_reason,
            ),
            steps=steps,
            crash_logs=crash_logs,
            device_info=DeviceInfoOut(
                model=device.model,
                android_version=device.android_version,
                resolution=device.resolution,
            ),
        )
        delays = [1, 3]
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        execution.callback_url,
                        json=result.model_dump(mode="json"),
                    )
                    resp.raise_for_status()
                    logger.info("Callback sent to %s (status=%d)", execution.callback_url, resp.status_code)
                    return
            except Exception as e:
                if attempt < 2:
                    logger.warning("Callback attempt %d failed (%s), retrying in %ds…", attempt + 1, e, delays[attempt])
                    await asyncio.sleep(delays[attempt])
                else:
                    logger.exception("Callback failed after 3 attempts: %s", execution.callback_url)

    async def _process_next(self, device_id: str):
        """Dequeue and run next execution for a device."""
        next_id = await scheduler.dequeue(device_id)
        if next_id:
            logger.info("Processing next execution %s for device %s", next_id, device_id)
            await self.execute(next_id)


test_runner = TestRunner()
