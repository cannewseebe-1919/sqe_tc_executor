"""Communication client for the Runner App installed on devices."""

import base64
import logging
from typing import Optional

from app.services.runner_registry import runner_registry

logger = logging.getLogger(__name__)


class RunnerAppClient:
    """Sends commands to the Runner App via its active WebSocket connection.

    The Runner App connects to /ws/runner and is registered in runner_registry.
    device_id here is the android_id sent by the Runner App on connect.
    """

    async def get_ui_tree(self, device_id: str) -> dict:
        result = await runner_registry.send_command(device_id, "get_ui_tree")
        return result.get("data", {})

    async def find_element(
        self,
        device_id: str,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        class_name: Optional[str] = None,
    ) -> Optional[dict]:
        params = {}
        if text:
            params["text"] = text
        if resource_id:
            params["resource_id"] = resource_id
        if class_name:
            params["class_name"] = class_name

        result = await runner_registry.send_command(device_id, "find_element", **params)
        elements = result.get("elements", [])
        return elements[0] if elements else None

    async def take_screenshot(self, device_id: str) -> bytes:
        result = await runner_registry.send_command(device_id, "screenshot")
        return base64.b64decode(result["data"])


runner_app_client = RunnerAppClient()
