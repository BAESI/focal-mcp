# FOCAL MCP Server

FOCAL MCP (Framework for Orchestrated Central AI ruLes) is a local MCP server that centralizes AI behavior rules and injects them across tools like Codex, Claude Code, and Cursor.

## What This Server Does
- Stores rules in a user home workspace: `~/.focal_mcp/workspace`
- Serves a web UI to edit rules as files
- Exposes MCP prompts/resources + list_changed notifications
- Provides a `focal_rules` tool so agents can fetch the latest rules before every response

## Project Layout (Refactored)
```
FOCAL-MCP/
  README.md
  SPEC.md
  agents.md
  pyproject.toml
  src/
    focal_mcp_server/
      app.py
      mcp.py
      notifications.py
      web.py
      workspace.py
      logging_utils.py
```

## Quick Start
```bash
uvx --from . focal-mcp-server
```

Web UI:
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

## Workspace
Rules are stored outside the repo:
```
~/.focal_mcp/workspace/
  core/
    system.md
    style.md
    safety.md
    tool_policy.md
  agents/
```

## MCP Behavior
- `initialize` returns instructions that include a runtime directive to call `focal_rules` before every response.
- `tools/list` exposes `focal_rules` which returns the latest rules from disk.
- Rule changes trigger:
  - `notifications/prompts/list_changed`
  - `notifications/resources/list_changed`

## Project Prompt (Codex)
The repository-level prompt for Codex lives in:
```
agents.md
```

## Development Notes
- This project uses a `src/` layout for the Python package.
- Use `SPEC.md` as the single source of truth for behavior, interfaces, and constraints.

## Roadmap (Next)
- Manage rules per project when working across multiple repos
- UI/UX improvements for rule editing and visibility
