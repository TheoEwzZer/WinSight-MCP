"""Windows window management using win32gui."""

from __future__ import annotations

import ctypes
import time

import win32con
import win32gui

from .types import PublicWindowInfo, WindowInfo, WindowListEntry


def _is_candidate(hwnd: int, filter_lower: str | None = None) -> str | None:
    """Return the window title if hwnd is a visible window matching the filter, else None."""
    if not win32gui.IsWindowVisible(hwnd):
        return None
    title: str = win32gui.GetWindowText(hwnd)
    is_match: bool = bool(title and title.strip()) and (
        filter_lower is None or filter_lower in title.lower()
    )
    return title if is_match else None


def _build_window_info(hwnd: int, title: str) -> WindowInfo:
    """Build a WindowInfo dict from an hwnd and its title."""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    show_cmd: int = win32gui.GetWindowPlacement(hwnd)[1]
    return {
        "title": title,
        "hwnd": hwnd,
        "left": left,
        "top": top,
        "width": right - left,
        "height": bottom - top,
        "minimized": show_cmd == win32con.SW_SHOWMINIMIZED,
        "maximized": show_cmd == win32con.SW_SHOWMAXIMIZED,
    }


def list_windows(filter_text: str | None = None) -> list[WindowListEntry]:
    """List visible windows, optionally filtered by title substring."""
    results: list[WindowListEntry] = []
    filter_lower: str | None = filter_text.lower() if filter_text else None

    def enum_callback(hwnd: int, ctx: list[WindowListEntry]) -> bool:
        """Collect visible window info into ctx for each enumerated hwnd."""
        title: str | None = _is_candidate(hwnd, filter_lower)
        if title is not None:
            info: WindowInfo = _build_window_info(hwnd, title)
            ctx.append({**info, "active": hwnd == win32gui.GetForegroundWindow()})
        return True

    win32gui.EnumWindows(enum_callback, results)
    return results


def find_window(title: str) -> WindowInfo | None:
    """Find the first visible window whose title contains the given string (case-insensitive)."""
    container: list[WindowInfo] = []

    def enum_callback(hwnd: int, ctx: list[WindowInfo]) -> bool:
        """Find the first matching window and stop enumeration."""
        if ctx:
            return False
        wnd_title: str | None = _is_candidate(hwnd, title.lower())
        if wnd_title is not None:
            ctx.append(_build_window_info(hwnd, wnd_title))
            return False
        return True

    try:
        win32gui.EnumWindows(enum_callback, container)
    except Exception:
        pass

    return container[0] if container else None


def get_window_info(title: str) -> PublicWindowInfo | None:
    """Get detailed info about a window matching the title."""
    w: WindowInfo | None = find_window(title)
    if w is None:
        return None
    return {
        "title": w["title"],
        "left": w["left"],
        "top": w["top"],
        "width": w["width"],
        "height": w["height"],
        "minimized": w["minimized"],
        "maximized": w["maximized"],
        "active": w["hwnd"] == win32gui.GetForegroundWindow(),
    }


def focus_window(title: str) -> str:
    """Bring a window to the foreground using win32gui with thread-attach trick."""
    w: WindowInfo | None = find_window(title)
    if w is None:
        return f"No window found matching '{title}'"

    hwnd: int = w["hwnd"]
    try:
        if w["minimized"]:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)

        _force_foreground(hwnd)
        return f"Window '{w['title']}' is now focused"
    except Exception as e:
        return f"Failed to focus window '{w['title']}': {e}"


def _force_foreground(hwnd: int) -> None:
    """Force a window to the foreground, bypassing Windows restrictions."""
    foreground_hwnd: int = win32gui.GetForegroundWindow()
    current_thread_id: int = ctypes.windll.kernel32.GetCurrentThreadId()
    foreground_thread_id: int = ctypes.windll.user32.GetWindowThreadProcessId(
        foreground_hwnd, None
    )

    if current_thread_id != foreground_thread_id:
        ctypes.windll.user32.AttachThreadInput(
            current_thread_id, foreground_thread_id, True
        )

    try:
        win32gui.BringWindowToTop(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(hwnd)
    finally:
        if current_thread_id != foreground_thread_id:
            ctypes.windll.user32.AttachThreadInput(
                current_thread_id, foreground_thread_id, False
            )


def get_window_rect(title: str) -> tuple[int, int, int, int] | None:
    """Get (left, top, width, height) of a window matching the title."""
    w: WindowInfo | None = find_window(title)
    if w is None:
        return None
    return w["left"], w["top"], w["width"], w["height"]
