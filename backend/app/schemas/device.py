"""Device Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DeviceOut(BaseModel):
    id: str
    name: str
    status: str
    model: str
    android_version: str
    resolution: str
    queue_length: int = 0
    connected_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DeviceListOut(BaseModel):
    devices: list[DeviceOut]


class DeviceUpdateIn(BaseModel):
    name: Optional[str] = None
