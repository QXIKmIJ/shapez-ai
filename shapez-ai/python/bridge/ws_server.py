"""
WebSocket RPC Server for Shapez AI Game Bridge.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, Callable, Awaitable
from aiohttp import web, WSMsgType

from .protocol import RpcResponse

logger = logging.getLogger("ShapezAI.Bridge")

class ShapezBridgeServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.app = web.Application(client_max_size=128 * 1024 * 1024)
        self.app.router.add_get("/", self._handle_ws)
        self.app.router.add_post("/api/rpc", self._handle_http_rpc)
        self.app.router.add_get("/api/status", self._handle_http_status)
        self.runner: Optional[web.AppRunner] = None
        self.active_ws: Optional[web.WebSocketResponse] = None
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.event_handlers: Dict[str, list[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}
        self.is_connected = asyncio.Event()

    def on_event(self, event_name: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Register an async handler for push events from the game."""
        self.event_handlers.setdefault(event_name, []).append(handler)

    async def start(self):
        """Start the WebSocket server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        logger.info(f"Shapez AI Bridge WebSocket server started on ws://{self.host}:{self.port}")

    async def stop(self):
        """Stop the server."""
        if self.active_ws and not self.active_ws.closed:
            await self.active_ws.close()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Bridge server stopped")

    async def wait_for_game(self, timeout: Optional[float] = None) -> bool:
        """Wait until Shapez Game Bridge connects."""
        try:
            await asyncio.wait_for(self.is_connected.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def _handle_ws(self, request):
        ws = web.WebSocketResponse(heartbeat=15.0, max_msg_size=128 * 1024 * 1024)
        await ws.prepare(request)

        logger.info("Game Bridge client connected")
        self.active_ws = ws
        self.is_connected.set()

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._dispatch_message(data)
                    except Exception as e:
                        logger.error(f"Error handling message: {e}", exc_info=True)
                elif msg.type == WSMsgType.ERROR:
                    logger.warning(f"WS error: {ws.exception()}")
        finally:
            logger.warning("Game Bridge client disconnected")
            self.active_ws = None
            self.is_connected.clear()
            # Fail all pending futures
            for fut in self.pending_requests.values():
                if not fut.done():
                    fut.set_exception(ConnectionResetError("Game disconnected"))
            self.pending_requests.clear()

        return ws

    async def _dispatch_message(self, data: Dict[str, Any]):
        msg_type = data.get("type")

        if msg_type == "response":
            req_id = data.get("id")
            if req_id in self.pending_requests:
                fut = self.pending_requests.pop(req_id)
                if not fut.done():
                    error = data.get("error")
                    if error:
                        fut.set_exception(RuntimeError(error))
                    else:
                        fut.set_result(data.get("result"))

        elif msg_type == "event":
            event_name = data.get("event")
            event_data = data.get("data", {})
            handlers = self.event_handlers.get(event_name, [])
            for handler in handlers:
                asyncio.create_task(handler(event_data))

    async def call(self, action: str, params: Optional[Dict[str, Any]] = None, timeout: float = 6.0) -> Any:
        """Send an RPC request to the game and wait for the response."""
        if not self.active_ws or self.active_ws.closed:
            raise ConnectionError("No active connection to Shapez game")

        req_id = str(uuid.uuid4())[:8]
        payload = {
            "type": "request",
            "id": req_id,
            "action": action,
            "params": params or {}
        }

        fut = asyncio.get_running_loop().create_future()
        self.pending_requests[req_id] = fut

        await self.active_ws.send_str(json.dumps(payload))
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self.pending_requests.pop(req_id, None)
            raise TimeoutError(f"RPC call '{action}' timed out after {timeout}s")

    async def _handle_http_status(self, request):
        return web.json_response({
            "connected": bool(self.active_ws and not self.active_ws.closed),
            "pending_requests": len(self.pending_requests)
        })

    async def _handle_http_rpc(self, request):
        try:
            body = await request.json()
            action = body.get("action")
            params = body.get("params", {})
            timeout = float(body.get("timeout", 6.0))
            res = await self.call(action, params, timeout=timeout)
            return web.json_response({"success": True, "result": res})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)
