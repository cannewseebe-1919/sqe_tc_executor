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
    """Maps android_id → active Runner App WebSocket, handles request/response.

    Also maintains a secondary adb_serial → android_id mapping so that
    test_runner (which knows only the adb serial) can find the right connection.
    """

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._pending: dict[str, asyncio.Future] = {}
        # adb_serial → android_id
        self._serial_to_android_id: dict[str, str] = {}
        # android_id → model (for model-based serial matching)
        self._android_id_to_model: dict[str, str] = {}

    async def register(self, android_id: str, ws: WebSocket,
                       adb_serial: Optional[str] = None, model: Optional[str] = None):
        self._connections[android_id] = ws
        if model:
            self._android_id_to_model[android_id] = model
        if adb_serial:
            self._serial_to_android_id[adb_serial] = android_id
        logger.info("Runner connected: android_id=%s adb_serial=%s model=%s",
                    android_id, adb_serial, model)

    def find_android_id_by_model(self, model: str) -> Optional[str]:
        """Return android_id of a connected Runner App whose model matches."""
        for android_id, m in self._android_id_to_model.items():
            if android_id in self._connections and m == model:
                return android_id
        return None

    async def unregister(self, android_id: str):
        self._connections.pop(android_id, None)
        # Remove reverse mapping entries pointing to this android_id
        stale = [s for s, a in self._serial_to_android_id.items() if a == android_id]
        for s in stale:
            del self._serial_to_android_id[s]
        logger.info("Runner disconnected: %s", android_id)

    def map_serial(self, adb_serial: str, android_id: str):
        """Explicitly set adb_serial → android_id mapping (called by device_monitor)."""
        self._serial_to_android_id[adb_serial] = android_id
        logger.info("Runner serial mapped: %s → %s", adb_serial, android_id)

    def resolve(self, device_id: str) -> Optional[str]:
        """Return the android_id to use for WebSocket lookup.

        Accepts either an android_id (returned as-is if connected) or
        an adb_serial (looked up via the mapping table).
        """
        if device_id in self._connections:
            return device_id
        return self._serial_to_android_id.get(device_id)

    def is_connected(self, device_id: str) -> bool:
        return self.resolve(device_id) is not None

    async def handle_message(self, device_id: Optional[str], msg: dict):
        request_id = msg.get("request_id", "")
        future = self._pending.pop(request_id, None)
        if future and not future.done():
            future.set_result(msg)
        else:
            logger.debug("Unmatched message from %s: type=%s", device_id, msg.get("type"))

    async def send_command(self, device_id: str, cmd_type: str, **params) -> dict:
        android_id = self.resolve(device_id)
        ws = self._connections.get(android_id) if android_id else None
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
