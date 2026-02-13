"""Tests for winsight_mcp.window_manager."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
import win32con

from winsight_mcp.types import PublicWindowInfo, WindowInfo, WindowListEntry
from winsight_mcp.window_manager import (
    build_window_info,
    force_foreground,
    is_candidate,
    find_window,
    focus_window,
    get_window_info,
    get_window_rect,
    list_windows,
    maximize_window,
    minimize_window,
    move_window,
    resize_window,
    restore_window,
    wait_for_window,
)


def _enum_single(
    hwnd: int,
) -> Callable[[Callable[[int, list[Any]], object], list[Any]], None]:
    """Return an EnumWindows side_effect that enumerates a single hwnd."""

    def _enum(callback: Callable[[int, list[Any]], object], ctx: list[Any]) -> None:
        """Simulate EnumWindows with a single window handle."""
        callback(hwnd, ctx)

    return _enum


# ---------------------------------------------------------------------------
# is_candidate
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
def test_is_candidate_visible_match(mock_gui: MagicMock) -> None:
    """Visible window matching the filter returns its title."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "My Test Window"
    assert is_candidate(1, "test") == "My Test Window"


@patch("winsight_mcp.window_manager.win32gui")
def test_is_candidate_not_visible(mock_gui: MagicMock) -> None:
    """Invisible window returns None."""
    mock_gui.IsWindowVisible.return_value = False
    assert is_candidate(1, "test") is None


@patch("winsight_mcp.window_manager.win32gui")
def test_is_candidate_empty_title(mock_gui: MagicMock) -> None:
    """Window with empty title returns None."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = ""
    assert is_candidate(1, None) is None


@patch("winsight_mcp.window_manager.win32gui")
def test_is_candidate_filter_no_match(mock_gui: MagicMock) -> None:
    """Window not matching the filter returns None."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "Other Window"
    assert is_candidate(1, "notepad") is None


@patch("winsight_mcp.window_manager.win32gui")
def test_is_candidate_whitespace_title(mock_gui: MagicMock) -> None:
    """Title with only spaces is rejected by title.strip()."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "   "
    assert is_candidate(1, None) is None


@patch("winsight_mcp.window_manager.win32gui")
def test_is_candidate_no_filter_with_valid_title(mock_gui: MagicMock) -> None:
    """Visible window with a real title and no filter returns the title."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "My App"
    assert is_candidate(1, None) == "My App"


# ---------------------------------------------------------------------------
# build_window_info
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
def testbuild_window_info_normal(mock_gui: MagicMock) -> None:
    """Normal window returns correct geometry and non-minimized/maximized state."""
    mock_gui.GetWindowRect.return_value = (10, 20, 810, 620)
    mock_gui.GetWindowPlacement.return_value = (
        0,
        win32con.SW_SHOW,
        (0, 0),
        (0, 0),
        (10, 20, 810, 620),
    )
    info: WindowInfo = build_window_info(42, "Test")
    assert info == {
        "title": "Test",
        "hwnd": 42,
        "left": 10,
        "top": 20,
        "width": 800,
        "height": 600,
        "minimized": False,
        "maximized": False,
    }


@patch("winsight_mcp.window_manager.win32gui")
def testbuild_window_info_minimized(mock_gui: MagicMock) -> None:
    """Minimized window is detected from SW_SHOWMINIMIZED placement."""
    mock_gui.GetWindowRect.return_value = (-32000, -32000, -31840, -31920)
    mock_gui.GetWindowPlacement.return_value = (
        0,
        win32con.SW_SHOWMINIMIZED,
        (0, 0),
        (0, 0),
        (-32000, -32000, -31840, -31920),
    )
    info: WindowInfo = build_window_info(99, "Minimized")
    assert info["title"] == "Minimized"
    assert info["hwnd"] == 99
    assert info["minimized"] is True
    assert info["maximized"] is False
    assert info["width"] == 160
    assert info["height"] == 80


@patch("winsight_mcp.window_manager.win32gui")
def testbuild_window_info_maximized(mock_gui: MagicMock) -> None:
    """Maximized window is detected from SW_SHOWMAXIMIZED placement."""
    mock_gui.GetWindowRect.return_value = (0, 0, 1920, 1080)
    mock_gui.GetWindowPlacement.return_value = (
        0,
        win32con.SW_SHOWMAXIMIZED,
        (0, 0),
        (0, 0),
        (0, 0, 1920, 1080),
    )
    info: WindowInfo = build_window_info(50, "Maximized")
    assert info["minimized"] is False
    assert info["maximized"] is True
    assert info["width"] == 1920
    assert info["height"] == 1080


# ---------------------------------------------------------------------------
# list_windows
# ---------------------------------------------------------------------------


def _setup_enum_mock(
    mock_gui: MagicMock,
    windows: dict[int, str],
    *,
    foreground_hwnd: int = 1,
    rect: tuple[int, int, int, int] = (0, 0, 100, 100),
) -> None:
    """Configure mock_gui for EnumWindows-based tests (list_windows, etc.)."""
    mock_gui.GetForegroundWindow.return_value = foreground_hwnd
    mock_gui.IsWindowVisible.return_value = True

    def _get_text(hwnd: int) -> str:
        """Return window title for the given hwnd."""
        return windows[hwnd]

    mock_gui.GetWindowText.side_effect = _get_text
    mock_gui.GetWindowRect.return_value = rect
    mock_gui.GetWindowPlacement.return_value = (
        0,
        win32con.SW_SHOW,
        (0, 0),
        (0, 0),
        rect,
    )

    def _fake_enum(
        callback: Callable[[int, list[Any]], object], ctx: list[Any]
    ) -> None:
        """Simulate EnumWindows by iterating over the test windows dict."""
        for hwnd in windows:
            callback(hwnd, ctx)

    mock_gui.EnumWindows.side_effect = _fake_enum


@patch("winsight_mcp.window_manager.win32gui")
def test_list_windows_with_results(mock_gui: MagicMock) -> None:
    """Returns all visible windows with correct active flag."""
    _setup_enum_mock(mock_gui, {1: "Window A", 2: "Window B"})

    result: list[WindowListEntry] = list_windows()
    assert len(result) == 2
    assert result[0]["title"] == "Window A"
    assert result[0]["active"] is True
    assert result[1]["title"] == "Window B"
    assert result[1]["active"] is False


@patch("winsight_mcp.window_manager.win32gui")
def test_list_windows_with_filter(mock_gui: MagicMock) -> None:
    """Filter returns only windows matching the substring."""
    _setup_enum_mock(mock_gui, {1: "Notepad", 2: "Chrome"})

    result: list[WindowListEntry] = list_windows("note")
    assert len(result) == 1
    assert result[0]["title"] == "Notepad"


@patch("winsight_mcp.window_manager.win32gui")
def test_list_windows_empty_string_filter(mock_gui: MagicMock) -> None:
    """Empty string filter behaves like None (no filtering)."""
    _setup_enum_mock(mock_gui, {1: "Notepad", 2: "Chrome"})

    result: list[WindowListEntry] = list_windows("")
    assert len(result) == 2


@patch("winsight_mcp.window_manager.win32gui")
def test_list_windows_all_invisible(mock_gui: MagicMock) -> None:
    """Returns empty list when all enumerated windows are invisible."""
    _setup_enum_mock(mock_gui, {1: "Hidden", 2: "Also Hidden"})
    mock_gui.IsWindowVisible.return_value = False

    result: list[WindowListEntry] = list_windows()
    assert result == []


# ---------------------------------------------------------------------------
# find_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
def test_find_window_found(mock_gui: MagicMock) -> None:
    """First matching window is returned with correct hwnd and title."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "My Notepad"
    mock_gui.GetWindowRect.return_value = (0, 0, 800, 600)
    mock_gui.GetWindowPlacement.return_value = (0, 0, (0, 0), (0, 0), (0, 0, 800, 600))
    mock_gui.EnumWindows.side_effect = _enum_single(10)

    result: WindowInfo | None = find_window("notepad")
    assert result is not None
    assert result["title"] == "My Notepad"
    assert result["hwnd"] == 10


@patch("winsight_mcp.window_manager.win32gui")
def test_find_window_not_found(mock_gui: MagicMock) -> None:
    """Returns None when no window matches the title."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "Chrome"
    mock_gui.EnumWindows.side_effect = _enum_single(10)

    result: WindowInfo | None = find_window("notepad")
    assert result is None


@patch("winsight_mcp.window_manager.win32gui")
def test_find_window_stops_after_first_match(mock_gui: MagicMock) -> None:
    """The ``if ctx:`` guard prevents processing hwnds after first match."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "Notepad"
    mock_gui.GetWindowRect.return_value = (0, 0, 800, 600)
    mock_gui.GetWindowPlacement.return_value = (0, 0, (0, 0), (0, 0), (0, 0, 800, 600))

    def _fake_enum(
        callback: Callable[[int, list[Any]], object], ctx: list[Any]
    ) -> None:
        """Enumerate 3 hwnds to verify early-exit after first match."""
        callback(10, ctx)  # Match -> appended to ctx, returns False
        callback(20, ctx)  # ctx is truthy -> guard returns False immediately
        callback(30, ctx)  # same

    mock_gui.EnumWindows.side_effect = _fake_enum

    result: WindowInfo | None = find_window("notepad")
    assert result is not None
    assert result["hwnd"] == 10
    assert mock_gui.IsWindowVisible.call_count == 1


@patch("winsight_mcp.window_manager.win32gui")
def test_find_window_enum_exception_swallowed(mock_gui: MagicMock) -> None:
    """EnumWindows exception is silently caught; find_window returns None."""
    mock_gui.EnumWindows.side_effect = OSError("EnumWindows failed")

    result: WindowInfo | None = find_window("anything")
    assert result is None


@patch("winsight_mcp.window_manager.win32gui")
def test_find_window_exception_after_match(mock_gui: MagicMock) -> None:
    """Win32 EnumWindows raises when callback returns False; result is still returned."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "Notepad"
    mock_gui.GetWindowRect.return_value = (0, 0, 800, 600)
    mock_gui.GetWindowPlacement.return_value = (0, 0, (0, 0), (0, 0), (0, 0, 800, 600))

    def _fake_enum(
        callback: Callable[[int, list[Any]], object], ctx: list[Any]
    ) -> None:
        """Enumerate one hwnd then raise to simulate early enumeration stop."""
        callback(10, ctx)
        raise OSError("pywintypes.error: enumeration stopped")

    mock_gui.EnumWindows.side_effect = _fake_enum

    result: WindowInfo | None = find_window("notepad")
    assert result is not None
    assert result["hwnd"] == 10


# ---------------------------------------------------------------------------
# get_window_info (unit-level, not via server)
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
def test_get_window_info_found(mock_gui: MagicMock) -> None:
    """Returns PublicWindowInfo without hwnd and with active flag."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "My Editor"
    mock_gui.GetWindowRect.return_value = (10, 20, 810, 620)
    mock_gui.GetWindowPlacement.return_value = (
        0,
        win32con.SW_SHOW,
        (0, 0),
        (0, 0),
        (10, 20, 810, 620),
    )
    mock_gui.GetForegroundWindow.return_value = 42
    mock_gui.EnumWindows.side_effect = _enum_single(42)

    info: PublicWindowInfo | None = get_window_info("editor")
    assert info is not None
    assert info["title"] == "My Editor"
    assert info["active"] is True
    assert "hwnd" not in info  # PublicWindowInfo excludes hwnd


@patch("winsight_mcp.window_manager.win32gui")
def test_get_window_info_not_found(mock_gui: MagicMock) -> None:
    """Returns None when no window matches."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "Chrome"
    mock_gui.EnumWindows.side_effect = _enum_single(1)

    info: PublicWindowInfo | None = get_window_info("notepad")
    assert info is None


# ---------------------------------------------------------------------------
# get_window_rect (unit-level)
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
def test_get_window_rect_found(mock_gui: MagicMock) -> None:
    """Returns (left, top, width, height) tuple for a matching window."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "My App"
    mock_gui.GetWindowRect.return_value = (50, 100, 850, 700)
    mock_gui.GetWindowPlacement.return_value = (
        0,
        0,
        (0, 0),
        (0, 0),
        (50, 100, 850, 700),
    )
    mock_gui.EnumWindows.side_effect = _enum_single(1)

    rect: tuple[int, int, int, int] | None = get_window_rect("app")
    assert rect == (50, 100, 800, 600)


@patch("winsight_mcp.window_manager.win32gui")
def test_get_window_rect_not_found(mock_gui: MagicMock) -> None:
    """Returns None when no window matches."""
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "Chrome"
    mock_gui.EnumWindows.side_effect = _enum_single(1)

    assert get_window_rect("notepad") is None


# ---------------------------------------------------------------------------
# force_foreground
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.ctypes")
@patch("winsight_mcp.window_manager.win32gui")
def testforce_foreground_attaches_threads(
    mock_gui: MagicMock, mock_ctypes: MagicMock
) -> None:
    """When current and foreground threads differ, AttachThreadInput is called."""
    mock_gui.GetForegroundWindow.return_value = 99
    mock_ctypes.windll.kernel32.GetCurrentThreadId.return_value = 100
    mock_ctypes.windll.user32.GetWindowThreadProcessId.return_value = 200

    force_foreground(42)

    mock_ctypes.windll.user32.AttachThreadInput.assert_any_call(100, 200, True)
    mock_ctypes.windll.user32.AttachThreadInput.assert_any_call(100, 200, False)
    mock_gui.BringWindowToTop.assert_called_once_with(42)
    mock_gui.SetForegroundWindow.assert_called_once_with(42)


@patch("winsight_mcp.window_manager.ctypes")
@patch("winsight_mcp.window_manager.win32gui")
def testforce_foreground_same_thread_skips_attach(
    mock_gui: MagicMock, mock_ctypes: MagicMock
) -> None:
    """When current and foreground threads are the same, skip AttachThreadInput."""
    mock_gui.GetForegroundWindow.return_value = 99
    mock_ctypes.windll.kernel32.GetCurrentThreadId.return_value = 100
    mock_ctypes.windll.user32.GetWindowThreadProcessId.return_value = 100

    force_foreground(42)

    mock_ctypes.windll.user32.AttachThreadInput.assert_not_called()
    mock_gui.BringWindowToTop.assert_called_once_with(42)


@patch("winsight_mcp.window_manager.ctypes")
@patch("winsight_mcp.window_manager.win32gui")
def testforce_foreground_detaches_on_exception(
    mock_gui: MagicMock, mock_ctypes: MagicMock
) -> None:
    """Thread input is detached even when BringWindowToTop raises."""
    mock_gui.GetForegroundWindow.return_value = 99
    mock_ctypes.windll.kernel32.GetCurrentThreadId.return_value = 100
    mock_ctypes.windll.user32.GetWindowThreadProcessId.return_value = 200
    mock_gui.BringWindowToTop.side_effect = OSError("Access denied")

    with pytest.raises(OSError, match="Access denied"):
        force_foreground(42)

    mock_ctypes.windll.user32.AttachThreadInput.assert_any_call(100, 200, True)
    mock_ctypes.windll.user32.AttachThreadInput.assert_any_call(100, 200, False)


# ---------------------------------------------------------------------------
# focus_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.force_foreground")
@patch("winsight_mcp.window_manager.find_window")
def test_focus_window_success(
    mock_find: MagicMock,
    mock_force: MagicMock,
    mock_gui: MagicMock,
    sample_window_info: WindowInfo,
) -> None:
    """Non-minimized window is focused without calling ShowWindow."""
    mock_find.return_value = sample_window_info
    result: str = focus_window("test")
    assert "now focused" in result
    mock_force.assert_called_once_with(sample_window_info["hwnd"])
    mock_gui.ShowWindow.assert_not_called()


@patch("winsight_mcp.window_manager.find_window")
def test_focus_window_not_found(mock_find: MagicMock) -> None:
    """Returns 'not found' message when window does not exist."""
    mock_find.return_value = None
    result: str = focus_window("nonexistent")
    assert "No window found" in result


@patch("winsight_mcp.window_manager.time")
@patch("winsight_mcp.window_manager.force_foreground")
@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_focus_window_restores_minimized(
    mock_find: MagicMock,
    mock_gui: MagicMock,
    mock_force: MagicMock,
    mock_time: MagicMock,
    sample_window_info: WindowInfo,
) -> None:
    """Minimized window triggers ShowWindow(SW_RESTORE) + sleep before focus."""
    info: WindowInfo = {
        "title": sample_window_info["title"],
        "hwnd": sample_window_info["hwnd"],
        "left": sample_window_info["left"],
        "top": sample_window_info["top"],
        "width": sample_window_info["width"],
        "height": sample_window_info["height"],
        "minimized": True,
        "maximized": sample_window_info["maximized"],
    }
    mock_find.return_value = info
    result: str = focus_window("minimized")
    assert "now focused" in result
    mock_gui.ShowWindow.assert_called_once_with(info["hwnd"], win32con.SW_RESTORE)
    mock_time.sleep.assert_called_once_with(0.3)
    mock_force.assert_called_once_with(info["hwnd"])


@patch("winsight_mcp.window_manager.force_foreground")
@patch("winsight_mcp.window_manager.find_window")
def test_focus_window_exception(
    mock_find: MagicMock, mock_force: MagicMock, sample_window_info: WindowInfo
) -> None:
    """Exception in force_foreground is caught and returns failure message."""
    mock_find.return_value = sample_window_info
    mock_force.side_effect = OSError("Access denied")
    result: str = focus_window("broken")
    assert "Failed to focus" in result
    assert "Access denied" in result


# ---------------------------------------------------------------------------
# resize_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_resize_window_success(
    mock_find: MagicMock, mock_gui: MagicMock, sample_window_info: WindowInfo
) -> None:
    """Calls SetWindowPos with SWP_NOMOVE to resize only."""
    mock_find.return_value = sample_window_info
    result: str = resize_window("test", 1024, 768)
    assert "resized to 1024x768" in result
    mock_gui.SetWindowPos.assert_called_once_with(
        sample_window_info["hwnd"],
        win32con.HWND_TOP,
        0,
        0,
        1024,
        768,
        win32con.SWP_NOMOVE | win32con.SWP_NOZORDER,
    )


@patch("winsight_mcp.window_manager.find_window")
def test_resize_window_not_found(mock_find: MagicMock) -> None:
    """Returns 'not found' when window does not exist."""
    mock_find.return_value = None
    result: str = resize_window("nonexistent", 1024, 768)
    assert "No window found" in result


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_resize_window_exception(
    mock_find: MagicMock, mock_gui: MagicMock, sample_window_info: WindowInfo
) -> None:
    """SetWindowPos exception is caught and returns failure message."""
    mock_find.return_value = sample_window_info
    mock_gui.SetWindowPos.side_effect = OSError("Access denied")
    result: str = resize_window("test", 1024, 768)
    assert "Failed to resize" in result
    assert "Access denied" in result


# ---------------------------------------------------------------------------
# move_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_move_window_success(
    mock_find: MagicMock, mock_gui: MagicMock, sample_window_info: WindowInfo
) -> None:
    """Calls SetWindowPos with SWP_NOSIZE to move only."""
    mock_find.return_value = sample_window_info
    result: str = move_window("test", 50, 100)
    assert "moved to (50, 100)" in result
    mock_gui.SetWindowPos.assert_called_once_with(
        sample_window_info["hwnd"],
        win32con.HWND_TOP,
        50,
        100,
        0,
        0,
        win32con.SWP_NOSIZE | win32con.SWP_NOZORDER,
    )


@patch("winsight_mcp.window_manager.find_window")
def test_move_window_not_found(mock_find: MagicMock) -> None:
    """Returns 'not found' when window does not exist."""
    mock_find.return_value = None
    result: str = move_window("nonexistent", 50, 100)
    assert "No window found" in result


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_move_window_exception(
    mock_find: MagicMock, mock_gui: MagicMock, sample_window_info: WindowInfo
) -> None:
    """SetWindowPos exception is caught and returns failure message."""
    mock_find.return_value = sample_window_info
    mock_gui.SetWindowPos.side_effect = OSError("Access denied")
    result: str = move_window("test", 50, 100)
    assert "Failed to move" in result
    assert "Access denied" in result


# ---------------------------------------------------------------------------
# minimize_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_minimize_window_success(
    mock_find: MagicMock, mock_gui: MagicMock, sample_window_info: WindowInfo
) -> None:
    """Calls ShowWindow with SW_MINIMIZE."""
    mock_find.return_value = sample_window_info
    result: str = minimize_window("test")
    assert "minimized" in result
    mock_gui.ShowWindow.assert_called_once_with(
        sample_window_info["hwnd"], win32con.SW_MINIMIZE
    )


@patch("winsight_mcp.window_manager.find_window")
def test_minimize_window_not_found(mock_find: MagicMock) -> None:
    """Returns 'not found' when window does not exist."""
    mock_find.return_value = None
    result: str = minimize_window("nonexistent")
    assert "No window found" in result


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_minimize_window_exception(
    mock_find: MagicMock, mock_gui: MagicMock, sample_window_info: WindowInfo
) -> None:
    """ShowWindow exception is caught and returns failure message."""
    mock_find.return_value = sample_window_info
    mock_gui.ShowWindow.side_effect = OSError("Access denied")
    result: str = minimize_window("test")
    assert "Failed to minimize" in result
    assert "Access denied" in result


# ---------------------------------------------------------------------------
# maximize_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_maximize_window_success(
    mock_find: MagicMock, mock_gui: MagicMock, sample_window_info: WindowInfo
) -> None:
    """Calls ShowWindow with SW_MAXIMIZE."""
    mock_find.return_value = sample_window_info
    result: str = maximize_window("test")
    assert "maximized" in result
    mock_gui.ShowWindow.assert_called_once_with(
        sample_window_info["hwnd"], win32con.SW_MAXIMIZE
    )


@patch("winsight_mcp.window_manager.find_window")
def test_maximize_window_not_found(mock_find: MagicMock) -> None:
    """Returns 'not found' when window does not exist."""
    mock_find.return_value = None
    result: str = maximize_window("nonexistent")
    assert "No window found" in result


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_maximize_window_exception(
    mock_find: MagicMock, mock_gui: MagicMock, sample_window_info: WindowInfo
) -> None:
    """ShowWindow exception is caught and returns failure message."""
    mock_find.return_value = sample_window_info
    mock_gui.ShowWindow.side_effect = OSError("Access denied")
    result: str = maximize_window("test")
    assert "Failed to maximize" in result
    assert "Access denied" in result


# ---------------------------------------------------------------------------
# restore_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_restore_window_success(
    mock_find: MagicMock, mock_gui: MagicMock, sample_window_info: WindowInfo
) -> None:
    """Calls ShowWindow with SW_RESTORE."""
    mock_find.return_value = sample_window_info
    result: str = restore_window("test")
    assert "restored" in result
    mock_gui.ShowWindow.assert_called_once_with(
        sample_window_info["hwnd"], win32con.SW_RESTORE
    )


@patch("winsight_mcp.window_manager.find_window")
def test_restore_window_not_found(mock_find: MagicMock) -> None:
    """Returns 'not found' when window does not exist."""
    mock_find.return_value = None
    result: str = restore_window("nonexistent")
    assert "No window found" in result


@patch("winsight_mcp.window_manager.win32gui")
@patch("winsight_mcp.window_manager.find_window")
def test_restore_window_exception(
    mock_find: MagicMock, mock_gui: MagicMock, sample_window_info: WindowInfo
) -> None:
    """ShowWindow exception is caught and returns failure message."""
    mock_find.return_value = sample_window_info
    mock_gui.ShowWindow.side_effect = OSError("Access denied")
    result: str = restore_window("test")
    assert "Failed to restore" in result
    assert "Access denied" in result


# ---------------------------------------------------------------------------
# wait_for_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.window_manager.time")
@patch("winsight_mcp.window_manager.find_window")
def test_wait_for_window_found_immediately(
    mock_find: MagicMock, mock_time: MagicMock, sample_window_info: WindowInfo
) -> None:
    """Window exists on first poll."""
    mock_time.time.side_effect = [0.0, 0.0]  # start, first check
    mock_find.return_value = sample_window_info
    result: str = wait_for_window("test")
    assert "Window found" in result
    assert "Test Window" in result
    mock_time.sleep.assert_not_called()


@patch("winsight_mcp.window_manager.time")
@patch("winsight_mcp.window_manager.find_window")
def test_wait_for_window_found_after_retries(
    mock_find: MagicMock, mock_time: MagicMock, sample_window_info: WindowInfo
) -> None:
    """Window appears after a few polling iterations."""
    mock_time.time.side_effect = [0.0, 1.0, 1.0, 2.0, 2.0]
    mock_find.side_effect = [None, sample_window_info]
    result: str = wait_for_window("test", timeout=10)
    assert "Window found" in result
    mock_time.sleep.assert_called_with(0.2)  # elapsed < 5 so 0.2s interval


@patch("winsight_mcp.window_manager.time")
@patch("winsight_mcp.window_manager.find_window")
def test_wait_for_window_timeout(mock_find: MagicMock, mock_time: MagicMock) -> None:
    """Window never appears; function times out."""
    mock_time.time.side_effect = [0.0, 1.0, 1.0, 31.0]
    mock_find.return_value = None
    result: str = wait_for_window("nonexistent", timeout=30)
    assert "Timed out" in result
    assert "nonexistent" in result


@patch("winsight_mcp.window_manager.time")
@patch("winsight_mcp.window_manager.find_window")
def test_wait_for_window_adaptive_polling(
    mock_find: MagicMock, mock_time: MagicMock
) -> None:
    """After 5 seconds elapsed, polling switches from 0.2s to 0.5s."""
    mock_time.time.side_effect = [0.0, 1.0, 1.0, 6.0, 6.0, 31.0]
    mock_find.return_value = None
    result: str = wait_for_window("nonexistent", timeout=30)
    assert "Timed out" in result
    sleep_calls = mock_time.sleep.call_args_list
    assert call(0.2) in sleep_calls
    assert call(0.5) in sleep_calls
