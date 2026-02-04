from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, WebSocket, Response
from fastapi.responses import JSONResponse
import uvicorn
import uuid

from .mcp import MCPHandler, JsonRpcError
from .notifications import Notifier
from .web import WebRoutes
from .workspace import WorkspaceManager
from .logging_utils import logger


app = FastAPI()
workspace = WorkspaceManager()
workspace.ensure()
notifier = Notifier()
handler = MCPHandler(workspace)
server_id = uuid.uuid4().hex[:8]

web_routes = WebRoutes(workspace, notifier, server_id)
app.include_router(web_routes.router)


@app.post("/mcp")
async def mcp(payload: Dict[str, Any]) -> Response:
    method = payload.get("method")
    request_id = payload.get("id")
    if method == "prompts/get":
        name = (payload.get("params") or {}).get("name")
        logger.info("MCP prompts/get name=%s id=%s", name, request_id)
    else:
        logger.info("MCP request method=%s id=%s", method, request_id)

    # JSON-RPC notifications should not receive a response
    if request_id is None:
        try:
            handler.handle(payload)
        except JsonRpcError as exc:
            logger.info("MCP notification error code=%s message=%s", exc.code, exc.message)
        except Exception:
            logger.exception("MCP notification error")
        return Response(status_code=204)

    try:
        result = handler.handle(payload)
        response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        return JSONResponse(response)
    except JsonRpcError as exc:
        logger.info("MCP error code=%s message=%s id=%s", exc.code, exc.message, request_id)
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": exc.code, "message": exc.message},
        }
        return JSONResponse(response)
    except Exception:
        logger.exception("MCP internal error id=%s", request_id)
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": "Internal error"},
        }
        return JSONResponse(response)


@app.websocket("/mcp/ws")
async def mcp_ws(websocket: WebSocket) -> None:
    await notifier.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        logger.exception("WS error")
        await notifier.disconnect(websocket)


def run() -> None:
    uvicorn.run("focal_mcp_server.app:app", host="127.0.0.1", port=8765, reload=False)
