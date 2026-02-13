"""WinSight MCP Server - Windows Screen Capture for Claude Code."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP, Image

from .screenshot import (
    capture_full_screen,
    capture_region,
    capture_window_hwnd,
    list_monitors as _list_monitors,
)
from .types import ProcessResult, PublicWindowInfo, WindowInfo, WindowListEntry
from .window_manager import (
    find_window as _find_window,
    focus_window as _focus_window,
    get_window_info as _get_window_info,
    list_windows as _list_windows,
    maximize_window as _maximize_window,
    minimize_window as _minimize_window,
    move_window as _move_window,
    resize_window as _resize_window,
    restore_window as _restore_window,
    wait_for_window as _wait_for_window,
)
from .process_manager import open_application as _open_application

mcp: FastMCP = FastMCP("WinSight", instructions="Windows Screen Capture MCP Server")


@mcp.tool()
def take_screenshot(monitor: int = 1) -> Image:
    """Capture the full screen or a specific monitor.

    Args:
        monitor: Monitor index (0 = all monitors combined, 1 = primary, 2+ = others)
    """
    data: bytes = capture_full_screen(monitor)
    return Image(data=data, format="png")


@mcp.tool()
def screenshot_window(window_title: str) -> Image:
    """Capture a screenshot of a specific window by its title.
    Uses Win32 PrintWindow API to capture the actual window content,
    even if the window is behind other windows.

    Args:
        window_title: Partial title of the window to capture
    """
    w: WindowInfo | None = _find_window(window_title)
    if w is None:
        raise ValueError(f"No window found matching '{window_title}'")

    data: bytes = capture_window_hwnd(w["hwnd"])
    return Image(data=data, format="png")


@mcp.tool()
def screenshot_region(x: int, y: int, width: int, height: int) -> Image:
    """Capture a specific region of the screen.

    Args:
        x: Left coordinate of the region
        y: Top coordinate of the region
        width: Width of the region in pixels
        height: Height of the region in pixels
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid dimensions: {width}x{height}")
    data: bytes = capture_region(x, y, width, height)
    return Image(data=data, format="png")


@mcp.tool()
def list_windows(filter: str | None = None) -> str:
    """List all visible windows, optionally filtered by title.

    Args:
        filter: Optional substring to filter window titles
    """
    windows: list[WindowListEntry] = _list_windows(filter)
    if not windows:
        return "No visible windows found" + (f" matching '{filter}'" if filter else "")

    lines: list[str] = []
    for w in windows:
        state: str = ""
        if w["minimized"]:
            state = " [minimized]"
        elif w["maximized"]:
            state = " [maximized]"
        if w["active"]:
            state += " [active]"
        lines.append(
            f"- {w['title']}{state}\n"
            f"  Position: ({w['left']}, {w['top']}) Size: {w['width']}x{w['height']}"
        )
    return f"Found {len(windows)} window(s):\n\n" + "\n".join(lines)


@mcp.tool()
def focus_window(window_title: str) -> str:
    """Bring a window to the foreground.

    Args:
        window_title: Partial title of the window to focus
    """
    return _focus_window(window_title)


@mcp.tool()
def open_application(
    command: str,
    args: list[str] | None = None,
    wait_for_window: str | None = None,
    timeout: int = 10,
) -> str:
    """Launch an application and optionally wait for its window.

    Args:
        command: Command or path to executable
        args: Optional command-line arguments
        wait_for_window: Optional window title to wait for after launch
        timeout: Seconds to wait for the window (default: 10)
    """
    result: ProcessResult = _open_application(command, args, wait_for_window, timeout)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_window_info(window_title: str) -> str:
    """Get detailed information about a specific window.

    Args:
        window_title: Partial title of the window
    """
    info: PublicWindowInfo | None = _get_window_info(window_title)
    if info is None:
        return f"No window found matching '{window_title}'"
    return json.dumps(info, indent=2)


@mcp.tool()
def list_monitors() -> str:
    """List all available monitors with their resolution and position.

    Returns monitor index, dimensions, position, and whether it is the primary monitor.
    Use the monitor index with take_screenshot to capture a specific monitor.
    """
    monitors = _list_monitors()
    if not monitors:
        return "No monitors found"
    return json.dumps(monitors, indent=2)


@mcp.tool()
def resize_window(window_title: str, width: int, height: int) -> str:
    """Resize a window to the specified dimensions, keeping its current position.

    Args:
        window_title: Partial title of the window to resize
        width: New width in pixels
        height: New height in pixels
    """
    return _resize_window(window_title, width, height)


@mcp.tool()
def move_window(window_title: str, x: int, y: int) -> str:
    """Move a window to the specified position, keeping its current size.

    Args:
        window_title: Partial title of the window to move
        x: New left coordinate in pixels
        y: New top coordinate in pixels
    """
    return _move_window(window_title, x, y)


@mcp.tool()
def minimize_window(window_title: str) -> str:
    """Minimize a window to the taskbar.

    Args:
        window_title: Partial title of the window to minimize
    """
    return _minimize_window(window_title)


@mcp.tool()
def maximize_window(window_title: str) -> str:
    """Maximize a window to fill the screen.

    Args:
        window_title: Partial title of the window to maximize
    """
    return _maximize_window(window_title)


@mcp.tool()
def restore_window(window_title: str) -> str:
    """Restore a minimized or maximized window to its normal state.

    Args:
        window_title: Partial title of the window to restore
    """
    return _restore_window(window_title)


@mcp.tool()
def wait_for_window(window_title: str, timeout: int = 30) -> str:
    """Wait for a window matching the title to appear.

    Uses adaptive polling: 0.2s intervals for the first 5 seconds, then 0.5s.
    Useful after launching an application via Bash to wait for its UI to be ready.

    Args:
        window_title: Partial title of the window to wait for
        timeout: Maximum seconds to wait (default: 30)
    """
    return _wait_for_window(window_title, timeout)


def main() -> None:
    """Start the WinSight MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
