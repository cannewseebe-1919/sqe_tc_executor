"""Screen streaming — scrcpy subprocess → WebSocket relay."""

import asyncio
import logging
from typing import Optional

from fastapi import WebSocket

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ScreenStreamer:
    """Manages scrcpy processes and streams frames to WebSocket clients."""

    def __init__(self):
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    async def start_scrcpy(self, device_id: str) -> asyncio.subprocess.Process:
        if device_id in self._processes:
            return self._processes[device_id]

        proc = await asyncio.create_subprocess_exec(
            settings.SCRCPY_PATH,
            "-s", device_id,
            "--no-display",
            "--record", "-",
            "--record-format", "mp4",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._processes[device_id] = proc
        logger.info("scrcpy started for %s (pid=%d)", device_id, proc.pid)
        return proc

    async def stop_scrcpy(self, device_id: str):
        proc = self._processes.pop(device_id, None)
        if proc:
            proc.kill()
            await proc.wait()
            logger.info("scrcpy stopped for %s", device_id)

    async def stream_to_websocket(self, device_id: str, ws: WebSocket):
        """Stream scrcpy output frames to a WebSocket connection.

        For MVP we use a simple approach: periodically capture screenshots
        via Runner App and send as binary frames.
        """
        from app.services.runner_app_client import runner_app_client

        try:
            while True:
                try:
                    screenshot_bytes = await runner_app_client.take_screenshot(device_id)
                    await ws.send_bytes(screenshot_bytes)
                except Exception as e:
                    logger.debug("Screenshot stream error: %s", e)
                    await ws.send_json({"error": str(e)})
                await asyncio.sleep(0.1)  # ~10 FPS
        except Exception:
            logger.debug("WebSocket stream ended for %s", device_id)

    async def stop_all(self):
        for device_id in list(self._processes.keys()):
            await self.stop_scrcpy(device_id)


screen_streamer = ScreenStreamer()
