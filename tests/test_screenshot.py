"""Tests for winsight_mcp.screenshot."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image as PILImage

from winsight_mcp.screenshot import (
    capture_full_screen,
    capture_region,
    capture_window_hwnd,
    list_monitors,
)
from winsight_mcp.types import MonitorInfo

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_DUAL_MONITORS: list[dict[str, int]] = [
    {"left": 0, "top": 0, "width": 1920, "height": 1080},
    {"left": 0, "top": 0, "width": 1920, "height": 1080},
]


def _setup_mss_mock(
    mock_mss_cls: MagicMock,
    monitors: list[dict[str, int]] | None = None,
) -> MagicMock:
    """Wire up the mss context-manager mock and return the inner sct object."""
    mock_sct = MagicMock()
    mock_mss_cls.return_value.__enter__ = MagicMock(return_value=mock_sct)
    mock_mss_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_sct.monitors = monitors if monitors is not None else list(_DUAL_MONITORS)
    return mock_sct


# ---------------------------------------------------------------------------
# capture_full_screen
# ---------------------------------------------------------------------------


@patch("winsight_mcp.screenshot.mss.mss")
def test_capture_full_screen_default_monitor(mock_mss_cls: MagicMock) -> None:
    """Captures monitor 1 and returns valid PNG bytes."""
    mock_sct: MagicMock = _setup_mss_mock(mock_mss_cls)
    mock_screenshot = MagicMock()
    mock_screenshot.size = (1920, 1080)
    mock_screenshot.bgra = b"\x00" * (1920 * 1080 * 4)
    mock_sct.grab.return_value = mock_screenshot

    result: bytes = capture_full_screen(1)
    assert result[:8] == PNG_MAGIC
    mock_sct.grab.assert_called_once_with(mock_sct.monitors[1])


@patch("winsight_mcp.screenshot.mss.mss")
def test_capture_full_screen_invalid_monitor(mock_mss_cls: MagicMock) -> None:
    """Out-of-range monitor index raises ValueError."""
    _setup_mss_mock(mock_mss_cls)

    with pytest.raises(ValueError, match="Monitor 5 not found"):
        capture_full_screen(5)


@patch("winsight_mcp.screenshot.mss.mss")
def test_capture_full_screen_negative_monitor(mock_mss_cls: MagicMock) -> None:
    """Negative monitor index raises ValueError."""
    _setup_mss_mock(mock_mss_cls)

    with pytest.raises(ValueError, match="Monitor -1 not found"):
        capture_full_screen(-1)


@patch("winsight_mcp.screenshot.mss.mss")
def test_capture_full_screen_single_monitor(mock_mss_cls: MagicMock) -> None:
    """With only the combined monitor (index 0), index 1 raises ValueError."""
    _setup_mss_mock(
        mock_mss_cls,
        monitors=[
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
        ],
    )

    with pytest.raises(ValueError, match="Monitor 1 not found"):
        capture_full_screen(1)


@patch("winsight_mcp.screenshot.mss.mss")
def test_capture_full_screen_all_monitors(mock_mss_cls: MagicMock) -> None:
    """Monitor index 0 captures the combined virtual screen."""
    mock_sct: MagicMock = _setup_mss_mock(
        mock_mss_cls,
        monitors=[
            {"left": 0, "top": 0, "width": 3840, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
        ],
    )
    mock_screenshot = MagicMock()
    mock_screenshot.size = (3840, 1080)
    mock_screenshot.bgra = b"\x00" * (3840 * 1080 * 4)
    mock_sct.grab.return_value = mock_screenshot

    result: bytes = capture_full_screen(0)
    assert result[:8] == PNG_MAGIC
    mock_sct.grab.assert_called_once_with(mock_sct.monitors[0])


# ---------------------------------------------------------------------------
# capture_region
# ---------------------------------------------------------------------------


@patch("winsight_mcp.screenshot.ImageGrab.grab")
def test_capture_region(mock_grab: MagicMock) -> None:
    """Captures a region and returns valid PNG bytes with correct bbox."""
    mock_grab.return_value = PILImage.new("RGB", (100, 50))

    result: bytes = capture_region(10, 20, 100, 50)
    assert result[:8] == PNG_MAGIC
    mock_grab.assert_called_once_with(bbox=(10, 20, 110, 70))


@patch("winsight_mcp.screenshot.ImageGrab.grab")
def test_capture_region_passes_negative_coords(mock_grab: MagicMock) -> None:
    """Negative x/y are forwarded to ImageGrab.grab unchanged."""
    mock_grab.return_value = PILImage.new("RGB", (50, 50))

    capture_region(-10, -20, 50, 50)
    mock_grab.assert_called_once_with(bbox=(-10, -20, 40, 30))


@patch("winsight_mcp.screenshot.ImageGrab.grab")
def test_capture_region_grab_exception(mock_grab: MagicMock) -> None:
    """Exception from ImageGrab.grab propagates to caller."""
    mock_grab.side_effect = OSError("grab failed")

    with pytest.raises(OSError, match="grab failed"):
        capture_region(0, 0, 100, 100)


# ---------------------------------------------------------------------------
# capture_window_hwnd
# ---------------------------------------------------------------------------


def _setup_hwnd_mocks(
    mock_win32gui: MagicMock,
    mock_win32ui: MagicMock,
    width: int = 100,
    height: int = 80,
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Configure mocks for the full Win32 DC/bitmap chain."""
    mock_win32gui.GetWindowRect.return_value = (0, 0, width, height)
    mock_win32gui.GetWindowDC.return_value = 1

    mock_mfc_dc = MagicMock()
    mock_save_dc = MagicMock()
    mock_bitmap = MagicMock()
    mock_win32ui.CreateDCFromHandle.return_value = mock_mfc_dc
    mock_mfc_dc.CreateCompatibleDC.return_value = mock_save_dc
    mock_win32ui.CreateBitmap.return_value = mock_bitmap

    mock_bitmap.GetInfo.return_value = {
        "bmType": 0,
        "bmWidth": width,
        "bmHeight": height,
        "bmWidthBytes": width * 4,
        "bmPlanes": 1,
        "bmBitsPixel": 32,
    }
    mock_bitmap.GetBitmapBits.return_value = b"\x00" * (width * height * 4)
    return mock_mfc_dc, mock_save_dc, mock_bitmap


@patch("winsight_mcp.screenshot.ctypes")
@patch("winsight_mcp.screenshot.win32ui")
@patch("winsight_mcp.screenshot.win32gui")
def test_capture_window_hwnd_success(
    mock_win32gui: MagicMock,
    mock_win32ui: MagicMock,
    mock_ctypes: MagicMock,
) -> None:
    """Captures window content via PrintWindow and returns valid PNG."""
    _, mock_save_dc, _ = _setup_hwnd_mocks(mock_win32gui, mock_win32ui)

    result: bytes = capture_window_hwnd(42)
    assert result[:8] == PNG_MAGIC
    mock_win32gui.GetWindowDC.assert_called_once_with(42)
    mock_ctypes.windll.user32.PrintWindow.assert_called_once_with(
        42, mock_save_dc.GetSafeHdc(), 2
    )


@patch("winsight_mcp.screenshot.ctypes")
@patch("winsight_mcp.screenshot.win32ui")
@patch("winsight_mcp.screenshot.win32gui")
def test_capture_window_hwnd_cleans_up_resources(
    mock_win32gui: MagicMock,
    mock_win32ui: MagicMock,
    _mock_ctypes: MagicMock,
) -> None:
    """All Win32 resources (DC, bitmap) are properly released after capture."""
    mock_mfc_dc, mock_save_dc, mock_bitmap = _setup_hwnd_mocks(
        mock_win32gui, mock_win32ui
    )

    capture_window_hwnd(42)

    mock_win32gui.DeleteObject.assert_called_once_with(mock_bitmap.GetHandle())
    mock_save_dc.DeleteDC.assert_called_once()
    mock_mfc_dc.DeleteDC.assert_called_once()
    mock_win32gui.ReleaseDC.assert_called_once_with(42, 1)


@patch("winsight_mcp.screenshot.ctypes")
@patch("winsight_mcp.screenshot.win32ui")
@patch("winsight_mcp.screenshot.win32gui")
def test_capture_window_hwnd_cleanup_on_exception(
    mock_win32gui: MagicMock,
    mock_win32ui: MagicMock,
    _mock_ctypes: MagicMock,
) -> None:
    """Win32 resources are released even when PIL conversion raises."""
    mock_mfc_dc, mock_save_dc, mock_bitmap = _setup_hwnd_mocks(
        mock_win32gui, mock_win32ui
    )
    mock_bitmap.GetBitmapBits.return_value = b""

    with pytest.raises(ValueError, match="not enough image data"):
        capture_window_hwnd(42)

    mock_win32gui.DeleteObject.assert_called_once()
    mock_save_dc.DeleteDC.assert_called_once()
    mock_mfc_dc.DeleteDC.assert_called_once()
    mock_win32gui.ReleaseDC.assert_called_once_with(42, 1)


@pytest.mark.parametrize(
    "rect",
    [
        (0, 0, 0, 0),  # both zero
        (0, 0, 100, 0),  # height zero, width valid
        (0, 0, 0, 100),  # width zero, height valid
        (10, 10, 5, 10),  # negative width (right < left)
    ],
    ids=["both_zero", "height_zero", "width_zero", "negative_width"],
)
@patch("winsight_mcp.screenshot.win32gui")
def test_capture_window_hwnd_invalid_dimensions(
    mock_win32gui: MagicMock, rect: tuple[int, int, int, int]
) -> None:
    """Invalid window dimensions (zero or negative) raise ValueError."""
    mock_win32gui.GetWindowRect.return_value = rect
    with pytest.raises(ValueError, match="invalid dimensions"):
        capture_window_hwnd(42)


# ---------------------------------------------------------------------------
# list_monitors
# ---------------------------------------------------------------------------


@patch("winsight_mcp.screenshot.mss.mss")
def test_list_monitors_dual_setup(mock_mss_cls: MagicMock) -> None:
    """Two real monitors are returned with correct info; index 0 (combined) is skipped."""
    _setup_mss_mock(
        mock_mss_cls,
        monitors=[
            {"left": 0, "top": 0, "width": 3840, "height": 1080},  # combined
            {"left": 0, "top": 0, "width": 1920, "height": 1080},  # primary
            {"left": 1920, "top": 0, "width": 1920, "height": 1080},  # secondary
        ],
    )

    result: list[MonitorInfo] = list_monitors()

    assert len(result) == 2
    assert result[0] == {
        "index": 1,
        "width": 1920,
        "height": 1080,
        "x": 0,
        "y": 0,
        "is_primary": True,
    }
    assert result[1] == {
        "index": 2,
        "width": 1920,
        "height": 1080,
        "x": 1920,
        "y": 0,
        "is_primary": False,
    }


@patch("winsight_mcp.screenshot.mss.mss")
def test_list_monitors_single(mock_mss_cls: MagicMock) -> None:
    """Single monitor setup returns one entry marked as primary."""
    _setup_mss_mock(
        mock_mss_cls,
        monitors=[
            {"left": 0, "top": 0, "width": 1920, "height": 1080},  # combined
            {"left": 0, "top": 0, "width": 1920, "height": 1080},  # only monitor
        ],
    )

    result: list[MonitorInfo] = list_monitors()

    assert len(result) == 1
    assert result[0]["is_primary"] is True
    assert result[0]["index"] == 1


@patch("winsight_mcp.screenshot.mss.mss")
def test_list_monitors_no_real_monitors(mock_mss_cls: MagicMock) -> None:
    """If mss only reports the combined monitor, an empty list is returned."""
    _setup_mss_mock(
        mock_mss_cls,
        monitors=[
            {"left": 0, "top": 0, "width": 1920, "height": 1080},  # combined only
        ],
    )

    result: list[MonitorInfo] = list_monitors()

    assert result == []
