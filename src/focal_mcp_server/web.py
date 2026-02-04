from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .workspace import WorkspaceManager
from .notifications import Notifier
from .logging_utils import logger


def build_tree(root: Path) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    for path in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        if path.is_dir():
            nodes.append({"type": "folder", "name": path.name, "children": build_tree(path)})
        else:
            nodes.append({"type": "file", "name": path.name})
    return nodes


class FilePayload(BaseModel):
    path: str
    content: str


class FolderPayload(BaseModel):
    path: str


class MovePayload(BaseModel):
    src: str
    dst: str


class WebRoutes:
    def __init__(self, workspace: WorkspaceManager, notifier: Notifier, server_id: str) -> None:
        self.workspace = workspace
        self.notifier = notifier
        self.server_id = server_id
        self.router = APIRouter()
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route("/", self.index, methods=["GET"], response_class=HTMLResponse)
        self.router.add_api_route("/api/tree", self.tree, methods=["GET"])
        self.router.add_api_route("/api/status", self.status, methods=["GET"])
        self.router.add_api_route("/api/file", self.read_file, methods=["GET"])
        self.router.add_api_route("/api/file", self.write_file, methods=["POST"])
        self.router.add_api_route("/api/file", self.delete_file, methods=["DELETE"])
        self.router.add_api_route("/api/folder", self.create_folder, methods=["POST"])
        self.router.add_api_route("/api/folder", self.delete_folder, methods=["DELETE"])
        self.router.add_api_route("/api/move", self.move_entry, methods=["POST"])

    async def index(self) -> HTMLResponse:
        return HTMLResponse(_HTML)

    async def tree(self) -> Dict[str, Any]:
        return {"root": build_tree(self.workspace.paths.root)}

    async def status(self) -> Dict[str, Any]:
        snapshot = self.workspace.rules_fingerprint()
        return {
            "serverId": self.server_id,
            "workspaceRoot": str(self.workspace.paths.root),
            **snapshot,
        }

    async def read_file(self, path: str) -> Dict[str, str]:
        full = self.workspace.resolve_safe(path)
        if not full.exists() or not full.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        return {"content": full.read_text(encoding="utf-8")}

    async def write_file(self, payload: FilePayload) -> Dict[str, str]:
        full = self.workspace.resolve_safe(payload.path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(payload.content, encoding="utf-8")
        logger.info("Write file path=%s bytes=%s", payload.path, len(payload.content.encode("utf-8")))
        await self.notifier.broadcast_list_changed()
        return {"status": "ok"}

    async def delete_file(self, path: str) -> Dict[str, str]:
        full = self.workspace.resolve_safe(path)
        if full.exists() and full.is_file():
            full.unlink()
            logger.info("Delete file path=%s", path)
            await self.notifier.broadcast_list_changed()
        return {"status": "ok"}

    async def create_folder(self, payload: FolderPayload) -> Dict[str, str]:
        full = self.workspace.resolve_safe(payload.path)
        full.mkdir(parents=True, exist_ok=True)
        logger.info("Create folder path=%s", payload.path)
        await self.notifier.broadcast_list_changed()
        return {"status": "ok"}

    async def delete_folder(self, path: str) -> Dict[str, str]:
        full = self.workspace.resolve_safe(path)
        if full.exists() and full.is_dir():
            for child in sorted(full.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                else:
                    child.rmdir()
            full.rmdir()
            logger.info("Delete folder path=%s", path)
            await self.notifier.broadcast_list_changed()
        return {"status": "ok"}

    async def move_entry(self, payload: MovePayload) -> Dict[str, str]:
        src = self.workspace.resolve_safe(payload.src)
        dst = self.workspace.resolve_safe(payload.dst)
        if not src.exists():
            raise HTTPException(status_code=404, detail="Source not found")
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        logger.info("Move entry src=%s dst=%s", payload.src, payload.dst)
        await self.notifier.broadcast_list_changed()
        return {"status": "ok"}


_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>FOCAL MCP</title>
  <style>
    :root {
      --bg: #0f1419;
      --panel: #182029;
      --panel-2: #1f2a35;
      --accent: #f4b942;
      --text: #e6eef5;
      --muted: #99a7b5;
      --border: #2a3745;
      font-family: "IBM Plex Sans", "Space Grotesk", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(circle at top, #1a2430, #0b1117);
      color: var(--text);
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header { padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; gap: 12px; align-items: center; }
    header h1 { margin: 0; font-size: 18px; letter-spacing: 0.5px; }
    header button { background: var(--accent); border: none; padding: 8px 12px; border-radius: 6px; font-weight: 600; cursor: pointer; }
    header button.secondary { background: var(--panel-2); color: var(--text); }
    #status-bar { padding: 6px 24px; border-bottom: 1px solid var(--border); font-size: 12px; color: var(--muted); }
    main { display: grid; grid-template-columns: 280px 1fr; flex: 1; min-height: 0; }
    #tree { background: var(--panel); border-right: 1px solid var(--border); padding: 16px; overflow: auto; }
    #editor { display: flex; flex-direction: column; padding: 16px; gap: 12px; min-height: 0; }
    #path { font-size: 13px; color: var(--muted); }
    textarea { flex: 1; width: 100%; background: var(--panel-2); color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-size: 14px; font-family: "IBM Plex Mono", monospace; }
    ul { list-style: none; padding-left: 16px; margin: 0; }
    li { margin: 4px 0; cursor: pointer; }
    li.folder { font-weight: 600; color: var(--accent); }
    .drag { opacity: 0.6; }
  </style>
</head>
<body>
  <header>
    <h1>FOCAL MCP Workspace</h1>
    <button onclick="createFile()">New File</button>
    <button onclick="createFolder()" class="secondary">New Folder</button>
    <button onclick="deleteEntry()" class="secondary">Delete</button>
    <button onclick="refreshTree()" class="secondary">Refresh</button>
  </header>
  <div id="status-bar">Loading status...</div>
  <main>
    <div id="tree"></div>
    <div id="editor">
      <div id="path">Select a file</div>
      <textarea id="content" placeholder="Select a file to edit"></textarea>
      <button onclick="saveFile()" style="align-self:flex-start;">Save</button>
    </div>
  </main>
  <script>
    let currentPath = null;
    let currentType = null;

    async function refreshStatus() {
      const res = await fetch('/api/status');
      const data = await res.json();
      const updated = data.rulesUpdatedAt ? new Date(data.rulesUpdatedAt).toLocaleString() : 'n/a';
      const status = document.getElementById('status-bar');
      status.textContent = `Server ${data.serverId} · Workspace ${data.workspaceRoot} · Rules ${data.rulesHash} · Updated ${updated}`;
    }

    async function refreshTree() {
      const res = await fetch('/api/tree');
      const data = await res.json();
      const tree = document.getElementById('tree');
      tree.innerHTML = '';
      tree.appendChild(renderNodes(data.root, ''));
      await refreshStatus();
    }

    function renderNodes(nodes, prefix) {
      const ul = document.createElement('ul');
      for (const node of nodes) {
        const li = document.createElement('li');
        li.textContent = node.name;
        const path = prefix ? prefix + '/' + node.name : node.name;
        li.dataset.path = path;
        if (node.type === 'folder') {
          li.classList.add('folder');
          li.addEventListener('click', (e) => { e.stopPropagation(); currentPath = path; currentType = 'folder'; });
          li.setAttribute('draggable', true);
          li.addEventListener('dragstart', onDragStart);
          li.addEventListener('dragover', onDragOver);
          li.addEventListener('drop', onDrop);
          li.appendChild(renderNodes(node.children, path));
        } else {
          li.addEventListener('click', async (e) => {
            e.stopPropagation();
            currentPath = path; currentType = 'file';
            const res = await fetch(`/api/file?path=${encodeURIComponent(path)}`);
            const data = await res.json();
            document.getElementById('path').textContent = path;
            document.getElementById('content').value = data.content;
          });
          li.setAttribute('draggable', true);
          li.addEventListener('dragstart', onDragStart);
          li.addEventListener('dragover', onDragOver);
          li.addEventListener('drop', onDrop);
        }
        ul.appendChild(li);
      }
      return ul;
    }

    function onDragStart(e) {
      e.dataTransfer.setData('text/plain', e.target.dataset.path);
      e.target.classList.add('drag');
    }

    function onDragOver(e) {
      e.preventDefault();
    }

    async function onDrop(e) {
      e.preventDefault();
      const src = e.dataTransfer.getData('text/plain');
      const dstBase = e.target.dataset.path;
      const dst = dstBase + '/' + src.split('/').pop();
      if (src === dst) return;
      await fetch('/api/move', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({src, dst}),
      });
      await refreshTree();
    }

    async function saveFile() {
      if (!currentPath || currentType !== 'file') return;
      const content = document.getElementById('content').value;
      await fetch('/api/file', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: currentPath, content}),
      });
      await refreshStatus();
    }

    async function createFile() {
      const path = prompt('New file path (e.g. core/new.md)');
      if (!path) return;
      await fetch('/api/file', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path, content: ''}),
      });
      await refreshTree();
    }

    async function createFolder() {
      const path = prompt('New folder path (e.g. agents)');
      if (!path) return;
      await fetch('/api/folder', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path}),
      });
      await refreshTree();
    }

    async function deleteEntry() {
      if (!currentPath) return;
      if (!confirm('Delete ' + currentPath + '?')) return;
      if (currentType === 'file') {
        await fetch(`/api/file?path=${encodeURIComponent(currentPath)}`, {method: 'DELETE'});
      } else {
        await fetch(`/api/folder?path=${encodeURIComponent(currentPath)}`, {method: 'DELETE'});
      }
      currentPath = null; currentType = null;
      document.getElementById('path').textContent = 'Select a file';
      document.getElementById('content').value = '';
      await refreshTree();
    }

    refreshTree();
  </script>
</body>
</html>"""
