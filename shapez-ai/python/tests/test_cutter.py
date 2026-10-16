"""
Unit tests for Cutter and Trash line planning.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from planner.router import ConveyorRouter
from planner.shape_analyzer import analyze_target_goal

class TestCutterPlanning(unittest.TestCase):
    def setUp(self):
        self.router = ConveyorRouter()

    def test_shape_analyzer_cut(self):
        req_raw = analyze_target_goal("CuCuCuCu")
        self.assertEqual(req_raw.op_type, "raw")
        self.assertEqual(req_raw.raw_shape, "CuCuCuCu")

        req_cut0 = analyze_target_goal("----CuCu")
        self.assertEqual(req_cut0.op_type, "cut")
        self.assertEqual(req_cut0.raw_shape, "CuCuCuCu")
        self.assertEqual(req_cut0.keep_half, 0)

        req_cut1 = analyze_target_goal("CuCu----")
        self.assertEqual(req_cut1.op_type, "cut")
        self.assertEqual(req_cut1.raw_shape, "CuCuCuCu")
        self.assertEqual(req_cut1.keep_half, 1)

    def test_cutter_line_planning(self):
        patch_tile = (-10, 8)
        hub_slot = (-2, 2)
        entry_dir = 0
        obstacles = set()

        plan = self.router.plan_cutter_and_conveyor(
            patch_tile=patch_tile,
            hub_entry_tile=hub_slot,
            entry_direction=entry_dir,
            obstacles=obstacles,
            keep_half=0
        )

        self.assertIsNotNone(plan)
        buildings = [e.building for e in plan]
        self.assertIn("miner", buildings)
        self.assertIn("cutter", buildings)
        self.assertIn("trash", buildings)
        self.assertIn("belt", buildings)

        # Check miner is on patch
        miner = next(e for e in plan if e.building == "miner")
        self.assertEqual((miner.x, miner.y), patch_tile)

        # Check cutter and trash exist
        cutter = next(e for e in plan if e.building == "cutter")
        trash = next(e for e in plan if e.building == "trash")
        self.assertIn(cutter.rotation, [0, 90, 180, 270])
        self.assertIn(trash.rotation, [0, 90, 180, 270])

    def test_cutter_rotation_variants(self):
        patch_tile = (-10, 8)
        hub_slot = (-2, 2)
        entry_dir = 0
        obstacles = set()

        for rot, expected_variant in [(90, "default"), (180, "rotate180"), (270, "ccw")]:
            plan = self.router.plan_cutter_and_conveyor(
                patch_tile=patch_tile,
                hub_entry_tile=hub_slot,
                entry_direction=entry_dir,
                obstacles=obstacles,
                keep_half=1,
                rotation=rot
            )
            self.assertIsNotNone(plan)
            buildings = [e.building for e in plan]
            self.assertIn("rotater", buildings)
            rotater = next(e for e in plan if e.building == "rotater")
            self.assertEqual(rotater.variant, expected_variant)

    def test_cut_and_paint_line_rotation(self):
        shape_patch = (12, 12)
        color_patch = (22, 22)
        hub_slot = (1, 2)
        entry_dir = 0
        obstacles = set()

        for rot, expected_variant in [(0, None), (90, "default"), (180, "rotate180"), (270, "ccw")]:
            plan = self.router.plan_cut_and_paint_line(
                shape_patch_tile=shape_patch,
                color_patch_tile=color_patch,
                hub_entry_tile=hub_slot,
                entry_direction=entry_dir,
                obstacles=obstacles,
                keep_half=0,
                rotation=rot
            )
            self.assertIsNotNone(plan)
            buildings = [e.building for e in plan]
            self.assertIn("cutter", buildings)
            self.assertIn("painter", buildings)
            if expected_variant:
                self.assertIn("rotater", buildings)
                rotater = next(e for e in plan if e.building == "rotater")
                self.assertEqual(rotater.variant, expected_variant)
            else:
                self.assertNotIn("rotater", buildings)

if __name__ == "__main__":
    unittest.main()

