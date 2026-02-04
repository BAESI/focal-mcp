from __future__ import annotations

import asyncio
from typing import Set

from fastapi import WebSocket

from .logging_utils import logger


class Notifier:
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
            count = len(self._clients)
        logger.info("WS connected. clients=%s", count)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)
            count = len(self._clients)
        logger.info("WS disconnected. clients=%s", count)

    async def _broadcast(self, method: str) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {},
        }
        async with self._lock:
            clients = list(self._clients)
        logger.info("Broadcast %s to %s clients", method, len(clients))
        for client in clients:
            try:
                await client.send_json(payload)
            except Exception:
                await self.disconnect(client)

    async def broadcast_prompts_list_changed(self) -> None:
        await self._broadcast("notifications/prompts/list_changed")

    async def broadcast_resources_list_changed(self) -> None:
        await self._broadcast("notifications/resources/list_changed")

    async def broadcast_list_changed(self) -> None:
        await self.broadcast_prompts_list_changed()
        await self.broadcast_resources_list_changed()
