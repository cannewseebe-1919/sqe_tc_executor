"""Device management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.device import Device
from app.schemas.device import DeviceOut, DeviceListOut, DeviceUpdateIn
from app.services.scheduler import scheduler

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", response_model=DeviceListOut)
async def list_devices(db: AsyncSession = Depends(get_db)):
    """List all registered devices with their status and queue length."""
    result = await db.execute(select(Device))
    devices = result.scalars().all()
    out = []
    for d in devices:
        q_len = await scheduler.queue_length(d.id)
        out.append(DeviceOut(
            id=d.id,
            name=d.name,
            status=d.status,
            model=d.model,
            android_version=d.android_version,
            resolution=d.resolution,
            queue_length=q_len,
        ))
    return DeviceListOut(devices=out)


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    q_len = await scheduler.queue_length(device.id)
    return DeviceOut(
        id=device.id,
        name=device.name,
        status=device.status,
        model=device.model,
        android_version=device.android_version,
        resolution=device.resolution,
        queue_length=q_len,
    )


@router.patch("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: str, data: DeviceUpdateIn, db: AsyncSession = Depends(get_db)
):
    """Update device info (e.g., user-assigned name)."""
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if data.name is not None:
        device.name = data.name
    await db.commit()
    await db.refresh(device)
    q_len = await scheduler.queue_length(device.id)
    return DeviceOut(
        id=device.id,
        name=device.name,
        status=device.status,
        model=device.model,
        android_version=device.android_version,
        resolution=device.resolution,
        queue_length=q_len,
    )
