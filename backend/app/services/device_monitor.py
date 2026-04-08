"""Device auto-detection via adb devices polling."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session
from app.models.device import Device
from app.services.adb_manager import adb_manager

logger = logging.getLogger(__name__)
settings = get_settings()


class DeviceMonitor:
    """Polls `adb devices` periodically and syncs DB state."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("DeviceMonitor started (interval=%ds)", settings.ADB_POLL_INTERVAL)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("DeviceMonitor stopped")

    async def _poll_loop(self):
        while self._running:
            try:
                await self._sync_devices()
            except Exception:
                logger.exception("DeviceMonitor poll error")
            await asyncio.sleep(settings.ADB_POLL_INTERVAL)

    async def _sync_devices(self):
        adb_devices = await adb_manager.list_devices()
        connected_serials = {d["serial"] for d in adb_devices if d["status"] == "device"}

        async with async_session() as session:
            result = await session.execute(select(Device))
            db_devices = {d.id: d for d in result.scalars().all()}

            # New devices
            for serial in connected_serials - db_devices.keys():
                await self._register_device(session, serial)

            # Update existing
            for serial, device in db_devices.items():
                if serial in connected_serials:
                    if device.status == "OFFLINE":
                        device.status = "CONNECTED"
                    device.last_seen_at = datetime.now(timezone.utc)
                else:
                    if device.status not in ("OFFLINE", "ERROR"):
                        device.status = "OFFLINE"
                        logger.warning("Device %s went OFFLINE", serial)

            await session.commit()

    async def _register_device(self, session: AsyncSession, serial: str):
        logger.info("New device detected: %s", serial)
        model = await adb_manager.get_device_model(serial)
        android_ver = await adb_manager.get_android_version(serial)
        resolution = await adb_manager.get_resolution(serial)
        device = Device(
            id=serial,
            name=f"{model} ({serial[-5:]})",
            model=model,
            android_version=android_ver,
            resolution=resolution,
            status="CONNECTED",
        )
        session.add(device)
        logger.info("Registered device: %s (%s)", serial, model)


device_monitor = DeviceMonitor()
