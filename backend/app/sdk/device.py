"""device object — provides tap, swipe, input_text, screenshot, UI navigation, etc."""

import json
import os
import re
import shlex
import subprocess
import time
from typing import Optional, Tuple

import httpx


class _Device:
    """Singleton device controller used inside TC scripts.

    Communicates with the Runner App (HTTP via adb forward) and
    sends ADB shell commands for input actions.
    """

    def __init__(self):
        self._device_id: str = ""
        self._adb: str = "adb"
        self._backend_port: int = 8001
        self._screenshot_dir: str = ""
        self._initialized = False

    def _ensure_init(self):
        if not self._initialized:
            self._device_id = os.environ.get("TC_DEVICE_ID", "")
            self._adb = os.environ.get("TC_ADB_PATH", "adb")
            self._backend_port = int(os.environ.get("TC_BACKEND_PORT", "8001"))
            self._screenshot_dir = os.environ.get("TC_SCREENSHOT_DIR", "screenshots")
            os.makedirs(self._screenshot_dir, exist_ok=True)
            self._initialized = True

    @staticmethod
    def _sanitize_shell_arg(value: str) -> str:
        """Remove shell metacharacters to prevent command injection."""
        return re.sub(r'[;&|`$(){}\\<>!\n\r]', '', value)

    def _adb_shell(self, command: str, timeout: float = 30) -> str:
        self._ensure_init()
        cmd = [self._adb]
        if self._device_id:
            cmd.extend(["-s", self._device_id])
        cmd.extend(["shell", command])
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()

    def _runner_url(self) -> str:
        self._ensure_init()
        return f"http://127.0.0.1:{self._backend_port}/runner/{self._device_id}"

    def _runner_get(self, path: str, params: dict = None, timeout: float = 10) -> dict:
        self._ensure_init()
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{self._runner_url()}{path}", params=params or {})
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Device control
    # ------------------------------------------------------------------

    def launch_app(self, package: str):
        """Launch an app by package name."""
        self._adb_shell(
            f"am start -n $(cmd package resolve-activity --brief {package} | tail -n 1)"
        )

    def stop_app(self, package: str):
        """Force-stop an app."""
        self._adb_shell(f"am force-stop {package}")

    def tap(
        self,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        xy: Optional[Tuple[int, int]] = None,
    ):
        """Tap on an element by text, resource_id, or (x, y) coordinates."""
        x, y = self._resolve_coordinates(text=text, resource_id=resource_id, xy=xy)
        self._adb_shell(f"input tap {x} {y}")

    def long_tap(
        self,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        xy: Optional[Tuple[int, int]] = None,
        duration: int = 1000,
    ):
        """Long-tap on an element."""
        x, y = self._resolve_coordinates(text=text, resource_id=resource_id, xy=xy)
        self._adb_shell(f"input swipe {x} {y} {x} {y} {duration}")

    def swipe(
        self,
        start_xy: Tuple[int, int],
        end_xy: Tuple[int, int],
        duration: int = 300,
    ):
        """Swipe from start to end coordinates."""
        self._adb_shell(
            f"input swipe {start_xy[0]} {start_xy[1]} {end_xy[0]} {end_xy[1]} {duration}"
        )

    def swipe_direction(self, direction: str, duration: int = 300):
        """Swipe in a direction (up/down/left/right) using center-based coordinates."""
        # Get screen size
        size_output = self._adb_shell("wm size")
        # "Physical size: 1080x1920"
        parts = size_output.split(":")[-1].strip().split("x")
        w, h = int(parts[0]), int(parts[1])
        cx, cy = w // 2, h // 2
        offset = min(w, h) // 3

        directions = {
            "up": (cx, cy + offset, cx, cy - offset),
            "down": (cx, cy - offset, cx, cy + offset),
            "left": (cx + offset, cy, cx - offset, cy),
            "right": (cx - offset, cy, cx + offset, cy),
        }
        coords = directions.get(direction.lower())
        if not coords:
            raise ValueError(f"Invalid direction: {direction}. Use up/down/left/right")
        self._adb_shell(f"input swipe {coords[0]} {coords[1]} {coords[2]} {coords[3]} {duration}")

    def input_text(self, text: str):
        """Type text into the currently focused field."""
        sanitized = self._sanitize_shell_arg(text)
        escaped = sanitized.replace(" ", "%s")
        self._adb_shell(f"input text {shlex.quote(escaped)}")

    def press_key(self, key: str):
        """Press a key (back, home, enter, volume_up, volume_down, power, etc.)."""
        if not re.match(r'^[a-zA-Z0-9_]+$', key):
            raise ValueError(f"Invalid key name: {key}")
        keycode_map = {
            "back": "KEYCODE_BACK",
            "home": "KEYCODE_HOME",
            "enter": "KEYCODE_ENTER",
            "menu": "KEYCODE_MENU",
            "volume_up": "KEYCODE_VOLUME_UP",
            "volume_down": "KEYCODE_VOLUME_DOWN",
            "power": "KEYCODE_POWER",
            "tab": "KEYCODE_TAB",
            "delete": "KEYCODE_DEL",
            "recent": "KEYCODE_APP_SWITCH",
        }
        keycode = keycode_map.get(key.lower(), key)
        self._adb_shell(f"input keyevent {keycode}")

    def wait(self, seconds: float):
        """Wait for a given number of seconds."""
        time.sleep(seconds)

    # ------------------------------------------------------------------
    # UI navigation (Runner App)
    # ------------------------------------------------------------------

    def find_element(
        self,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        class_name: Optional[str] = None,
    ) -> Optional[dict]:
        """Find a UI element. Returns dict with bounds, text, resource_id, etc."""
        params = {}
        if text:
            params["text"] = text
        if resource_id:
            params["resource_id"] = resource_id
        if class_name:
            params["class_name"] = class_name
        try:
            return self._runner_get("/find-element", params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_ui_tree(self) -> dict:
        """Get the full UI tree of the current screen."""
        return self._runner_get("/ui-tree")

    def wait_for_element(
        self,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        timeout: int = 10,
    ) -> dict:
        """Wait until an element appears on screen."""
        from app.sdk.decorators import ElementNotFoundError

        deadline = time.time() + timeout
        while time.time() < deadline:
            elem = self.find_element(text=text, resource_id=resource_id)
            if elem:
                return elem
            time.sleep(0.5)
        desc = text or resource_id or "unknown"
        raise ElementNotFoundError(f"Element '{desc}' not found within {timeout}s")

    def element_exists(
        self,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if an element exists on screen."""
        return self.find_element(text=text, resource_id=resource_id) is not None

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def screenshot(self, name: str = "screenshot") -> str:
        """Take a screenshot via Runner App and save locally. Returns the file path."""
        self._ensure_init()
        import base64
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(f"{self._runner_url()}/screenshot")
                resp.raise_for_status()
                data = resp.json()
                png_bytes = base64.b64decode(data["data"])
                local_path = os.path.join(self._screenshot_dir, f"{name}.png")
                with open(local_path, "wb") as f:
                    f.write(png_bytes)
                return local_path
        except Exception:
            # Fallback to ADB screencap if Runner App is not connected
            remote_path = "/sdcard/tc_screenshot.png"
            self._adb_shell(f"screencap {remote_path}")
            local_path = os.path.join(self._screenshot_dir, f"{name}.png")
            cmd = [self._adb]
            if self._device_id:
                cmd.extend(["-s", self._device_id])
            cmd.extend(["pull", remote_path, local_path])
            subprocess.run(cmd, capture_output=True, timeout=10)
            return local_path

    def get_logcat(self, filter: str = "", lines: int = 100) -> str:
        """Collect logcat logs."""
        cmd = f"logcat -d -t {lines}"
        if filter:
            cmd += f" {filter}"
        return self._adb_shell(cmd)

    def get_current_activity(self) -> str:
        """Get the name of the currently resumed Activity."""
        output = self._adb_shell("dumpsys activity activities | grep mResumedActivity")
        return output.strip()

    def get_device_info(self) -> dict:
        """Get device model, OS version, resolution."""
        return {
            "model": self._adb_shell("getprop ro.product.model"),
            "android_version": self._adb_shell("getprop ro.build.version.release"),
            "resolution": self._adb_shell("wm size").split(":")[-1].strip() if ":" in self._adb_shell("wm size") else "",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_coordinates(
        self,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        xy: Optional[Tuple[int, int]] = None,
    ) -> Tuple[int, int]:
        """Resolve element to (x, y) center coordinates."""
        from app.sdk.decorators import ElementNotFoundError

        if xy:
            return xy

        elem = self.find_element(text=text, resource_id=resource_id)
        if not elem:
            desc = text or resource_id or "unknown"
            raise ElementNotFoundError(f"Element '{desc}' not found")

        bounds = elem.get("bounds", {})
        x = (bounds.get("left", 0) + bounds.get("right", 0)) // 2
        y = (bounds.get("top", 0) + bounds.get("bottom", 0)) // 2
        return x, y


# Singleton instance used in TC scripts
device = _Device()
