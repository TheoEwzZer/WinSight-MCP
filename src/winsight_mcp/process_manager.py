"""Application launching and process management."""

from __future__ import annotations

import subprocess
import time

from .types import ProcessResult, WindowInfo, WindowRect
from .window_manager import find_window


def open_application(
    command: str,
    args: list[str] | None = None,
    wait_for_window: str | None = None,
    timeout: int = 10,
) -> ProcessResult:
    """Launch an application and optionally wait for its window to appear."""
    cmd: list[str] = [command] + (args or [])
    try:
        proc: subprocess.Popen[bytes] = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    except FileNotFoundError:
        return {"error": f"Command not found: {command}"}
    except Exception as e:
        return {"error": f"Failed to launch: {e}"}

    result: ProcessResult = {"pid": proc.pid, "command": command}

    if wait_for_window:
        window: WindowInfo | None = _wait_for_window(wait_for_window, timeout)
        if window:
            result["window"] = _window_rect(window)
        else:
            result["window_warning"] = (
                f"Window matching '{wait_for_window}' not found within {timeout}s"
            )

    return result


def _window_rect(w: WindowInfo) -> WindowRect:
    """Extract window rect dict including hwnd for PrintWindow capture."""
    return {
        "title": w["title"],
        "hwnd": w["hwnd"],
        "left": w["left"],
        "top": w["top"],
        "width": w["width"],
        "height": w["height"],
    }


def _wait_for_window(title: str, timeout: int = 10) -> WindowInfo | None:
    """Poll for a window matching the title to appear."""
    start: float = time.time()
    while time.time() - start < timeout:
        w: WindowInfo | None = find_window(title)
        if w is not None:
            return w
        elapsed: float = time.time() - start
        time.sleep(0.2 if elapsed < 5 else 0.5)
    return None
