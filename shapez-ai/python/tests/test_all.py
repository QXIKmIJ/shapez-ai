"""
Comprehensive Unit & Integration Test Suite for Shapez AI MVP.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import unittest
import asyncio
from typing import Set, Tuple

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from planner.shape_analyzer import ParsedShape, ShapeLayer, Quadrant
from planner.router import ConveyorRouter, manhattan_distance, OFFSETS
from bridge.protocol import EntitySpec
from supervisor.watchdog import FactoryWatchdog, ProductionLine

class TestShapeAnalyzer(unittest.TestCase):
    def test_parse_raw_circle(self):
        shape = ParsedShape.from_code("CuCuCuCu")
        self.assertEqual(shape.num_layers, 1)
        self.assertTrue(shape.is_pure_raw())
        self.assertEqual(shape.to_code(), "CuCuCuCu")

    def test_rotation(self):
        # Layer: TR=Ru, BR=Cu, BL=Su, TL=Wu
        layer = ShapeLayer.from_string("RuCuSuWu")
        # Rotate CW: TL->TR, TR->BR, BR->BL, BL->TL -> WuRuCuSu
        cw = layer.rotate_cw()
        self.assertEqual(cw.to_code(), "WuRuCuSu")

    def test_cutter(self):
        layer = ShapeLayer.from_string("RuCuSuWu")
        left, right = layer.cut_half()
        # Left half has BL(Su) and TL(Wu), TR and BR empty: -- -- Su Wu -> ----SuWu
        self.assertEqual(left.to_code(), "----SuWu")
        # Right half has TR(Ru) and BR(Cu), BL and TL empty: Ru Cu -- -- -> RuCu----
        self.assertEqual(right.to_code(), "RuCu----")

class TestConveyorRouter(unittest.TestCase):
    def setUp(self):
        self.router = ConveyorRouter()

    def test_hub_perimeter_slots(self):
        # Test finding slot for a patch to the east (x=10, y=0)
        slot, entry_dir = self.router.find_nearest_hub_slot((10, 0))
        # Nearest slot should be on east face (x=2, y in [-2..1])
        self.assertEqual(slot[0], 2)
        # Entry direction into east face should be 270 (moving left/west)
        self.assertEqual(entry_dir, 270)

        # Test finding slot for a patch to the north (x=0, y=-10)
        slot, entry_dir = self.router.find_nearest_hub_slot((0, -10))
        self.assertEqual(slot[1], -3)
        self.assertEqual(entry_dir, 180)  # moving down/south

    def test_astar_straight_path(self):
        start = (5, 0)
        goal = (2, 0)
        obstacles: Set[Tuple[int, int]] = set()
        path = self.router.find_path(start, goal, obstacles)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], start)
        self.assertEqual(path[-1], goal)
        self.assertEqual(len(path), 4)  # (5,0), (4,0), (3,0), (2,0)

    def test_astar_with_obstacle(self):
        start = (4, 0)
        goal = (2, 0)
        obstacles = {(3, 0)}  # Obstacle directly in between
        path = self.router.find_path(start, goal, obstacles)
        self.assertIsNotNone(path)
        self.assertNotIn((3, 0), path)
        self.assertEqual(path[0], start)
        self.assertEqual(path[-1], goal)

    def test_path_to_belts_rotations(self):
        # Moving west: (4, 0) -> (3, 0) -> (2, 0)
        path = [(4, 0), (3, 0), (2, 0)]
        belts = self.router.path_to_belts(path, final_rotation=270)
        self.assertEqual(len(belts), 3)
        for b in belts:
            self.assertEqual(b.rotation, 270)  # all pointing west

class TestWatchdog(unittest.TestCase):
    def setUp(self):
        self.router = ConveyorRouter()
        self.watchdog = FactoryWatchdog(self.router)

    def test_line_registration_and_lookup(self):
        entities = [
            EntitySpec(building="miner", x=5, y=0, rotation=270),
            EntitySpec(building="belt", x=4, y=0, rotation=270),
            EntitySpec(building="belt", x=3, y=0, rotation=270),
            EntitySpec(building="belt", x=2, y=0, rotation=270),
        ]
        self.watchdog.register_line("test_line", "CuCuCuCu", (5, 0), entities)
        line = self.watchdog.lines.get("test_line")
        self.assertIsNotNone(line)
        self.assertTrue(line.contains_tile((4, 0)))
        self.assertEqual(line.get_spec_at((4, 0)).building, "belt")
        self.assertFalse(line.contains_tile((10, 10)))

if __name__ == "__main__":
    unittest.main()
