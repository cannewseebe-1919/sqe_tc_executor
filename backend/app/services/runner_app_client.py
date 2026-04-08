"""Communication client for the Runner App installed on devices."""

import logging
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RunnerAppClient:
    """HTTP client that talks to the Runner App on each device.

    The Runner App exposes an HTTP server on the device.
    We use adb forward to access it from the host.
    """

    def __init__(self):
        self._forwarded_ports: dict[str, int] = {}
        self._next_port = 18080

    async def _ensure_forward(self, device_id: str) -> int:
        """Set up adb port forwarding if not already done."""
        if device_id in self._forwarded_ports:
            return self._forwarded_ports[device_id]

        from app.services.adb_manager import adb_manager

        local_port = self._next_port
        self._next_port += 1
        await adb_manager.run(
            "forward", f"tcp:{local_port}", f"tcp:{settings.RUNNER_APP_PORT}",
            device_id=device_id,
        )
        self._forwarded_ports[device_id] = local_port
        logger.info("Forwarded %s -> localhost:%d", device_id, local_port)
        return local_port

    def _base_url(self, port: int) -> str:
        return f"http://127.0.0.1:{port}"

    async def get_ui_tree(self, device_id: str) -> dict:
        port = await self._ensure_forward(device_id)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self._base_url(port)}/ui-tree")
            resp.raise_for_status()
            return resp.json()

    async def find_element(
        self,
        device_id: str,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        class_name: Optional[str] = None,
    ) -> Optional[dict]:
        port = await self._ensure_forward(device_id)
        params = {}
        if text:
            params["text"] = text
        if resource_id:
            params["resource_id"] = resource_id
        if class_name:
            params["class_name"] = class_name
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self._base_url(port)}/find-element", params=params)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def take_screenshot(self, device_id: str) -> bytes:
        port = await self._ensure_forward(device_id)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self._base_url(port)}/screenshot")
            resp.raise_for_status()
            return resp.content

    async def remove_forward(self, device_id: str):
        if device_id in self._forwarded_ports:
            from app.services.adb_manager import adb_manager
            port = self._forwarded_ports.pop(device_id)
            await adb_manager.run("forward", "--remove", f"tcp:{port}", device_id=device_id)


runner_app_client = RunnerAppClient()
