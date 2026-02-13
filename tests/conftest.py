"""Shared fixtures and Win32 stubs for cross-platform testing."""

from __future__ import annotations

import ctypes
import subprocess
import sys
from io import BytesIO
from unittest.mock import MagicMock

from PIL import Image as PILImage

_mock_win32con = MagicMock()
_mock_win32con.SW_SHOWMINIMIZED = 2
_mock_win32con.SW_SHOWMAXIMIZED = 3
_mock_win32con.SW_RESTORE = 9
_mock_win32con.SW_SHOW = 5
_mock_win32con.SW_MINIMIZE = 6
_mock_win32con.SW_MAXIMIZE = 3
_mock_win32con.SWP_NOMOVE = 0x0002
_mock_win32con.SWP_NOSIZE = 0x0001
_mock_win32con.SWP_NOZORDER = 0x0004
_mock_win32con.HWND_TOP = 0

sys.modules.setdefault("win32gui", MagicMock())
sys.modules.setdefault("win32ui", MagicMock())
sys.modules.setdefault("win32con", _mock_win32con)

if not hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
    subprocess.CREATE_NEW_PROCESS_GROUP = 0x00000200

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()

# ---------------------------------------------------------------------------

from mcp.server.fastmcp.server import FastMCP
import pytest

from winsight_mcp.server import mcp as _mcp_instance
from winsight_mcp.types import WindowInfo


@pytest.fixture
def sample_window_info() -> WindowInfo:
    """Reusable WindowInfo dict for tests."""
    return {
        "title": "Test Window",
        "hwnd": 12345,
        "left": 100,
        "top": 200,
        "width": 800,
        "height": 600,
        "minimized": False,
        "maximized": False,
    }


@pytest.fixture
def mcp_server() -> FastMCP:
    """Return the FastMCP server instance."""
    return _mcp_instance


@pytest.fixture
def fake_png_bytes() -> bytes:
    """Minimal valid PNG bytes."""
    img: PILImage.Image = PILImage.new("RGB", (10, 10))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
