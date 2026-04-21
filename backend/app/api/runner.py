"""WebSocket endpoint for Runner App connections."""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.runner_registry import runner_registry

logger = logging.getLogger(__name__)
router = APIRouter(tags=["runner"])


@router.websocket("/ws/runner")
async def runner_websocket(websocket: WebSocket):
    """Runner App connects here and receives commands, sends back results."""
    await websocket.accept()
    device_id = None
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from Runner App: %s", raw[:200])
                continue

            if msg.get("type") == "device_info":
                device_id = msg.get("device_id")
                if not device_id:
                    logger.warning("Runner App sent device_info without device_id")
                    continue
                await runner_registry.register(device_id, websocket)
            else:
                await runner_registry.handle_message(device_id, msg)

    except WebSocketDisconnect:
        logger.info("Runner App disconnected: %s", device_id)
    except Exception:
        logger.exception("Runner WebSocket error for device %s", device_id)
    finally:
        if device_id:
            await runner_registry.unregister(device_id)
