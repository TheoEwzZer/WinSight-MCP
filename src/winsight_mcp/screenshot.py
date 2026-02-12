"""Screen capture functions using Pillow, mss, and Win32 PrintWindow."""

from __future__ import annotations

import ctypes
import io
from typing import TYPE_CHECKING, cast

import mss
import win32gui
import win32ui
from PIL import Image as PILImage
from PIL import ImageGrab

from .types import BitmapInfo

if TYPE_CHECKING:
    from _win32typing import PyCBitmap, PyCDC
    from mss.screenshot import ScreenShot

# PrintWindow flag: capture full DWM-rendered content (Windows 8.1+)
PW_RENDERFULLCONTENT: int = 2


def capture_full_screen(monitor: int = 1) -> bytes:
    """Capture the full screen (or a specific monitor) and return PNG bytes."""
    with mss.mss() as sct:
        monitors: list[dict[str, int]] = sct.monitors
        if monitor < 0 or monitor >= len(monitors):
            raise ValueError(
                f"Monitor {monitor} not found. Available: 0-{len(monitors) - 1} "
                f"(0 = all monitors combined)"
            )
        screenshot: ScreenShot = sct.grab(monitors[monitor])

    pil_img: PILImage.Image = PILImage.frombytes(
        "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
    )
    buffer: io.BytesIO = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    return buffer.getvalue()


def capture_region(x: int, y: int, width: int, height: int) -> bytes:
    """Capture a specific region of the screen and return PNG bytes."""
    bbox: tuple[int, int, int, int] = (x, y, x + width, y + height)
    screenshot: PILImage.Image = ImageGrab.grab(bbox=bbox)
    buffer: io.BytesIO = io.BytesIO()
    screenshot.save(buffer, format="PNG")
    return buffer.getvalue()


def capture_window_hwnd(hwnd: int) -> bytes:
    """Capture a window's content using Win32 PrintWindow API.

    This captures the actual window content even if it's behind other windows.
    """
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width: int = right - left
    height: int = bottom - top

    if width <= 0 or height <= 0:
        raise ValueError(f"Window has invalid dimensions: {width}x{height}")

    # Create device contexts and bitmap
    hwnd_dc: int = win32gui.GetWindowDC(hwnd)
    mfc_dc: PyCDC = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc: PyCDC = mfc_dc.CreateCompatibleDC()
    bitmap: PyCBitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(bitmap)

    # Use PrintWindow to render the window content into our bitmap
    ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)

    # Convert to PIL Image
    bmp_info: BitmapInfo = cast(BitmapInfo, bitmap.GetInfo())  # pyright: ignore[reportUnknownMemberType]
    bmp_bits: bytes = bitmap.GetBitmapBits(True)
    pil_img: PILImage.Image = PILImage.frombuffer(
        "RGB",
        (bmp_info["bmWidth"], bmp_info["bmHeight"]),
        bmp_bits,
        "raw",
        "BGRX",
        0,
        1,
    )

    # Cleanup Win32 resources
    win32gui.DeleteObject(bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)

    buffer: io.BytesIO = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    return buffer.getvalue()
