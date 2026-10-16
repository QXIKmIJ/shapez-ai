"""
Comprehensive integration tests for Shapez AI N-0.3.0 features:
- In-Game HUD & Web Pause/Resume
- Interactive Two-Way Chat & Preference Adaptation
- Persistent SQLite Decision History & Full-Text Search
- Installed Mod Registry & Capabilities Catalog
- Upgrades Tracking & Unlock Engine
Author: QXIK_mIJ
License: Apache License 2.0
"""

import unittest
import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supervisor.session_manager import SessionManager, ReasoningEntry, ActionRecord, ChatMessage
from supervisor.history_db import HistoryDB
from mods.mod_registry import ModRegistry
from planner.router import ConveyorRouter
from planner.shape_analyzer import analyze_target_goal
from llm.prompts import make_planning_prompt, make_chat_prompt

class TestN030Features(unittest.TestCase):
    def setUp(self):
        self.session_mgr = SessionManager()
        self.test_session_id = f"test_session_{int(time.time() * 1000)}"
        self.session = self.session_mgr.get_or_create(self.test_session_id)

    def test_pause_resume_persistence(self):
        # 1. Defaults to paused on startup
        self.assertTrue(self.session.is_paused)

        # 2. Resume AI
        resumed = self.session_mgr.set_paused(self.test_session_id, False)
        self.assertFalse(resumed)
        self.assertFalse(self.session_mgr.is_paused(self.test_session_id))

        # 3. Reload from disk to verify offline persistence
        fresh_mgr = SessionManager()
        loaded = fresh_mgr.get_or_create(self.test_session_id)
        self.assertFalse(loaded.is_paused)

        # 4. Pause again
        paused = self.session_mgr.set_paused(self.test_session_id, True)
        self.assertTrue(paused)
        fresh_mgr2 = SessionManager()
        loaded2 = fresh_mgr2.get_or_create(self.test_session_id)
        self.assertTrue(loaded2.is_paused)

    def test_user_preferences_adaptation(self):
        # Default preferences
        prefs = self.session.preferences
        self.assertTrue(prefs.get("compact"))
        self.assertTrue(prefs.get("aesthetic"))

        # Player requests symmetry and custom bus corridor
        self.session_mgr.update_preferences(self.test_session_id, {
            "symmetric": True,
            "corridor_width": 2,
            "preserve_old_lines": True
        })

        fresh_state = self.session_mgr.get_or_create(self.test_session_id)
        self.assertTrue(fresh_state.preferences.get("preserve_old_lines"))
        self.assertEqual(fresh_state.preferences.get("corridor_width"), 2)

    def test_chat_message_recording(self):
        msg1 = ChatMessage(sender="player", text="Сделай этот завод компактнее")
        self.session_mgr.add_chat_message(self.test_session_id, msg1)

        msg2 = ChatMessage(sender="ai", text="Указание принято. Минимизирую длину магистралей.")
        self.session_mgr.add_chat_message(self.test_session_id, msg2)

        state = self.session_mgr.get_or_create(self.test_session_id)
        self.assertEqual(len(state.chat_history), 2)
        self.assertEqual(state.chat_history[0].text, "Сделай этот завод компактнее")
        self.assertEqual(state.chat_history[1].sender, "ai")

    def test_sqlite_persistent_history_and_search(self):
        db = self.session_mgr.history_db
        entry_id = f"e_{int(time.time()*1000)}"
        entry = {
            "id": entry_id,
            "timestamp": time.time(),
            "level": 3,
            "goal_shape": "RuRu----",
            "model": "Qwen3.5-9B-Q8_0",
            "reasoning_content": "<think>Analysing cutter placement on patch (-10, 8)</think>",
            "thought": "Симметричное модульное размещение резчика",
            "plan_action": "cutter_and_deliver_RuRu----",
            "chosen_patch": {"tileX": -10, "tileY": 8},
            "dispatched_actions": [{"command": "execute_batch", "placedCount": 21}],
            "llm_latency_ms": 1450.0,
            "execution_latency_ms": 3.2,
            "status": "success"
        }

        db.insert_entry(self.test_session_id, entry)

        # 1. Search by keyword in thought
        res = db.search_history(session_id=self.test_session_id, query="Симметричное")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], entry_id)

        # 2. Search by level filter
        res_lvl = db.search_history(session_id=self.test_session_id, level=3)
        self.assertEqual(len(res_lvl), 1)

        # 3. Search non-existent level
        res_none = db.search_history(session_id=self.test_session_id, level=99)
        self.assertEqual(len(res_none), 0)

        # 4. Search by status
        res_success = db.search_history(session_id=self.test_session_id, status="success")
        self.assertGreaterEqual(len(res_success), 1)

    def test_mod_registry(self):
        registry = ModRegistry()
        self.assertGreaterEqual(len(registry.installed_mods), 10)
        self.assertIn("mirrored_buildings", registry.installed_mods)
        self.assertIn("packaging", registry.installed_mods)
        self.assertIn("add-building-basic", registry.installed_mods)

        mirrored_mod = registry.installed_mods["mirrored_buildings"]
        building_ids = [b.building_id for b in mirrored_mod.new_buildings]
        self.assertIn("cutter_mirrored", building_ids)
        self.assertIn("stacker_mirrored", building_ids)

        prompt_summary = registry.get_prompt_summary()
        self.assertIn("4 way Balancer", prompt_summary)
        self.assertIn("Mirrored Buildings", prompt_summary)

    def test_smart_aesthetic_routing(self):
        router = ConveyorRouter()
        # Direct straight path with turn penalty
        path = router.find_path((0, 10), (0, 2), set())
        self.assertIsNotNone(path)
        # Should be a strictly straight line along y axis: all x must be 0
        for pt in path:
            self.assertEqual(pt[0], 0)

        # Path requiring one turn: (0, 10) -> (5, 2)
        path2 = router.find_path((0, 10), (5, 2), set())
        self.assertIsNotNone(path2)
        belts = router.path_to_belts(path2, start_direction=0, final_rotation=0)
        self.assertEqual(len(belts), len(path2))

if __name__ == "__main__":
    unittest.main()
