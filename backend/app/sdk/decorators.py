"""@step decorator for TC methods."""

import functools
import json
import sys
import time
import traceback
from typing import Optional


def step(name: str, timeout: Optional[int] = None):
    """Decorator that wraps a test step method.

    Captures timing, exceptions, and emits JSON result to stdout
    so the TestRunner can parse it.
    """

    def decorator(func):
        func._step_name = name
        func._step_timeout = timeout

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            import os

            step_timeout = timeout or getattr(self, "timeout_per_step", 30)
            start = time.time()
            result = {
                "name": name,
                "status": "PASSED",
                "duration_sec": 0,
                "log": "",
                "error_type": None,
                "screenshot_path": None,
            }
            try:
                func(self, *args, **kwargs)
            except AssertionError as e:
                result["status"] = "FAILED"
                result["error_type"] = "ASSERTION_FAILED"
                result["log"] = str(e)
            except ElementNotFoundError as e:
                result["status"] = "FAILED"
                result["error_type"] = "ELEMENT_NOT_FOUND"
                result["log"] = str(e)
            except TimeoutError as e:
                result["status"] = "FAILED"
                result["error_type"] = "STEP_TIMEOUT"
                result["log"] = str(e)
            except Exception as e:
                result["status"] = "FAILED"
                result["error_type"] = "ADB_ERROR"
                result["log"] = traceback.format_exc()

            result["duration_sec"] = round(time.time() - start, 3)

            # Check for auto-screenshot
            screenshot_dir = os.environ.get("TC_SCREENSHOT_DIR", "")
            if screenshot_dir:
                try:
                    from device import device as dev
                    path = dev.screenshot(func.__name__)
                    result["screenshot_path"] = path
                except Exception:
                    pass

            # Emit result as JSON line (ensure_ascii=True avoids Windows stdout encoding issues)
            print(f"[STEP_RESULT]{json.dumps(result, ensure_ascii=True)}", flush=True)
            return result

        return wrapper

    return decorator


class ElementNotFoundError(Exception):
    """Raised when a UI element cannot be found."""
    pass
