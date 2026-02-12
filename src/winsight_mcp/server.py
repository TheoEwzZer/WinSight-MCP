"""WinSight MCP Server - Windows Screen Capture for Claude Code."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP, Image

from .screenshot import capture_full_screen, capture_region, capture_window_hwnd
from .types import ProcessResult, PublicWindowInfo, WindowInfo, WindowListEntry
from .window_manager import (
    find_window as _find_window,
    list_windows as _list_windows,
    get_window_info as _get_window_info,
    focus_window as _focus_window,
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


def main() -> None:
    """Start the WinSight MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
