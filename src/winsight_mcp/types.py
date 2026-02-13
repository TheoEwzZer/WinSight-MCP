"""Shared type definitions for WinSight MCP."""

from __future__ import annotations

from typing import TypedDict


class WindowInfo(TypedDict):
    """Window information returned by find_window and list_windows."""

    title: str
    hwnd: int
    left: int
    top: int
    width: int
    height: int
    minimized: bool
    maximized: bool


class WindowListEntry(WindowInfo):
    """Window entry with active state, returned by list_windows."""

    active: bool


class PublicWindowInfo(TypedDict):
    """Window info exposed to the user (no hwnd)."""

    title: str
    left: int
    top: int
    width: int
    height: int
    minimized: bool
    maximized: bool
    active: bool


class WindowRect(TypedDict):
    """Window position and size for capture."""

    title: str
    hwnd: int
    left: int
    top: int
    width: int
    height: int


class BitmapInfo(TypedDict):
    """Return type of PyCBitmap.GetInfo() (BITMAP struct)."""

    bmType: int
    bmWidth: int
    bmHeight: int
    bmWidthBytes: int
    bmPlanes: int
    bmBitsPixel: int


class MonitorInfo(TypedDict):
    """Monitor information returned by list_monitors."""

    index: int
    width: int
    height: int
    x: int
    y: int
    is_primary: bool


class ProcessResult(TypedDict, total=False):
    """Result from open_application."""

    pid: int
    command: str
    window: WindowRect
    window_warning: str
    error: str
