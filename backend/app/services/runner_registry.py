"""Registry for active Runner App WebSocket connections."""

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)

COMMAND_TIMEOUT = 15  # seconds


class RunnerRegistry:
    """Maps android_id → active Runner App WebSocket, handles request/response."""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._pending: dict[str, asyncio.Future] = {}

    async def register(self, device_id: str, ws: WebSocket):
        self._connections[device_id] = ws
        logger.info("Runner connected: %s", device_id)

    async def unregister(self, device_id: str):
        self._connections.pop(device_id, None)
        logger.info("Runner disconnected: %s", device_id)

    def is_connected(self, device_id: str) -> bool:
        return device_id in self._connections

    async def handle_message(self, device_id: Optional[str], msg: dict):
        request_id = msg.get("request_id", "")
        future = self._pending.pop(request_id, None)
        if future and not future.done():
            future.set_result(msg)
        else:
            logger.debug("Unmatched message from %s: type=%s", device_id, msg.get("type"))

    async def send_command(self, device_id: str, cmd_type: str, **params) -> dict:
        ws = self._connections.get(device_id)
        if ws is None:
            raise RuntimeError(f"Runner App not connected for device {device_id}")

        request_id = str(uuid.uuid4())
        cmd = {"type": cmd_type, "request_id": request_id, **params}

        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[request_id] = future

        try:
            await ws.send_text(json.dumps(cmd))
            result = await asyncio.wait_for(future, timeout=COMMAND_TIMEOUT)
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            raise TimeoutError(f"Runner App did not respond within {COMMAND_TIMEOUT}s "
                               f"(device={device_id}, cmd={cmd_type})")
        except Exception:
            self._pending.pop(request_id, None)
            raise

        if not result.get("success", True):
            raise RuntimeError(result.get("error", "Runner App returned failure"))
        return result


runner_registry = RunnerRegistry()
