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


async def _setup_adb_reverse(serial: str):
    """Set up adb reverse so the Runner App can reach the backend via USB."""
    port = settings.BACKEND_EXTERNAL_PORT
    try:
        await adb_manager.run("reverse", f"tcp:{port}", f"tcp:{port}", device_id=serial)
        logger.info("adb reverse tcp:%d set up for %s", port, serial)
    except Exception:
        logger.warning("Failed to set up adb reverse for %s", serial)


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
        if not settings.ADB_ENABLED:
            logger.info("DeviceMonitor: ADB_ENABLED=False, skipping real device sync")
            return
        while self._running:
            try:
                await self._sync_devices()
            except Exception:
                logger.exception("DeviceMonitor poll error")
            await asyncio.sleep(settings.ADB_POLL_INTERVAL)

    async def _sync_devices(self):
        adb_devices = await adb_manager.list_devices()
        connected_serials = {d["serial"] for d in adb_devices if d["status"] == "device"}

        # Collect serials that just came back online (need queue processing after commit)
        reconnected: list[str] = []

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
                        reconnected.append(serial)
                        logger.info("Device %s reconnected", serial)
                    device.last_seen_at = datetime.now(timezone.utc)
                else:
                    if device.status not in ("OFFLINE", "ERROR"):
                        device.status = "OFFLINE"
                        logger.warning("Device %s went OFFLINE", serial)

            await session.commit()

        # After commit: set up adb reverse and process queued executions for reconnected devices
        for serial in reconnected:
            await _setup_adb_reverse(serial)
            await self._process_queued(serial)

    async def _process_queued(self, device_id: str):
        """Start the next queued execution for a device that just came back online."""
        from app.services.scheduler import scheduler
        from app.services.test_runner import test_runner

        next_id = await scheduler.dequeue(device_id)
        if next_id:
            logger.info("Processing queued execution %s for device %s", next_id, device_id)
            asyncio.create_task(test_runner.execute(next_id))

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
        await _setup_adb_reverse(serial)


device_monitor = DeviceMonitor()
