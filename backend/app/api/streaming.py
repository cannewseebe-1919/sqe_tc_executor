"""Screen streaming WebSocket endpoint."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.screen_streamer import screen_streamer

logger = logging.getLogger(__name__)
router = APIRouter(tags=["streaming"])


@router.websocket("/api/execute/{execution_id}/stream")
async def execution_stream(websocket: WebSocket, execution_id: str):
    """WebSocket endpoint for real-time device screen streaming during execution."""
    await websocket.accept()

    # Look up device_id from execution
    from app.core.database import async_session
    from app.models.execution import Execution

    async with async_session() as session:
        execution = await session.get(Execution, execution_id)
        if not execution:
            await websocket.send_json({"error": "Execution not found"})
            await websocket.close()
            return
        device_id = execution.device_id

    try:
        await screen_streamer.stream_to_websocket(device_id, websocket)
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for execution %s", execution_id)
    except Exception:
        logger.exception("Stream error for execution %s", execution_id)
    finally:
        await websocket.close()


@router.websocket("/api/devices/{device_id}/stream")
async def device_stream(websocket: WebSocket, device_id: str):
    """WebSocket endpoint for direct device screen streaming."""
    await websocket.accept()
    try:
        await screen_streamer.stream_to_websocket(device_id, websocket)
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for device %s", device_id)
    except Exception:
        logger.exception("Stream error for device %s", device_id)
    finally:
        await websocket.close()
