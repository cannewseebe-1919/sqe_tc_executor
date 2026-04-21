"""Crash / Kernel Panic / ANR detection via logcat monitoring."""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Optional, Awaitable

from app.services.adb_manager import adb_manager

logger = logging.getLogger(__name__)

# Detection patterns
CRASH_PATTERN = re.compile(r"FATAL EXCEPTION", re.IGNORECASE)
ANR_PATTERN = re.compile(r"ANR in", re.IGNORECASE)
SYSTEM_UI_CRASH = re.compile(r"Process com\.android\.systemui has died", re.IGNORECASE)


@dataclass
class CrashEvent:
    device_id: str
    event_type: str  # APP_CRASH | ANR | KERNEL_PANIC | SYSTEM_UI_CRASH
    log: str = ""
    timestamp: str = ""


CrashCallback = Callable[[CrashEvent], Awaitable[None]]


class CrashDetector:
    """Monitors logcat and ADB connectivity for a single device."""

    def __init__(self, device_id: str, on_crash: Optional[CrashCallback] = None):
        self.device_id = device_id
        self._on_crash = on_crash
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._crash_logs: list[str] = []

    @property
    def crash_logs(self) -> list[str]:
        return list(self._crash_logs)

    async def start(self):
        self._running = True
        self._tasks = [
            asyncio.create_task(self._logcat_monitor()),
            asyncio.create_task(self._adb_connection_monitor()),
        ]
        logger.info("CrashDetector started for %s", self.device_id)

    async def stop(self):
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _logcat_monitor(self):
        """Stream logcat and match crash/ANR patterns."""
        try:
            from app.services.adb_manager import adb_manager
            proc = await asyncio.create_subprocess_exec(
                adb_manager.adb_path, "-s", self.device_id, "logcat", "-v", "time", "-T", "1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            while self._running and proc.stdout:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace")
                await self._check_line(line)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("logcat monitor error for %s", self.device_id)
        finally:
            try:
                proc.kill()
            except Exception:
                pass

    async def _check_line(self, line: str):
        event = None
        if CRASH_PATTERN.search(line):
            event = CrashEvent(self.device_id, "APP_CRASH", log=line)
        elif ANR_PATTERN.search(line):
            event = CrashEvent(self.device_id, "ANR", log=line)
        elif SYSTEM_UI_CRASH.search(line):
            event = CrashEvent(self.device_id, "SYSTEM_UI_CRASH", log=line)

        if event:
            self._crash_logs.append(f"[{event.event_type}] {line.strip()}")
            logger.warning("Crash detected on %s: %s", self.device_id, event.event_type)
            if self._on_crash:
                await self._on_crash(event)

    async def _adb_connection_monitor(self):
        """Periodically check if device is still reachable."""
        try:
            while self._running:
                devices = await adb_manager.list_devices()
                serials = {d["serial"] for d in devices if d["status"] == "device"}
                if self.device_id not in serials:
                    logger.warning("Device %s disconnected — possible kernel panic", self.device_id)
                    event = CrashEvent(self.device_id, "KERNEL_PANIC", log="ADB connection lost")
                    self._crash_logs.append("[KERNEL_PANIC] ADB connection lost")
                    if self._on_crash:
                        await self._on_crash(event)
                    break
                await asyncio.sleep(3)
        except asyncio.CancelledError:
            pass
