"""tc_executor_sdk — TC 스크립트에서 사용하는 SDK 진입점.

TC 스크립트 예시:
    from tc_executor_sdk import TestCase, device, step, assert_screen, assert_element
"""

from app.sdk import TestCase, device, step, assert_screen, assert_element
from app.sdk.decorators import ElementNotFoundError

__all__ = ["TestCase", "device", "step", "assert_screen", "assert_element", "ElementNotFoundError"]
