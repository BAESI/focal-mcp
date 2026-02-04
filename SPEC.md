# FOCAL MCP Server – Full Development Specification

> Purpose: This document is the single source of truth for implementing the system with coding agents such as Codex / Claude Code / Cursor.  
> It is not just a task list. It includes the philosophy (Why), product definition (What), and the implementation structure/interfaces (How).

---

## 0. Project Overview (Why)

### 0.1 Problem Statement
Modern developers do not rely on a single AI tool. They use Cursor, Codex, Claude Code, etc., often across multiple machines. Each tool forces them to manage **system prompts, style guides, safety rules, and tool usage rules** in different places and formats.

This creates:
- Duplicate rule configuration across tools
- Inconsistent response quality and safety between tools
- Rules scattered inside repositories, polluting codebases
- Reconfiguration costs whenever a new machine or environment is used

### 0.2 Guiding Philosophy
This project follows:

- **Rule is not project data**: Rules are user/team assets, not repo assets.
- **Single Source of Truth**: All AI tools must reference one rule hub.
- **Tool-agnostic**: Rules persist even if tools change.
- **Invisible by default**: Rules should feel always-on, not manually applied.

FOCAL MCP Server is the **operating system for rules** that implements this philosophy.

---

## 1. Product Definition (What)

### 1.1 One-line Definition
FOCAL MCP is a **central MCP server that automatically injects consistent behavior rules across AI tools**.

### 1.2 Core Features
- All AI tools share the same rules
- Rules live in the **user home directory**, not the repo
- MCP server provides a **Web UI**
- Rules are managed as a **file/folder tree**
- Rule changes are **immediately reflected** (prompts/resources list_changed)
- Rule scope:
  - System prompts
  - Style guides
  - Safety policies
  - Tool usage policies
  - Sub-agents (role prompt bundles)

---

## 2. UX Principles

### 2.1 UX Model
- **Tool Launch Sync Model**
- User only starts the MCP server
- When an AI tool starts, rules are already applied

### 2.2 Desired User Feeling
- "It just works by default"
- My working identity persists across tools
- Editing rules feels as light as editing a document

---

## 3. System Architecture

### 3.1 Components

1) FOCAL MCP Server (Python / FastAPI)
- MCP Server (JSON-RPC 2.0)
- Web UI Server
- Workspace Manager

2) Workspace (User Home)
- `~/.focal_mcp/workspace/`
- Physical storage of rule files

3) MCP Clients
- Codex
- Claude Code
- Cursor

---

## 4. Workspace Design

### 4.1 Location (Important)
- **Never inside the repository**
- Default location:

```
~/.focal_mcp/
  workspace/
    core/
      system.md
      style.md
      safety.md
      tool_policy.md
    agents/
  workspace.json
```

### 4.2 Core Rules (Required)
| File | Meaning |
|---|---|
| core/system.md | Global behavior / system prompt |
| core/style.md | Tone, response format, code style |
| core/safety.md | Safety rules and refusal policy |
| core/tool_policy.md | Tool usage order/constraints |

### 4.3 Agents Rules
- `agents/*.md` = sub-agent definitions
- One file = one role

Example:
```
agents/reviewer.md
agents/doc_writer.md
```

---

## 5. Web UI Requirements

### 5.1 UI Goal
- Make rules feel like a **file system**, not a settings panel

### 5.2 Layout
- Left: file/folder tree
- Center: Markdown editor
- Top: New File / New Folder / Delete / Refresh

### 5.3 Required Features
- File create / edit / delete
- Folder create / delete
- **Drag-and-drop move**
- On save: immediately emit MCP prompts/resources list_changed

---

## 6. MCP Server Specification

### 6.1 Transport
- JSON-RPC 2.0
- Transport:
  - HTTP (required)
  - WebSocket (notifications)

Endpoints:
```
POST /mcp
GET  /mcp/ws
```

---

### 6.1.1 initialize
- Client calls initialize on connect
- Server returns protocolVersion, serverInfo, capabilities
- Include **instructions** that bundle core rules
- The top of instructions must contain the runtime directive:
  - Before every user response, call MCP tool `focal_rules` to fetch the latest rules

### 6.2 MCP Prompts

#### prompts/list
- Expose core rules + agents rules

Mapping:
| Prompt Name | File Path |
|---|---|
| core.system | core/system.md |
| core.style | core/style.md |
| core.safety | core/safety.md |
| core.tool_policy | core/tool_policy.md |
| agents.reviewer | agents/reviewer.md |

#### prompts/get
- Map name → file path and return content
- Return as a system role message

---

### 6.3 MCP Resources

#### resources/list
- Flatten all files inside workspace
- URI scheme:
```
focal:///core/system.md
```

#### resources/read
- Return raw file content

---

### 6.4 MCP Notifications

#### notifications/prompts/list_changed & notifications/resources/list_changed (Critical)
- Fire on create / update / delete / move
- Send list_changed for prompts and resources respectively
- Broadcast via WebSocket

---

### 6.5 MCP Tools

#### tools/list
- Expose `focal_rules`
- Purpose: fetch the latest rules before every response

#### tools/call
- When name = `focal_rules`, return the full core rules as text

---

## 7. Security (MVP Minimum)

- Bind to 127.0.0.1 by default
- Block path traversal completely
- (Optional) X-API-Key support

---

## 8. Fixed Tech Stack

- Python 3.11+
- FastAPI
- Uvicorn
- pathlib
- Pydantic

---

## 9. Definition of Done

- [ ] Web UI accessible when server runs
- [ ] Workspace auto-created
- [ ] Web UI supports CRUD
- [ ] MCP prompts/list, get work
- [ ] MCP resources/list, read work
- [ ] Rule changes trigger prompts/resources list_changed
- [ ] Demo success in at least one of Codex / Claude Code / Cursor
- [ ] No rule files inside the repository

---

## 10. Role of Codex

> Codex is not a code generator. It is the engineer implementing this system according to this document.

Codex must:
- Never violate the philosophy or constraints in this spec
- Never include rules inside the repo
- Make the architectural intent obvious in the code structure

---

## 11. Recommended Development Order

1) Workspace load/save
2) Web UI + file CRUD
3) MCP prompts/resources
4) prompts/resources list_changed notification
5) README (tool connection guide)

---

**This document remains the authoritative source for all future implementation, refactoring, and expansion.**
