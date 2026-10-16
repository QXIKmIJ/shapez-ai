"""
End-to-End Simulation Test for Shapez AI MVP.
Simulates Game Bridge interactions: connection, planning, batch placement,
human destruction, and self-healing watchdog repair.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import asyncio
import json
import unittest
from typing import Dict, Any, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiohttp
from main import ShapezAiOrchestrator
from bridge.protocol import EntitySpec

TEST_WS_PORT = 8766

class MockShapezGame:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws: Any = None
        self.session: Any = None
        self.placed_entities: List[Dict[str, Any]] = []
        self.hud_history: List[Dict[str, str]] = []
        self.preflight_called = False
        self.execute_called = False
        self.repair_executed = False

    async def connect(self):
        self.session = aiohttp.ClientSession()
        self.ws = await self.session.ws_connect(self.ws_url)

    async def close(self):
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()

    async def send_event(self, event_name: str, data: Dict[str, Any]):
        await self.ws.send_str(json.dumps({
            "type": "event",
            "event": event_name,
            "data": data
        }))

    async def handle_requests(self, stop_after_repair: asyncio.Event):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("type") == "request":
                    req_id = data.get("id")
                    action = data.get("action")
                    params = data.get("params", {})

                    if action == "set_hud_status":
                        self.hud_history.append(params)
                        await self.ws.send_str(json.dumps({
                            "type": "response",
                            "id": req_id,
                            "result": {"success": True}
                        }))

                    elif action == "get_game_state":
                        state = {
                            "ready": True,
                            "revision": 1,
                            "level": 1,
                            "goal": {"shape": "CuCuCuCu", "required": 30, "delivered": 0},
                            "patches": [{"type": "shape", "item": "CuCuCuCu", "tileX": 10, "tileY": 2, "size": 16}],
                            "entities": self.placed_entities,
                            "unlockedBuildings": ["miner", "belt"]
                        }
                        await self.ws.send_str(json.dumps({
                            "type": "response",
                            "id": req_id,
                            "result": state
                        }))

                    elif action == "preflight_check":
                        self.preflight_called = True
                        await self.ws.send_str(json.dumps({
                            "type": "response",
                            "id": req_id,
                            "result": {"valid": True, "count": len(params.get("entities", []))}
                        }))

                    elif action == "execute_batch":
                        self.execute_called = True
                        entities = params.get("entities", [])
                        self.placed_entities.extend(entities)
                        if len(entities) == 1 and entities[0].get("building") == "belt":
                            # This was the single-tile repair!
                            self.repair_executed = True
                            stop_after_repair.set()

                        await self.ws.send_str(json.dumps({
                            "type": "response",
                            "id": req_id,
                            "result": {"success": True, "placedCount": len(entities), "revision": 2}
                        }))

                    elif action == "delete_batch":
                        coords = params.get("coords", [])
                        await self.ws.send_str(json.dumps({
                            "type": "response",
                            "id": req_id,
                            "result": {"success": True, "deletedCount": len(coords)}
                        }))


class TestEndToEndMVP(unittest.IsolatedAsyncioTestCase):
    async def test_full_autonomous_cycle(self):
        # 1. Start Orchestrator on test port
        orchestrator = ShapezAiOrchestrator(
            ws_port=TEST_WS_PORT,
            llm_url="http://127.0.0.1:18088/v1"
        )
        await orchestrator.server.start()

        stop_repair_event = asyncio.Event()
        mock_game = MockShapezGame(f"ws://127.0.0.1:{TEST_WS_PORT}")

        try:
            # 2. Connect Mock Game
            await mock_game.connect()
            listener_task = asyncio.create_task(mock_game.handle_requests(stop_repair_event))

            # 3. Game signals ready
            await mock_game.send_event("bridge:connected", {"version": "0.1.0"})
            await mock_game.send_event("game:ready", {
                "ready": True,
                "revision": 1,
                "level": 1,
                "goal": {"shape": "CuCuCuCu", "required": 30, "delivered": 0},
                "patches": [{"type": "shape", "item": "CuCuCuCu", "tileX": 10, "tileY": 2, "size": 16}]
            })

            # Wait for planning and placement
            for _ in range(30):
                if mock_game.execute_called:
                    break
                await asyncio.sleep(0.5)

            self.assertTrue(mock_game.preflight_called, "Preflight check should have been called")
            self.assertTrue(mock_game.execute_called, "Execute batch should have been called")
            self.assertGreater(len(mock_game.placed_entities), 0, "Entities should be placed")

            # 4. Human Intervention: Manually destroy a belt in the middle of the line!
            broken_tile = mock_game.placed_entities[2]  # Pick 3rd entity (a conveyor belt)
            bx, by = broken_tile["x"], broken_tile["y"]

            await mock_game.send_event("event:entity_destroyed", {
                "manual": True,
                "building": "belt",
                "x": bx,
                "y": by,
                "rotation": broken_tile["rotation"],
                "worldRevision": 3
            })

            # 5. Wait for Watchdog to detect and repair
            try:
                await asyncio.wait_for(stop_repair_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass

            self.assertTrue(mock_game.repair_executed, "Watchdog should have executed repair batch")

            # Check HUD status log
            statuses = [h.get("status") for h in mock_game.hud_history]
            self.assertIn("Repairing", statuses, "HUD should show 'Repairing' status during intervention")
            self.assertIn("Operational", statuses, "HUD should return to 'Operational' after repair")

            listener_task.cancel()
        finally:
            await mock_game.close()
            await orchestrator.server.stop()

if __name__ == "__main__":
    unittest.main()
