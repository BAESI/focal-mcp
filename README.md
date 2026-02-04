# FOCAL MCP Server

FOCAL MCP (Framework for Orchestrated Central AI ruLes) is a local MCP server that centralizes AI behavior rules and applies them across tools like Codex, Claude Code, and Cursor.

## Quick Start

### Prerequisites
- `uv` installed (required for `uvx`)

### Run the server (recommended)
```bash
uvx --from focal-mcp-server focal-mcp-server
```

Open the Web UI:
```
http://127.0.0.1:8765
```

MCP endpoint:
```
http://127.0.0.1:8765/mcp
```

WebSocket notifications:
```
ws://127.0.0.1:8765/mcp/ws
```

## Configure Your MCP Client

FOCAL MCP uses **streamable HTTP**, so you start the server yourself and point clients to the URL above.

### Codex (example)
Add the following to `~/.codex/config.toml`:
```toml
[mcp_servers.focal]
enabled = true
url = "http://127.0.0.1:8765/mcp"
```

Restart Codex after saving.

## Edit Rules (Live)
Rules live outside the repo in:
```
~/.focal_mcp/workspace/
  core/
    system.md
    style.md
    safety.md
    tool_policy.md
  agents/
```

Use the Web UI to edit files. Updates are applied immediately.

## How Rules Are Applied
FOCAL MCP exposes a tool named `focal_rules`. Agents should call it before every response to fetch the latest rules.

If rules do not update immediately:
1. Ensure the client is connected to the MCP server.
2. Ensure the client calls `focal_rules` before responding.
3. Reconnect the client if needed.

## Project Prompt (Codex)
The repository-level prompt is stored in:
```
agents.md
```

## Roadmap
- Project-specific rule management for multi-repo workflows
- UI/UX improvements for rule editing and visibility
