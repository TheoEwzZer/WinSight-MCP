"""Application launching and process management."""

from __future__ import annotations

import subprocess
import sys
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


def run_python_script(
    script_path: str,
    wait_for_window: str | None = None,
    capture_after: float = 2.0,
    timeout: int = 30,
) -> ProcessResult:
    """Run a Python script, capture console output and optionally wait for a window."""
    try:
        proc: subprocess.Popen[bytes] = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    except Exception as e:
        return {"error": f"Failed to run script: {e}"}

    result: ProcessResult = {"pid": proc.pid, "script": script_path}

    if wait_for_window:
        window: WindowInfo | None = _wait_for_window(wait_for_window, timeout=timeout)
        if window:
            time.sleep(capture_after)
            window = find_window(wait_for_window) or window
            result["window"] = _window_rect(window)
        else:
            result["window_warning"] = (
                f"Window matching '{wait_for_window}' not found within {timeout}s"
            )

    try:
        stdout_bytes, stderr_bytes = proc.communicate(timeout=3)
        result["stdout"] = stdout_bytes.decode("utf-8", errors="replace")
        result["stderr"] = stderr_bytes.decode("utf-8", errors="replace")
        result["returncode"] = proc.returncode
    except subprocess.TimeoutExpired:
        result["note"] = "Process still running (GUI app likely)"

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
