"""Tests for winsight_mcp.types TypedDict definitions."""

from __future__ import annotations

from winsight_mcp.types import (
    BitmapInfo,
    MonitorInfo,
    PublicWindowInfo,
    WindowInfo,
    WindowRect,
)


def test_window_info_keys() -> None:
    """WindowInfo has the 8 expected keys."""
    expected: set[str] = {
        "title",
        "hwnd",
        "left",
        "top",
        "width",
        "height",
        "minimized",
        "maximized",
    }
    assert set(WindowInfo.__annotations__) == expected


def test_public_window_info_excludes_hwnd() -> None:
    """PublicWindowInfo does not have 'hwnd'."""
    all_keys: set[str] = set()
    for cls in PublicWindowInfo.__mro__:
        if hasattr(cls, "__annotations__"):
            all_keys.update(cls.__annotations__)
    assert "hwnd" not in all_keys


def test_window_rect_keys() -> None:
    """WindowRect has the expected keys."""
    expected: set[str] = {"title", "hwnd", "left", "top", "width", "height"}
    assert set(WindowRect.__annotations__) == expected


def test_bitmap_info_keys() -> None:
    """BitmapInfo has the expected keys."""
    expected: set[str] = {
        "bmType",
        "bmWidth",
        "bmHeight",
        "bmWidthBytes",
        "bmPlanes",
        "bmBitsPixel",
    }
    assert set(BitmapInfo.__annotations__) == expected


def test_monitor_info_keys() -> None:
    """MonitorInfo has the 6 expected keys."""
    expected: set[str] = {"index", "width", "height", "x", "y", "is_primary"}
    assert set(MonitorInfo.__annotations__) == expected
