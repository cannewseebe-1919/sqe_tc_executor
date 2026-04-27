"""WebSocket endpoint for Runner App connections + HTTP proxy for TC scripts."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.services.runner_app_client import runner_app_client
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


# ---------------------------------------------------------------------------
# HTTP proxy endpoints — called by TC scripts via device.py SDK
# These forward requests to the Runner App over its active WebSocket connection.
# ---------------------------------------------------------------------------

@router.get("/runner/{device_id}/status")
async def runner_status(device_id: str):
    """Check if Runner App is connected for this device."""
    connected = runner_registry.is_connected(device_id)
    return {"device_id": device_id, "connected": connected}


@router.get("/runner/{device_id}/ui-tree")
async def get_ui_tree(device_id: str):
    """Return full UI tree from the Runner App."""
    if not runner_registry.is_connected(device_id):
        raise HTTPException(status_code=503, detail="Runner App not connected")
    try:
        tree = await runner_app_client.get_ui_tree(device_id)
        return tree
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/runner/{device_id}/find-element")
async def find_element(
    device_id: str,
    text: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None),
):
    """Find UI element by text / resource_id / class_name."""
    if not runner_registry.is_connected(device_id):
        raise HTTPException(status_code=503, detail="Runner App not connected")
    try:
        elem = await runner_app_client.find_element(
            device_id, text=text, resource_id=resource_id, class_name=class_name
        )
        if elem is None:
            raise HTTPException(status_code=404, detail="Element not found")
        return elem
    except HTTPException:
        raise
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/runner/{device_id}/screenshot")
async def take_screenshot(device_id: str):
    """Take a screenshot and return as base64 PNG."""
    if not runner_registry.is_connected(device_id):
        raise HTTPException(status_code=503, detail="Runner App not connected")
    try:
        png_bytes = await runner_app_client.take_screenshot(device_id)
        import base64
        return {"format": "png", "encoding": "base64", "data": base64.b64encode(png_bytes).decode()}
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/runner/{device_id}/ping")
async def ping_runner(device_id: str):
    """Ping the Runner App to check accessibility/screen-capture status."""
    if not runner_registry.is_connected(device_id):
        raise HTTPException(status_code=503, detail="Runner App not connected")
    try:
        result = await runner_registry.send_command(device_id, "ping")
        return result
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
