"""Screen streaming — screenshot polling → WebSocket fan-out."""

import asyncio
import base64
import logging
from typing import Set

from fastapi import WebSocket

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

STREAM_INTERVAL = 0.1  # ~10 FPS
RUNNER_APP_FAIL_THRESHOLD = 3  # switch to ADB after this many consecutive Runner App failures


class DeviceStream:
    """One screenshot loop per device, shared by all WebSocket subscribers."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self._subscribers: Set[WebSocket] = set()
        self._task: asyncio.Task | None = None
        self._runner_fail_count = 0

    def add(self, ws: WebSocket):
        self._subscribers.add(ws)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    def remove(self, ws: WebSocket):
        self._subscribers.discard(ws)

    @property
    def active(self) -> bool:
        return bool(self._subscribers)

    async def _take_screenshot_runner(self) -> bytes:
        from app.services.runner_app_client import runner_app_client
        return await runner_app_client.take_screenshot(self.device_id)

    async def _take_screenshot_adb(self) -> bytes:
        import subprocess
        from app.core.config import get_settings
        cfg = get_settings()
        adb = cfg.ADB_PATH
        cmd = [adb, "-s", self.device_id, "exec-out", "screencap", "-p"]
        loop = asyncio.get_event_loop()

        def _run():
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            return result.stdout

        data = await loop.run_in_executor(None, _run)
        if not data:
            raise RuntimeError("screencap returned empty data")
        return data

    async def _take_screenshot(self) -> bytes:
        if self._runner_fail_count < RUNNER_APP_FAIL_THRESHOLD:
            try:
                result = await self._take_screenshot_runner()
                self._runner_fail_count = 0
                return result
            except Exception:
                self._runner_fail_count += 1
                logger.debug("Runner App unavailable for %s (%d/%d), using ADB",
                             self.device_id, self._runner_fail_count, RUNNER_APP_FAIL_THRESHOLD)
        return await self._take_screenshot_adb()

    async def _broadcast(self, payload: dict):
        dead = set()
        for ws in list(self._subscribers):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        self._subscribers -= dead

    async def _loop(self):
        logger.info("Stream loop started for %s", self.device_id)
        consecutive_errors = 0
        while self.active:
            try:
                screenshot_bytes = await self._take_screenshot()
                frame_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
                await self._broadcast({"frame": frame_b64})
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                logger.debug("Stream error for %s (%d): %s", self.device_id, consecutive_errors, e)
                await self._broadcast({"error": str(e)})
                if consecutive_errors >= 10:
                    logger.warning("Stream loop stopping for %s after 10 errors", self.device_id)
                    break
            await asyncio.sleep(STREAM_INTERVAL)
        logger.info("Stream loop stopped for %s", self.device_id)


class ScreenStreamer:
    def __init__(self):
        self._streams: dict[str, DeviceStream] = {}

    def _get_stream(self, device_id: str) -> DeviceStream:
        if device_id not in self._streams:
            self._streams[device_id] = DeviceStream(device_id)
        return self._streams[device_id]

    async def stream_to_websocket(self, device_id: str, ws: WebSocket):
        stream = self._get_stream(device_id)
        stream.add(ws)
        try:
            # Keep the WebSocket alive until client disconnects
            while True:
                try:
                    await asyncio.wait_for(ws.receive_text(), timeout=30)
                except asyncio.TimeoutError:
                    pass  # keepalive
        except Exception:
            pass
        finally:
            stream.remove(ws)

    async def stop_all(self):
        pass


screen_streamer = ScreenStreamer()
