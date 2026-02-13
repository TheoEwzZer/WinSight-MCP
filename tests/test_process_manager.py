"""Tests for winsight_mcp.process_manager."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from winsight_mcp.process_manager import (
    poll_for_window,
    open_application,
)
from winsight_mcp.types import ProcessResult, WindowInfo


# ---------------------------------------------------------------------------
# open_application
# ---------------------------------------------------------------------------


@patch("winsight_mcp.process_manager.subprocess.Popen")
def test_open_application_success_no_wait(mock_popen: MagicMock) -> None:
    """Successful launch without waiting returns pid, command, and correct Popen kwargs."""
    mock_proc = MagicMock()
    mock_proc.pid = 1234
    mock_popen.return_value = mock_proc

    result: ProcessResult = open_application("notepad.exe")
    assert result.get("pid") == 1234
    assert result.get("command") == "notepad.exe"
    assert "error" not in result
    cmd_passed = mock_popen.call_args[0][0]
    assert cmd_passed == ["notepad.exe"]
    _, kwargs = mock_popen.call_args
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.PIPE
    assert kwargs["creationflags"] == subprocess.CREATE_NEW_PROCESS_GROUP


@patch("winsight_mcp.process_manager.subprocess.Popen")
def test_open_application_empty_args_list(mock_popen: MagicMock) -> None:
    """Empty args list (falsy) results in command-only list."""
    mock_proc = MagicMock()
    mock_proc.pid = 1111
    mock_popen.return_value = mock_proc

    open_application("notepad.exe", args=[])

    cmd_passed = mock_popen.call_args[0][0]
    assert cmd_passed == ["notepad.exe"]


@patch("winsight_mcp.process_manager.subprocess.Popen")
def test_open_application_with_args(mock_popen: MagicMock) -> None:
    """Arguments are correctly concatenated into the command list."""
    mock_proc = MagicMock()
    mock_proc.pid = 4321
    mock_popen.return_value = mock_proc

    open_application("cmd.exe", args=["/c", "echo test"])

    cmd_passed = mock_popen.call_args[0][0]
    assert cmd_passed == ["cmd.exe", "/c", "echo test"]


@patch("winsight_mcp.process_manager.subprocess.Popen")
def test_open_application_command_not_found(mock_popen: MagicMock) -> None:
    """FileNotFoundError produces an error dict with 'Command not found'."""
    mock_popen.side_effect = FileNotFoundError()

    result: ProcessResult = open_application("nonexistent")
    assert "error" in result
    assert "Command not found" in result["error"]


@patch("winsight_mcp.process_manager.subprocess.Popen")
def test_open_application_generic_error(mock_popen: MagicMock) -> None:
    """OSError produces an error dict with 'Failed to launch'."""
    mock_popen.side_effect = OSError("Permission denied")

    result: ProcessResult = open_application("forbidden.exe")
    assert "error" in result
    assert "Failed to launch" in result["error"]


@patch("winsight_mcp.process_manager.poll_for_window")
@patch("winsight_mcp.process_manager.subprocess.Popen")
def test_open_application_window_found(
    mock_popen: MagicMock,
    mock_wait: MagicMock,
    sample_window_info: WindowInfo,
) -> None:
    """When wait_for_window finds the window, result includes window info."""
    mock_proc = MagicMock()
    mock_proc.pid = 5678
    mock_popen.return_value = mock_proc
    mock_wait.return_value = sample_window_info

    result: ProcessResult = open_application("notepad.exe", wait_for_window="Notepad")
    assert result.get("pid") == 5678
    assert "window" in result
    assert result["window"]["title"] == "Test Window"


@patch("winsight_mcp.process_manager.poll_for_window")
@patch("winsight_mcp.process_manager.subprocess.Popen")
def test_open_application_window_timeout(
    mock_popen: MagicMock, mock_wait: MagicMock
) -> None:
    """When wait_for_window times out, result includes a warning."""
    mock_proc = MagicMock()
    mock_proc.pid = 9999
    mock_popen.return_value = mock_proc
    mock_wait.return_value = None

    result: ProcessResult = open_application(
        "notepad.exe", wait_for_window="Notepad", timeout=1
    )
    assert "window_warning" in result
    assert "not found" in result["window_warning"]


# ---------------------------------------------------------------------------
# poll_for_window
# ---------------------------------------------------------------------------


@patch("winsight_mcp.process_manager.time")
@patch("winsight_mcp.process_manager.find_window")
def testpoll_for_window_poll_then_find(
    mock_find: MagicMock,
    mock_time: MagicMock,
    sample_window_info: WindowInfo,
) -> None:
    """Polls multiple times before finding the window."""
    mock_find.side_effect = [None, None, sample_window_info]
    mock_time.time.side_effect = [0, 1, 2, 3, 4, 5]
    mock_time.sleep = MagicMock()

    result: WindowInfo | None = poll_for_window("Test", timeout=10)
    assert result is not None
    assert result["title"] == "Test Window"
    assert mock_time.sleep.call_count == 2


@patch("winsight_mcp.process_manager.time")
@patch("winsight_mcp.process_manager.find_window")
def testpoll_for_window_adaptive_sleep(
    mock_find: MagicMock,
    mock_time: MagicMock,
    sample_window_info: WindowInfo,
) -> None:
    """Sleep interval switches from 0.2s to 0.5s after 5 seconds elapsed."""
    mock_find.side_effect = [None, None, sample_window_info]
    mock_time.time.side_effect = [0, 2, 3, 6, 7, 8]
    mock_time.sleep = MagicMock()

    poll_for_window("Test", timeout=20)

    mock_time.sleep.assert_any_call(0.2)
    mock_time.sleep.assert_any_call(0.5)


@patch("winsight_mcp.process_manager.time")
@patch("winsight_mcp.process_manager.find_window")
def testpoll_for_window_timeout_returns_none(
    mock_find: MagicMock,
    mock_time: MagicMock,
) -> None:
    """Returns None when timeout expires without finding the window."""
    mock_find.return_value = None
    mock_time.time.side_effect = [0, 5, 6, 11]
    mock_time.sleep = MagicMock()

    result: WindowInfo | None = poll_for_window("Ghost", timeout=10)
    assert result is None
    assert mock_find.call_count == 1
