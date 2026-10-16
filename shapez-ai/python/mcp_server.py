"""
Model Context Protocol (MCP) Server for Shapez AI.
Allows external AI agents and MCP clients to query game state, inspect reasoning, and control factories.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import asyncio
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server import Server as MCPServer

ORCHESTRATOR_URL = "http://127.0.0.1:8765"

server = MCPServer("shapez-ai")

def _http_request(endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{ORCHESTRATOR_URL}{endpoint}"
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"} if payload else {}
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "success": False}

@server.tool()
def list_sessions() -> List[Dict[str, Any]]:
    """List all active and persisted game sessions in Shapez AI."""
    res = _http_request("/api/sessions")
    if "sessions" in res:
        return res["sessions"]
    # Fallback to single session
    s = _http_request("/api/session")
    return [s] if "session_id" in s else []

@server.tool()
def get_session_state(session_id: str = "session_primary") -> Dict[str, Any]:
    """Retrieve full telemetry, goals, and cognitive reasoning history for a session."""
    return _http_request(f"/api/session?session_id={session_id}")

@server.tool()
def get_game_state(session_id: str = "session_primary") -> Dict[str, Any]:
    """Fetch live real-time game state (hub goals, patches, placed buildings, inventory) from the game client."""
    return _http_request("/api/rpc", method="POST", data={
        "action": "get_game_state",
        "params": {},
        "session_id": session_id
    })

@server.tool()
def plan_and_build(session_id: str = "session_primary") -> Dict[str, Any]:
    """Trigger autonomous AI strategic planning and building for the current level goal."""
    return _http_request(f"/api/plan?session_id={session_id}", method="POST")

@server.tool()
def inspect_tile(x: int, y: int, session_id: str = "session_primary") -> Dict[str, Any]:
    """Inspect world tile at coordinates (x, y) to check lower layer resources and placed buildings."""
    return _http_request("/api/rpc", method="POST", data={
        "action": "inspect_tile",
        "params": {"x": x, "y": y},
        "session_id": session_id
    })

@server.tool()
def eval_code(code: str, session_id: str = "session_primary") -> Dict[str, Any]:
    """Evaluate arbitrary JavaScript code inside the running shapez.io game client."""
    return _http_request("/api/rpc", method="POST", data={
        "action": "eval_code",
        "params": {"code": code},
        "session_id": session_id
    })

if __name__ == "__main__":
    # Run stdio MCP server for agent clients
    server.run()
