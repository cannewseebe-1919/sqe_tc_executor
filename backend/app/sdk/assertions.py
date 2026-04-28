"""Assertion helpers for TC scripts."""

from typing import Optional

from .device import device


def assert_screen(
    text_exists: Optional[str] = None,
    text_not_exists: Optional[str] = None,
    resource_id_exists: Optional[str] = None,
):
    """Assert conditions about the current screen.

    Args:
        text_exists: Assert that this text is visible on screen.
        text_not_exists: Assert that this text is NOT visible on screen.
        resource_id_exists: Assert that an element with this resource ID exists.
    """
    if text_exists is not None:
        elem = device.find_element(text=text_exists)
        if not elem:
            raise AssertionError(f"text '{text_exists}' not found on screen")

    if text_not_exists is not None:
        elem = device.find_element(text=text_not_exists)
        if elem:
            raise AssertionError(f"text '{text_not_exists}' should not exist but was found on screen")

    if resource_id_exists is not None:
        elem = device.find_element(resource_id=resource_id_exists)
        if not elem:
            raise AssertionError(f"resource_id '{resource_id_exists}' not found on screen")


def assert_element(
    text: Optional[str] = None,
    resource_id: Optional[str] = None,
    attribute: str = "text",
    expected: Optional[str] = None,
):
    """Assert that an element has a specific attribute value.

    Args:
        text: Find element by text.
        resource_id: Find element by resource ID.
        attribute: The attribute to check (e.g., 'text', 'enabled', 'checked').
        expected: The expected value of the attribute.
    """
    elem = device.find_element(text=text, resource_id=resource_id)
    if not elem:
        desc = text or resource_id or "unknown"
        raise AssertionError(f"Element '{desc}' not found")

    actual = elem.get(attribute)
    if actual is None:
        raise AssertionError(f"Element has no attribute '{attribute}'")

    if str(actual) != str(expected):
        raise AssertionError(
            f"Element attribute '{attribute}': expected '{expected}', got '{actual}'"
        )
