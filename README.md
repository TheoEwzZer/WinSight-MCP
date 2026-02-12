# WinSight MCP

mcp-name: io.github.TheoEwzZer/winsight

Windows Screen Capture MCP Server — give Claude Code eyes on your Windows desktop.

WinSight is an [MCP](https://modelcontextprotocol.io) server that lets Claude Code capture your screen, manage windows, and launch applications on Windows.

## Features

- **Screenshot** the full screen, a specific region, or a specific window
- **Window capture** uses Win32 `PrintWindow` API — captures the real window content even when it's behind other windows
- **List and inspect** open windows (title, position, size, state)
- **Focus** any window, including minimized or background apps
- **Launch** applications and Python scripts, with automatic window detection

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

| Tool                | Description                                                             |
| ------------------- | ----------------------------------------------------------------------- |
| `take_screenshot`   | Capture the full screen or a specific monitor                           |
| `screenshot_window` | Capture a specific window by title (works even if behind other windows) |
| `screenshot_region` | Capture a rectangular region of the screen                              |
| `list_windows`      | List all visible windows with optional title filter                     |
| `get_window_info`   | Get detailed info about a window (position, size, state)                |
| `focus_window`      | Bring a window to the foreground                                        |
| `open_application`  | Launch an application and optionally wait for its window                |
| `run_python_script` | Run a Python script and capture console output + window screenshot      |

## Examples

Once the MCP server is connected, you can ask Claude Code things like:

- "Take a screenshot of my screen"
- "List all open windows"
- "Capture the Notepad window"
- "Open calculator and take a screenshot of it"
- "Run my tkinter script and show me what it looks like"
- "Focus the Chrome window"

## License

MIT
