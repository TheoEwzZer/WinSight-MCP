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


def resize_window(window_title: str, width: int, height: int) -> str:
    """Resize a window to the given dimensions, keeping its current position."""
    w: WindowInfo | None = find_window(window_title)
    if w is None:
        return f"No window found matching '{window_title}'"

    hwnd: int = w["hwnd"]
    try:
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            0,
            0,
            width,
            height,
            win32con.SWP_NOMOVE | win32con.SWP_NOZORDER,
        )
        return f"Window '{w['title']}' resized to {width}x{height}"
    except Exception as e:
        return f"Failed to resize window '{w['title']}': {e}"


def move_window(window_title: str, x: int, y: int) -> str:
    """Move a window to the given position, keeping its current size."""
    w: WindowInfo | None = find_window(window_title)
    if w is None:
        return f"No window found matching '{window_title}'"

    hwnd: int = w["hwnd"]
    try:
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            x,
            y,
            0,
            0,
            win32con.SWP_NOSIZE | win32con.SWP_NOZORDER,
        )
        return f"Window '{w['title']}' moved to ({x}, {y})"
    except Exception as e:
        return f"Failed to move window '{w['title']}': {e}"


def minimize_window(window_title: str) -> str:
    """Minimize a window."""
    w: WindowInfo | None = find_window(window_title)
    if w is None:
        return f"No window found matching '{window_title}'"

    try:
        win32gui.ShowWindow(w["hwnd"], win32con.SW_MINIMIZE)
        return f"Window '{w['title']}' minimized"
    except Exception as e:
        return f"Failed to minimize window '{w['title']}': {e}"


def maximize_window(window_title: str) -> str:
    """Maximize a window."""
    w: WindowInfo | None = find_window(window_title)
    if w is None:
        return f"No window found matching '{window_title}'"

    try:
        win32gui.ShowWindow(w["hwnd"], win32con.SW_MAXIMIZE)
        return f"Window '{w['title']}' maximized"
    except Exception as e:
        return f"Failed to maximize window '{w['title']}': {e}"


def restore_window(window_title: str) -> str:
    """Restore a minimized or maximized window to its normal state."""
    w: WindowInfo | None = find_window(window_title)
    if w is None:
        return f"No window found matching '{window_title}'"

    try:
        win32gui.ShowWindow(w["hwnd"], win32con.SW_RESTORE)
        return f"Window '{w['title']}' restored"
    except Exception as e:
        return f"Failed to restore window '{w['title']}': {e}"


def wait_for_window(window_title: str, timeout: int = 30) -> str:
    """Wait for a window matching the title to appear.

    Uses adaptive polling: 0.2s intervals for the first 5 seconds, then 0.5s.
    """
    start: float = time.time()
    while time.time() - start < timeout:
        w: WindowInfo | None = find_window(window_title)
        if w is not None:
            return f"Window found: '{w['title']}'"
        elapsed: float = time.time() - start
        time.sleep(0.2 if elapsed < 5 else 0.5)
    return f"Timed out waiting for window matching '{window_title}' after {timeout}s"


def get_window_rect(title: str) -> tuple[int, int, int, int] | None:
    """Get (left, top, width, height) of a window matching the title."""
    w: WindowInfo | None = find_window(title)
    if w is None:
        return None
    return w["left"], w["top"], w["width"], w["height"]
