# WinSight MCP

mcp-name: io.github.TheoEwzZer/winsight

Windows Screen Capture MCP Server — give Claude Code eyes on your Windows desktop.

WinSight is an [MCP](https://modelcontextprotocol.io) server that lets Claude Code capture your screen, manage windows, and launch applications on Windows.

## Features

- **Screenshot** the full screen, a specific region, or a specific window
- **Window capture** uses Win32 `PrintWindow` API — captures the real window content even when it's behind other windows
- **List and inspect** open windows and monitors (title, position, size, state, resolution)
- **Control windows** — move, resize, minimize, maximize, restore, and focus
- **Launch** applications and wait for their windows

## Requirements

- **Windows 10/11**
- **Python 3.10+**

## Quick Start

### Option 1: uvx (recommended)

No install needed — runs directly:

```json
{
  "mcpServers": {
    "winsight": {
      "command": "uvx",
      "args": ["winsight-mcp"]
    }
  }
}
```

Add this to your project's `.mcp.json` or `~/.claude/claude_desktop_config.json`.

### Option 2: pip install

```bash
pip install winsight-mcp
```

Then configure:

```json
{
  "mcpServers": {
    "winsight": {
      "command": "winsight-mcp"
    }
  }
}
```

### Option 3: From source

```bash
git clone https://github.com/TheoEwzZer/WinSight-MCP.git
cd WinSight-MCP
uv sync
```

```json
{
  "mcpServers": {
    "winsight": {
      "command": "uv",
      "args": ["--directory", "/path/to/WinSight-MCP", "run", "winsight-mcp"]
    }
  }
}
```

## Tools

### Screenshot

| Tool                | Description                                                             |
| ------------------- | ----------------------------------------------------------------------- |
| `take_screenshot`   | Capture the full screen or a specific monitor                           |
| `screenshot_window` | Capture a specific window by title (works even if behind other windows) |
| `screenshot_region` | Capture a rectangular region of the screen                              |

### Window Management

| Tool              | Description                                                 |
| ----------------- | ----------------------------------------------------------- |
| `list_windows`    | List all visible windows with optional title filter         |
| `get_window_info` | Get detailed info about a window (position, size, state)    |
| `focus_window`    | Bring a window to the foreground                            |
| `resize_window`   | Resize a window to specific dimensions                      |
| `move_window`     | Move a window to a specific position                        |
| `minimize_window` | Minimize a window to the taskbar                            |
| `maximize_window` | Maximize a window to fill the screen                        |
| `restore_window`  | Restore a minimized or maximized window to its normal state |
| `wait_for_window` | Wait for a window to appear (adaptive polling with timeout) |

### System

| Tool               | Description                                                   |
| ------------------ | ------------------------------------------------------------- |
| `list_monitors`    | List all monitors with resolution, position, and primary flag |
| `open_application` | Launch an application and optionally wait for its window      |

## Examples

Once the MCP server is connected, you can ask Claude Code things like:

- "Take a screenshot of my screen"
- "List all open windows"
- "Capture the Notepad window"
- "Open calculator and take a screenshot of it"
- "Focus the Chrome window"
- "Resize the app window to 800x600 and take a screenshot"
- "Move the window to the top-left corner"
- "What monitors do I have?"

## License

MIT
