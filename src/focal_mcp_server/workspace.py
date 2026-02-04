from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Iterable, Dict, Any

WORKSPACE_ROOT = Path.home() / ".focal_mcp" / "workspace"
CORE_DIR = "core"
AGENTS_DIR = "agents"

DEFAULT_CORE_FILES = {
    "core/system.md": """# System

FOCAL MCP system prompt.
""",
    "core/style.md": """# Style

FOCAL MCP style guide.
""",
    "core/safety.md": """# Safety

FOCAL MCP safety rules.
""",
    "core/tool_policy.md": """# Tool Policy

FOCAL MCP tool usage rules.
""",
}


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path

    @property
    def core(self) -> Path:
        return self.root / CORE_DIR

    @property
    def agents(self) -> Path:
        return self.root / AGENTS_DIR


class WorkspaceManager:
    def __init__(self, root: Path | None = None) -> None:
        self.paths = WorkspacePaths(root=root or WORKSPACE_ROOT)

    def ensure(self) -> None:
        self.paths.root.mkdir(parents=True, exist_ok=True)
        self.paths.core.mkdir(parents=True, exist_ok=True)
        self.paths.agents.mkdir(parents=True, exist_ok=True)
        for rel_path, content in DEFAULT_CORE_FILES.items():
            path = self.paths.root / rel_path
            if not path.exists():
                path.write_text(content, encoding="utf-8")

    def resolve_safe(self, rel_path: str) -> Path:
        candidate = (self.paths.root / rel_path.lstrip("/"))
        resolved = candidate.resolve()
        if self.paths.root.resolve() not in resolved.parents and resolved != self.paths.root.resolve():
            raise ValueError("Path traversal blocked")
        return resolved

    def list_files(self) -> Iterable[Path]:
        for path in self.paths.root.rglob("*"):
            if path.is_file():
                yield path

    def relative(self, path: Path) -> str:
        return str(path.relative_to(self.paths.root)).replace("\\", "/")

    def rules_fingerprint(self) -> Dict[str, Any]:
        sha = hashlib.sha256()
        latest_mtime: float | None = None
        files = sorted(self.list_files(), key=lambda p: self.relative(p))
        for path in files:
            rel = self.relative(path)
            sha.update(rel.encode("utf-8"))
            sha.update(b"|")
            sha.update(path.read_bytes())
            mtime = path.stat().st_mtime
            if latest_mtime is None or mtime > latest_mtime:
                latest_mtime = mtime
        result: Dict[str, Any] = {
            "rulesHash": sha.hexdigest()[:12],
            "rulesUpdatedAt": None,
        }
        if latest_mtime is not None:
            result["rulesUpdatedAt"] = datetime.fromtimestamp(latest_mtime, tz=timezone.utc).isoformat()
        return result
