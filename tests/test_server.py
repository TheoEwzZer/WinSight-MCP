"""Integration tests for winsight_mcp.server MCP tools."""

from __future__ import annotations

import json
from typing import Any, Sequence
from unittest.mock import MagicMock, patch

from mcp.types import (
    AudioContent,
    EmbeddedResource,
    ImageContent,
    ResourceLink,
    TextContent,
    Tool,
)
import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from winsight_mcp.types import WindowInfo


async def _call(
    server: FastMCP, tool: str, args: dict[str, Any] | None = None
) -> list[Any]:
    """Call a tool and return the content list."""
    raw: (
        Sequence[
            TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource
        ]
        | dict[str, Any]
    ) = await server.call_tool(tool, args or {})
    if isinstance(raw, tuple):
        return list(raw[0])
    return list(raw)


def _text(result: list[Any]) -> str:
    """Extract the text string from a content list returned by _call."""
    return result[0].text


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


async def test_all_tools_registered(mcp_server: FastMCP) -> None:
    """All 14 MCP tools are registered on the server."""
    tools: list[Tool] = await mcp_server.list_tools()
    tool_names: set[str] = {t.name for t in tools}
    expected: set[str] = {
        "take_screenshot",
        "screenshot_window",
        "screenshot_region",
        "list_windows",
        "focus_window",
        "open_application",
        "get_window_info",
        "list_monitors",
        "resize_window",
        "move_window",
        "minimize_window",
        "maximize_window",
        "restore_window",
        "wait_for_window",
    }
    assert tool_names == expected


# ---------------------------------------------------------------------------
# take_screenshot
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server.capture_full_screen")
async def test_take_screenshot_returns_image(
    mock_capture: MagicMock, mcp_server: FastMCP, fake_png_bytes: bytes
) -> None:
    """Returns an Image content block for a valid monitor."""
    mock_capture.return_value = fake_png_bytes
    result: list[Any] = await _call(mcp_server, "take_screenshot", {"monitor": 1})
    assert len(result) == 1
    assert result[0].type == "image"
    mock_capture.assert_called_once_with(1)


@patch("winsight_mcp.server.capture_full_screen")
async def test_take_screenshot_default_monitor(
    mock_capture: MagicMock, mcp_server: FastMCP, fake_png_bytes: bytes
) -> None:
    """Omitting monitor uses default value (1)."""
    mock_capture.return_value = fake_png_bytes
    result: list[Any] = await _call(mcp_server, "take_screenshot")
    assert result[0].type == "image"
    mock_capture.assert_called_once_with(1)


@patch("winsight_mcp.server.capture_full_screen")
async def test_take_screenshot_invalid_monitor(
    mock_capture: MagicMock, mcp_server: FastMCP
) -> None:
    """Invalid monitor index raises ToolError."""
    mock_capture.side_effect = ValueError("Monitor 5 not found")
    with pytest.raises(ToolError, match="Monitor 5 not found"):
        await mcp_server.call_tool("take_screenshot", {"monitor": 5})


# ---------------------------------------------------------------------------
# screenshot_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server.capture_window_hwnd")
@patch("winsight_mcp.server._find_window")
async def test_screenshot_window_success(
    mock_find: MagicMock,
    mock_capture: MagicMock,
    mcp_server: FastMCP,
    fake_png_bytes: bytes,
    sample_window_info: WindowInfo,
) -> None:
    """Finds the window by title and returns an Image content block."""
    mock_find.return_value = sample_window_info
    mock_capture.return_value = fake_png_bytes
    result: list[Any] = await _call(
        mcp_server, "screenshot_window", {"window_title": "Test"}
    )
    assert len(result) == 1
    assert result[0].type == "image"


@patch("winsight_mcp.server._find_window")
async def test_screenshot_window_not_found(
    mock_find: MagicMock, mcp_server: FastMCP
) -> None:
    """Missing window raises ToolError."""
    mock_find.return_value = None
    with pytest.raises(ToolError, match="No window found"):
        await mcp_server.call_tool("screenshot_window", {"window_title": "nonexistent"})


# ---------------------------------------------------------------------------
# screenshot_region
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server.capture_region")
async def test_screenshot_region_success(
    mock_capture: MagicMock, mcp_server: FastMCP, fake_png_bytes: bytes
) -> None:
    """Valid region returns an Image content block."""
    mock_capture.return_value = fake_png_bytes
    result: list[Any] = await _call(
        mcp_server, "screenshot_region", {"x": 0, "y": 0, "width": 100, "height": 50}
    )
    assert len(result) == 1
    assert result[0].type == "image"


async def test_screenshot_region_invalid_dimensions(mcp_server: FastMCP) -> None:
    """Zero width raises ToolError."""
    with pytest.raises(ToolError, match="Invalid dimensions"):
        await mcp_server.call_tool(
            "screenshot_region", {"x": 0, "y": 0, "width": 0, "height": 50}
        )


async def test_screenshot_region_negative_height(mcp_server: FastMCP) -> None:
    """height <= 0 branch with valid width."""
    with pytest.raises(ToolError, match="Invalid dimensions"):
        await mcp_server.call_tool(
            "screenshot_region", {"x": 0, "y": 0, "width": 100, "height": -1}
        )


# ---------------------------------------------------------------------------
# list_windows
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._list_windows")
async def test_list_windows_with_results(
    mock_list: MagicMock, mcp_server: FastMCP
) -> None:
    """Formats window list with state labels and position info."""
    mock_list.return_value = [
        {
            "title": "Window A",
            "hwnd": 1,
            "left": 0,
            "top": 0,
            "width": 800,
            "height": 600,
            "minimized": False,
            "maximized": False,
            "active": True,
        }
    ]
    result: list[Any] = await _call(mcp_server, "list_windows")
    text: str = _text(result)
    assert "Window A" in text
    assert "[active]" in text
    assert "[minimized]" not in text
    assert "[maximized]" not in text


@patch("winsight_mcp.server._list_windows")
async def test_list_windows_empty(mock_list: MagicMock, mcp_server: FastMCP) -> None:
    """Empty result returns a 'no windows found' message."""
    mock_list.return_value = []
    result: list[Any] = await _call(mcp_server, "list_windows")
    assert "No visible windows found" in _text(result)


@patch("winsight_mcp.server._list_windows")
async def test_list_windows_formatting_states(
    mock_list: MagicMock, mcp_server: FastMCP
) -> None:
    """Verify [minimized], [maximized], [active] state labels and position format."""
    mock_list.return_value = [
        {
            "title": "Min Win",
            "hwnd": 1,
            "left": 10,
            "top": 20,
            "width": 800,
            "height": 600,
            "minimized": True,
            "maximized": False,
            "active": False,
        },
        {
            "title": "Max Win",
            "hwnd": 2,
            "left": 0,
            "top": 0,
            "width": 1920,
            "height": 1080,
            "minimized": False,
            "maximized": True,
            "active": True,
        },
    ]
    result: list[Any] = await _call(mcp_server, "list_windows")
    text: str = _text(result)
    assert "Found 2 window(s):" in text
    assert "[minimized]" in text
    assert "[maximized] [active]" in text
    assert "Position: (10, 20) Size: 800x600" in text
    assert "Position: (0, 0) Size: 1920x1080" in text


@patch("winsight_mcp.server._list_windows")
async def test_list_windows_empty_with_filter(
    mock_list: MagicMock, mcp_server: FastMCP
) -> None:
    """Empty result with a filter includes the filter string in the message."""
    mock_list.return_value = []
    result: list[Any] = await _call(mcp_server, "list_windows", {"filter": "notepad"})
    text: str = _text(result)
    assert "No visible windows found" in text
    assert "notepad" in text


# ---------------------------------------------------------------------------
# focus_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._focus_window")
async def test_focus_window_delegates(
    mock_focus: MagicMock, mcp_server: FastMCP
) -> None:
    """Delegates to _focus_window and returns the result string."""
    mock_focus.return_value = "Window 'Test' is now focused"
    result: list[Any] = await _call(
        mcp_server, "focus_window", {"window_title": "Test"}
    )
    assert "now focused" in _text(result)


# ---------------------------------------------------------------------------
# open_application
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._open_application")
async def test_open_application_returns_json(
    mock_open: MagicMock, mcp_server: FastMCP
) -> None:
    """Successful launch returns JSON with pid and command."""
    mock_open.return_value = {"pid": 1234, "command": "notepad.exe"}
    result: list[Any] = await _call(
        mcp_server, "open_application", {"command": "notepad.exe"}
    )
    data = json.loads(_text(result))
    assert data["pid"] == 1234


@patch("winsight_mcp.server._open_application")
async def test_open_application_error_returns_json(
    mock_open: MagicMock, mcp_server: FastMCP
) -> None:
    """Error from process_manager is serialised as JSON with 'error' key."""
    mock_open.return_value = {"error": "Command not found: ghost.exe"}
    result: list[Any] = await _call(
        mcp_server, "open_application", {"command": "ghost.exe"}
    )
    data = json.loads(_text(result))
    assert "error" in data
    assert "Command not found" in data["error"]


@patch("winsight_mcp.server._open_application")
async def test_open_application_with_wait_for_window(
    mock_open: MagicMock, mcp_server: FastMCP
) -> None:
    """open_application with wait_for_window passes all args correctly."""
    mock_open.return_value = {
        "pid": 5678,
        "command": "notepad.exe",
        "window": {
            "title": "Notepad",
            "hwnd": 42,
            "left": 0,
            "top": 0,
            "width": 800,
            "height": 600,
        },
    }
    result: list[Any] = await _call(
        mcp_server,
        "open_application",
        {"command": "notepad.exe", "wait_for_window": "Notepad", "timeout": 5},
    )
    data = json.loads(_text(result))
    assert data["pid"] == 5678
    assert "window" in data
    mock_open.assert_called_once_with("notepad.exe", None, "Notepad", 5)


# ---------------------------------------------------------------------------
# get_window_info
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._get_window_info")
async def test_get_window_info_found(mock_info: MagicMock, mcp_server: FastMCP) -> None:
    """Found window returns JSON with title and no hwnd."""
    mock_info.return_value = {
        "title": "Test",
        "left": 0,
        "top": 0,
        "width": 800,
        "height": 600,
        "minimized": False,
        "maximized": False,
        "active": True,
    }
    result: list[Any] = await _call(
        mcp_server, "get_window_info", {"window_title": "Test"}
    )
    data = json.loads(_text(result))
    assert data["title"] == "Test"


@patch("winsight_mcp.server._get_window_info")
async def test_get_window_info_not_found(
    mock_info: MagicMock, mcp_server: FastMCP
) -> None:
    """Missing window returns a 'not found' message."""
    mock_info.return_value = None
    result: list[Any] = await _call(
        mcp_server, "get_window_info", {"window_title": "nonexistent"}
    )
    assert "No window found" in _text(result)


# ---------------------------------------------------------------------------
# list_monitors
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._list_monitors")
async def test_list_monitors_returns_json(
    mock_list: MagicMock, mcp_server: FastMCP
) -> None:
    """Returns JSON array with monitor info."""
    mock_list.return_value = [
        {"index": 1, "width": 1920, "height": 1080, "x": 0, "y": 0, "is_primary": True},
    ]
    result: list[Any] = await _call(mcp_server, "list_monitors")
    data = json.loads(_text(result))
    assert len(data) == 1
    assert data[0]["is_primary"] is True


@patch("winsight_mcp.server._list_monitors")
async def test_list_monitors_empty(mock_list: MagicMock, mcp_server: FastMCP) -> None:
    """Empty monitor list returns a 'not found' message."""
    mock_list.return_value = []
    result: list[Any] = await _call(mcp_server, "list_monitors")
    assert "No monitors found" in _text(result)


# ---------------------------------------------------------------------------
# resize_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._resize_window")
async def test_resize_window_delegates(
    mock_resize: MagicMock, mcp_server: FastMCP
) -> None:
    """Delegates to _resize_window with correct args."""
    mock_resize.return_value = "Window 'Test' resized to 800x600"
    result: list[Any] = await _call(
        mcp_server,
        "resize_window",
        {"window_title": "Test", "width": 800, "height": 600},
    )
    assert "resized" in _text(result)
    mock_resize.assert_called_once_with("Test", 800, 600)


# ---------------------------------------------------------------------------
# move_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._move_window")
async def test_move_window_delegates(mock_move: MagicMock, mcp_server: FastMCP) -> None:
    """Delegates to _move_window with correct args."""
    mock_move.return_value = "Window 'Test' moved to (100, 200)"
    result: list[Any] = await _call(
        mcp_server, "move_window", {"window_title": "Test", "x": 100, "y": 200}
    )
    assert "moved" in _text(result)
    mock_move.assert_called_once_with("Test", 100, 200)


# ---------------------------------------------------------------------------
# minimize_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._minimize_window")
async def test_minimize_window_delegates(
    mock_min: MagicMock, mcp_server: FastMCP
) -> None:
    """Delegates to _minimize_window."""
    mock_min.return_value = "Window 'Test' minimized"
    result: list[Any] = await _call(
        mcp_server, "minimize_window", {"window_title": "Test"}
    )
    assert "minimized" in _text(result)


# ---------------------------------------------------------------------------
# maximize_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._maximize_window")
async def test_maximize_window_delegates(
    mock_max: MagicMock, mcp_server: FastMCP
) -> None:
    """Delegates to _maximize_window."""
    mock_max.return_value = "Window 'Test' maximized"
    result: list[Any] = await _call(
        mcp_server, "maximize_window", {"window_title": "Test"}
    )
    assert "maximized" in _text(result)


# ---------------------------------------------------------------------------
# restore_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._restore_window")
async def test_restore_window_delegates(
    mock_restore: MagicMock, mcp_server: FastMCP
) -> None:
    """Delegates to _restore_window."""
    mock_restore.return_value = "Window 'Test' restored"
    result: list[Any] = await _call(
        mcp_server, "restore_window", {"window_title": "Test"}
    )
    assert "restored" in _text(result)


# ---------------------------------------------------------------------------
# wait_for_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server._wait_for_window")
async def test_wait_for_window_found(mock_wait: MagicMock, mcp_server: FastMCP) -> None:
    """Returns success message when window is found."""
    mock_wait.return_value = "Window found: 'My App'"
    result: list[Any] = await _call(
        mcp_server, "wait_for_window", {"window_title": "My App", "timeout": 10}
    )
    assert "Window found" in _text(result)
    mock_wait.assert_called_once_with("My App", 10)


@patch("winsight_mcp.server._wait_for_window")
async def test_wait_for_window_timeout(
    mock_wait: MagicMock, mcp_server: FastMCP
) -> None:
    """Returns timeout message when window is not found."""
    mock_wait.return_value = "Timed out waiting for window matching 'Ghost' after 5s"
    result: list[Any] = await _call(
        mcp_server, "wait_for_window", {"window_title": "Ghost", "timeout": 5}
    )
    assert "Timed out" in _text(result)


@patch("winsight_mcp.server._wait_for_window")
async def test_wait_for_window_default_timeout(
    mock_wait: MagicMock, mcp_server: FastMCP
) -> None:
    """Omitting timeout defaults to 30 seconds."""
    mock_wait.return_value = "Window found: 'App'"
    await mcp_server.call_tool("wait_for_window", {"window_title": "App"})
    mock_wait.assert_called_once_with("App", 30)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server.mcp")
def test_main_calls_mcp_run(mock_mcp: MagicMock) -> None:
    """main() starts the server over stdio."""
    from winsight_mcp.server import main

    main()
    mock_mcp.run.assert_called_once_with(transport="stdio")


# ---------------------------------------------------------------------------
# __main__ entry point
# ---------------------------------------------------------------------------


@patch("winsight_mcp.server.main")
def test_dunder_main_calls_main(mock_main: MagicMock) -> None:
    """python -m winsight_mcp invokes main()."""
    import runpy

    runpy.run_module("winsight_mcp", run_name="__main__")
    mock_main.assert_called_once()
