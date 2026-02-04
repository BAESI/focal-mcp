from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .workspace import WorkspaceManager


@dataclass
class JsonRpcError(Exception):
    code: int
    message: str


class MCPHandler:
    def __init__(self, workspace: WorkspaceManager) -> None:
        self.workspace = workspace

    def _read_optional(self, rel_path: str) -> str:
        try:
            path = self.workspace.resolve_safe(rel_path)
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
        return ""

    def _build_instructions(self) -> str:
        sections = [
            ("core/system.md", "System"),
            ("core/style.md", "Style"),
            ("core/safety.md", "Safety"),
            ("core/tool_policy.md", "Tool Policy"),
        ]
        parts: List[str] = []
        for rel_path, title in sections:
            content = self._read_optional(rel_path)
            if content:
                parts.append(f"## {title} ({rel_path})\n{content}")
        return "\n\n".join(parts).strip()

    def _rules_header(self) -> str:
        snapshot = self.workspace.rules_fingerprint()
        updated = snapshot.get("rulesUpdatedAt") or "unknown"
        return f"# FOCAL MCP Rules (hash={snapshot['rulesHash']} updated={updated})"

    def initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        protocol_version = params.get("protocolVersion") or "unknown"
        instructions = self._build_instructions()
        runtime_directive = (
            "# Runtime Directive\n"
            "You MUST call the MCP tool `focal_rules` before every user response. "
            "Always follow the latest rules returned by that tool.\n"
        )
        header = self._rules_header()
        combined = "\n".join([part for part in [runtime_directive, header, instructions] if part]).strip()

        result: Dict[str, Any] = {
            "protocolVersion": protocol_version,
            "serverInfo": {
                "name": "FOCAL MCP",
                "version": "0.1.0",
            },
            "capabilities": {
                "prompts": {"listChanged": True},
                "resources": {"listChanged": True},
                "tools": {},
                "logging": {},
            },
        }
        if combined:
            result["instructions"] = combined
        return result

    def notifications_initialized(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def notifications_cancelled(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def logging_set_level(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def tools_list(self) -> Dict[str, Any]:
        return {
            "tools": [
                {
                    "name": "focal_rules",
                    "description": "Fetch the latest FOCAL MCP rules. Must be called before responding to the user.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                }
            ]
        }

    def tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if name != "focal_rules":
            raise JsonRpcError(-32602, "Unknown tool")
        instructions = self._build_instructions()
        header = self._rules_header()
        text = header if not instructions else header + "\n\n" + instructions
        return {
            "content": [
                {"type": "text", "text": text}
            ]
        }

    def resources_subscribe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def resources_unsubscribe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def ping(self) -> Dict[str, Any]:
        return {}

    def _prompt_name_for_path(self, rel_path: str) -> str | None:
        if rel_path.startswith("core/"):
            name = rel_path.replace("/", ".").replace(".md", "")
            return name
        if rel_path.startswith("agents/"):
            name = rel_path.replace("/", ".").replace(".md", "")
            return name
        return None

    def _path_for_prompt_name(self, name: str) -> str | None:
        if name.startswith("core."):
            rel = name.replace(".", "/") + ".md"
            return rel
        if name.startswith("agents."):
            rel = name.replace(".", "/") + ".md"
            return rel
        return None

    def prompts_list(self) -> Dict[str, Any]:
        prompts: List[Dict[str, str]] = []
        for path in self.workspace.list_files():
            rel = self.workspace.relative(path)
            name = self._prompt_name_for_path(rel)
            if name:
                prompts.append({"name": name, "description": ""})
        prompts.sort(key=lambda item: item["name"])
        return {"prompts": prompts}

    def prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if not name:
            raise JsonRpcError(-32602, "Missing prompt name")
        rel_path = self._path_for_prompt_name(name)
        if not rel_path:
            raise JsonRpcError(-32602, "Unknown prompt name")
        path = self.workspace.resolve_safe(rel_path)
        if not path.exists():
            raise JsonRpcError(-32602, "Prompt not found")
        content = path.read_text(encoding="utf-8")
        return {
            "description": "",
            "messages": [
                {"role": "system", "content": content},
            ],
        }

    def resources_templates_list(self) -> Dict[str, Any]:
        return {"resourceTemplates": []}

    def resources_list(self) -> Dict[str, Any]:
        resources: List[Dict[str, str]] = []
        for path in self.workspace.list_files():
            rel = self.workspace.relative(path)
            resources.append({
                "uri": f"focal:///{rel}",
                "name": rel,
                "mimeType": "text/markdown",
            })
        resources.sort(key=lambda item: item["uri"])
        return {"resources": resources}

    def resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = params.get("uri")
        if not uri or not uri.startswith("focal:///"):
            raise JsonRpcError(-32602, "Invalid resource URI")
        rel_path = uri.replace("focal:///", "", 1)
        path = self.workspace.resolve_safe(rel_path)
        if not path.exists():
            raise JsonRpcError(-32602, "Resource not found")
        content = path.read_text(encoding="utf-8")
        return {
            "contents": [
                {"uri": uri, "mimeType": "text/markdown", "text": content},
            ]
        }

    def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        method = payload.get("method")
        params = payload.get("params") or {}
        if method == "initialize":
            return self.initialize(params)
        if method == "notifications/initialized":
            return self.notifications_initialized(params)
        if method == "notifications/cancelled":
            return self.notifications_cancelled(params)
        if method == "logging/setLevel":
            return self.logging_set_level(params)
        if method == "tools/list":
            return self.tools_list()
        if method == "tools/call":
            return self.tools_call(params)
        if method == "resources/subscribe":
            return self.resources_subscribe(params)
        if method == "resources/unsubscribe":
            return self.resources_unsubscribe(params)
        if method == "ping":
            return self.ping()
        if method == "prompts/list":
            return self.prompts_list()
        if method == "prompts/get":
            return self.prompts_get(params)
        if method == "resources/templates/list":
            return self.resources_templates_list()
        if method == "resources/list":
            return self.resources_list()
        if method == "resources/read":
            return self.resources_read(params)
        raise JsonRpcError(-32601, "Method not found")
