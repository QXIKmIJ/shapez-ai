"""
Unit and Integration Tests for Closed-Loop Verification, Agentic Chat Tools, and Level Transitions.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import asyncio
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from supervisor.watchdog import FactoryWatchdog, ProductionLine
from planner.router import ConveyorRouter
from bridge.protocol import EntitySpec
from supervisor.tools import AgentToolExecutor
from supervisor.session_manager import SessionManager

class TestWatchdogClosedLoop(unittest.TestCase):
    def setUp(self):
        self.router = ConveyorRouter()
        self.watchdog = FactoryWatchdog(self.router)

    def test_transit_time_buffer_prevents_false_stall(self):
        specs = [
            EntitySpec(building="miner", x=10, y=0, rotation=270),
            EntitySpec(building="belt", x=9, y=0, rotation=270),
            EntitySpec(building="belt", x=8, y=0, rotation=270),
            EntitySpec(building="belt", x=7, y=0, rotation=270),
        ]
        line = self.watchdog.register_line(
            line_id="test_line_1",
            target_shape="CuCuCuCu",
            patch_tile=(10, 0),
            entities=specs,
            hub_slot=(0, 0)
        )

        # Distance is 10, transit time estimate is 10/2 + 3 = 8.0s
        self.assertGreaterEqual(line.transit_time_est, 8.0)

        # 1. Right after construction: 0 throughput and 0 delivered, but elapsed < transit_time_est
        health = self.watchdog.check_health(current_throughput=0.0, current_delivered=0)
        self.assertEqual(health["status"], "transit_in_progress")
        self.assertFalse(health["stalled"])
        self.assertTrue(health["is_healthy"])

    def test_delivery_marks_operational(self):
        specs = [EntitySpec(building="miner", x=5, y=0, rotation=270)]
        line = self.watchdog.register_line("test_line_2", "CuCuCuCu", (5, 0), specs, (0, 0))

        # Delivery occurred
        health = self.watchdog.check_health(current_throughput=3.5, current_delivered=12)
        self.assertEqual(health["status"], "operational")
        self.assertTrue(health["is_healthy"])
        self.assertFalse(health["stalled"])

    def test_stall_detected_after_transit_and_grace_period(self):
        specs = [EntitySpec(building="miner", x=2, y=0, rotation=270)]
        line = self.watchdog.register_line("test_line_3", "CuCuCuCu", (2, 0), specs, (0, 0))

        # Simulate time passed past transit + grace period
        line.created_at = time.time() - 30.0
        line.last_progress_time = time.time() - 30.0

        health = self.watchdog.check_health(
            current_throughput=0.0,
            current_delivered=0,
            game_state={"entities": []}
        )
        self.assertEqual(health["status"], "stalled")
        self.assertTrue(health["stalled"])
        self.assertFalse(health["is_healthy"])
        self.assertEqual(health["missing_entities_count"], 1)

    def test_escalation_guardrail_after_3_attempts(self):
        specs = [EntitySpec(building="miner", x=2, y=0, rotation=270)]
        line = self.watchdog.register_line("test_line_4", "CuCuCuCu", (2, 0), specs, (0, 0))
        line.repair_attempts = 3
        line.created_at = time.time() - 30.0
        line.last_progress_time = time.time() - 30.0

        health = self.watchdog.check_health(current_throughput=0.0, current_delivered=0)
        self.assertEqual(health["status"], "blocked")
        self.assertTrue(health["is_blocked"])

class TestAgentToolExecutor(unittest.IsolatedAsyncioTestCase):
    async def test_tool_diagnose_factory(self):
        mock_orchestrator = MagicMock()
        mock_server = MagicMock()
        mock_server.active_ws = MagicMock()
        mock_server.active_ws.closed = False
        mock_server.call = AsyncMock(side_effect=lambda action, *args: {
            "diagnose_factory": {
                "level": 3,
                "goal": {"shape": "CuCuCuCu", "delivered": 5, "required": 30, "throughput": 1.2},
                "miners": [{"x": 10, "y": 2, "minedItem": "CuCuCuCu"}],
                "processors": [],
                "hubEntrances": [{"beltX": 1, "beltY": -2}],
                "beltCount": 12
            },
            "get_game_state": {
                "level": 3,
                "goal": {"shape": "CuCuCuCu", "delivered": 5, "required": 30},
                "entities": [{"x": 10, "y": 2, "building": "miner"}]
            }
        }.get(action, {}))

        mock_orchestrator.server = mock_server
        mock_orchestrator.watchdog = FactoryWatchdog(ConveyorRouter())
        mock_orchestrator.session_mgr = SessionManager()

        executor = AgentToolExecutor(mock_orchestrator)
        diag = await executor.execute_tool("diagnose_factory", {}, "test_sess")

        self.assertTrue(diag["success"])
        self.assertEqual(diag["level"], 3)
        self.assertEqual(diag["delivered"], 5)
        self.assertTrue(diag["is_working"])
        self.assertIn("Фабрика функционирует нормально", diag["summary"])

    async def test_repair_factory_respects_pause(self):
        mock_orchestrator = MagicMock()
        session_mgr = SessionManager()
        session_mgr.set_paused("test_paused_sess", True)

        mock_orchestrator.session_mgr = session_mgr
        executor = AgentToolExecutor(mock_orchestrator)

        repair_res = await executor.execute_tool("repair_factory", {"reason": "test"}, "test_paused_sess")
        self.assertFalse(repair_res["success"])
        self.assertTrue(repair_res["paused"])
        self.assertIn("ИИ на паузе", repair_res["error"])

if __name__ == "__main__":
    unittest.main()
