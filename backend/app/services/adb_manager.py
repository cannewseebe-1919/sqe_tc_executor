"""ADB Manager — wraps adb shell commands."""

import asyncio
import logging
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ADBManager:
    """Thin async wrapper around adb CLI."""

    def __init__(self, adb_path: str = settings.ADB_PATH):
        self.adb_path = adb_path

    async def run(self, *args: str, device_id: Optional[str] = None, timeout: float = 30) -> str:
        cmd = [self.adb_path]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(args)
        logger.debug("ADB: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"ADB command timed out: {' '.join(cmd)}")
        output = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            logger.warning("ADB error (rc=%d): %s", proc.returncode, err)
        return output

    async def shell(self, device_id: str, command: str, timeout: float = 30) -> str:
        return await self.run("shell", command, device_id=device_id, timeout=timeout)

    async def list_devices(self) -> list[dict]:
        """Return list of {serial, status} from adb devices."""
        output = await self.run("devices")
        devices = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                devices.append({"serial": parts[0], "status": parts[1]})
        return devices

    async def get_device_model(self, device_id: str) -> str:
        return await self.shell(device_id, "getprop ro.product.model")

    async def get_android_version(self, device_id: str) -> str:
        return await self.shell(device_id, "getprop ro.build.version.release")

    async def get_resolution(self, device_id: str) -> str:
        output = await self.shell(device_id, "wm size")
        # "Physical size: 1440x3120"
        if ":" in output:
            return output.split(":")[-1].strip()
        return output

    async def tap(self, device_id: str, x: int, y: int) -> str:
        return await self.shell(device_id, f"input tap {x} {y}")

    async def long_tap(self, device_id: str, x: int, y: int, duration: int = 1000) -> str:
        return await self.shell(device_id, f"input swipe {x} {y} {x} {y} {duration}")

    async def swipe(
        self, device_id: str, x1: int, y1: int, x2: int, y2: int, duration: int = 300
    ) -> str:
        return await self.shell(device_id, f"input swipe {x1} {y1} {x2} {y2} {duration}")

    async def input_text(self, device_id: str, text: str) -> str:
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        return await self.shell(device_id, f"input text '{escaped}'")

    async def key_event(self, device_id: str, keycode: str) -> str:
        return await self.shell(device_id, f"input keyevent {keycode}")

    async def launch_app(self, device_id: str, package: str) -> str:
        return await self.shell(
            device_id,
            f"am start -n $(cmd package resolve-activity --brief {package} | tail -n 1)",
        )

    async def stop_app(self, device_id: str, package: str) -> str:
        return await self.shell(device_id, f"am force-stop {package}")

    async def screenshot(self, device_id: str, remote_path: str = "/sdcard/screenshot.png") -> str:
        await self.shell(device_id, f"screencap -p {remote_path}")
        return remote_path

    async def pull_file(self, device_id: str, remote: str, local: str) -> str:
        return await self.run("pull", remote, local, device_id=device_id)

    async def get_current_activity(self, device_id: str) -> str:
        output = await self.shell(
            device_id, "dumpsys activity activities | grep mResumedActivity"
        )
        return output.strip()

    async def get_logcat(
        self, device_id: str, filter_expr: str = "", lines: int = 100
    ) -> str:
        cmd = f"logcat -d -t {lines}"
        if filter_expr:
            cmd += f" {filter_expr}"
        return await self.shell(device_id, cmd, timeout=10)

    async def install_apk(self, device_id: str, apk_path: str) -> str:
        return await self.run("install", "-r", apk_path, device_id=device_id, timeout=60)


adb_manager = ADBManager()
