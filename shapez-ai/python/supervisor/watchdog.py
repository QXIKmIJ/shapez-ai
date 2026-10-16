"""
Self-healing Production Watchdog for Shapez AI.
Monitors human interventions, conveyor disruptions, delivery latency, and production stalls.
Provides closed-loop verification: Planning -> Construction -> Verification -> Monitoring -> Diagnosis -> Repair.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import asyncio
import logging
import time
from typing import Dict, List, Set, Tuple, Optional, Any

try:
    from ..bridge.protocol import EntitySpec, DeleteCoord
    from ..planner.router import ConveyorRouter, manhattan_distance
except (ImportError, ValueError):
    from bridge.protocol import EntitySpec, DeleteCoord
    from planner.router import ConveyorRouter, manhattan_distance

logger = logging.getLogger("ShapezAI.Watchdog")

class ProductionLine:
    def __init__(
        self,
        line_id: str,
        target_shape: str,
        patch_tile: Tuple[int, int],
        entities: List[EntitySpec],
        hub_slot: Optional[Tuple[int, int]] = None
    ):
        self.line_id = line_id
        self.target_shape = target_shape
        self.patch_tile = patch_tile
        self.hub_slot = hub_slot or (0, 0)
        self.entities = entities  # Full list of EntitySpecs
        self.entity_map: Dict[Tuple[int, int], EntitySpec] = {
            (e.x, e.y): e for e in entities
        }
        self.created_at: float = time.time()
        self.last_progress_time: float = self.created_at
        self.last_delivered_count: int = 0
        self.last_throughput: float = 0.0
        self.repair_attempts: int = 0
        self.status: str = "transit_in_progress"
        self.last_issue: Optional[str] = None

        # Calculate estimated transit time based on Manhattan distance and conveyor speed (~2 tiles/s)
        dist = manhattan_distance(self.patch_tile, self.hub_slot)
        # Minimum 4s, distance / 2.0 + 3.0s buffer
        self.transit_time_est: float = max(4.0, (dist / 2.0) + 3.0)

    def contains_tile(self, tile: Tuple[int, int]) -> bool:
        return tile in self.entity_map

    def get_spec_at(self, tile: Tuple[int, int]) -> Optional[EntitySpec]:
        return self.entity_map.get(tile)

    def remove_tile(self, tile: Tuple[int, int]):
        if tile in self.entity_map:
            del self.entity_map[tile]
            self.entities = list(self.entity_map.values())

    def update_entities(self, new_entities: List[EntitySpec]):
        self.entities = new_entities
        self.entity_map = {(e.x, e.y): e for e in new_entities}
        self.created_at = time.time()
        self.last_progress_time = self.created_at
        self.status = "transit_in_progress"

class FactoryWatchdog:
    def __init__(self, router: ConveyorRouter):
        self.router = router
        self.lines: Dict[str, ProductionLine] = {}
        self.is_repairing = False
        self._repair_lock = asyncio.Lock()
        self.last_diagnosis_result: Optional[Dict[str, Any]] = None

    def register_line(
        self,
        line_id: str,
        target_shape: str,
        patch_tile: Tuple[int, int],
        entities: List[EntitySpec],
        hub_slot: Optional[Tuple[int, int]] = None
    ) -> ProductionLine:
        """Register a newly built production line for closed-loop monitoring."""
        line = ProductionLine(line_id, target_shape, patch_tile, entities, hub_slot)
        self.lines[line_id] = line
        logger.info(
            f"[Watchdog] Registered production line '{line_id}' with {len(entities)} components. "
            f"Estimated transit latency: {line.transit_time_est:.1f}s."
        )
        return line

    def get_active_line(self) -> Optional[ProductionLine]:
        """Returns the most recently registered active production line."""
        if not self.lines:
            return None
        return list(self.lines.values())[-1]

    def get_all_occupied_tiles(self) -> Set[Tuple[int, int]]:
        """Collect all currently registered entity tiles."""
        occupied = set()
        for line in self.lines.values():
            occupied.update(line.entity_map.keys())
        return occupied

    def check_health(
        self,
        current_throughput: float,
        current_delivered: int,
        game_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Closed-loop health check:
        1. Checks transit time buffer (prevents premature false repairs while items travel).
        2. Verifies delivery progress (increments or throughput > 0).
        3. Detects zero-progress stalls after transit buffer.
        4. Scans map entities for broken/missing components.
        5. Enforces escalation guardrails (max 3 retry attempts before re-strategizing).
        """
        now = time.time()
        line = self.get_active_line()
        if not line:
            return {
                "has_line": False,
                "status": "idle",
                "is_healthy": True,
                "stalled": False,
                "message": "No tracked production lines."
            }

        elapsed = now - line.created_at
        time_since_progress = now - line.last_progress_time
        line.last_throughput = current_throughput

        # 1. Check if delivery is actively occurring
        has_delivery_progress = current_delivered > line.last_delivered_count
        has_positive_throughput = current_throughput > 0.05

        if has_delivery_progress or has_positive_throughput:
            line.status = "operational"
            line.last_progress_time = now
            line.last_delivered_count = current_delivered
            line.repair_attempts = 0
            line.last_issue = None
            return {
                "has_line": True,
                "line_id": line.line_id,
                "status": "operational",
                "is_healthy": True,
                "stalled": False,
                "throughput": current_throughput,
                "delivered": current_delivered,
                "elapsed": elapsed,
                "transit_time_est": line.transit_time_est,
                "message": f"Factory is actively delivering '{line.target_shape}' ({current_throughput:.1f} items/s)."
            }

        # 2. Check if items are still in transit (conveyor travel time)
        if elapsed < line.transit_time_est:
            line.status = "transit_in_progress"
            remaining = line.transit_time_est - elapsed
            return {
                "has_line": True,
                "line_id": line.line_id,
                "status": "transit_in_progress",
                "is_healthy": True,
                "stalled": False,
                "throughput": 0.0,
                "delivered": current_delivered,
                "elapsed": elapsed,
                "transit_time_est": line.transit_time_est,
                "message": f"Items in transit from patch to Hub ({remaining:.1f}s remaining in transit buffer)."
            }

        # 3. Grace period exceeded without delivery -> STALL DETECTED
        stall_threshold = line.transit_time_est + 8.0
        if time_since_progress >= stall_threshold:
            line.status = "stalled"
            issue_desc = f"No delivery detected for {time_since_progress:.1f}s (transit estimate was {line.transit_time_est:.1f}s)."
            line.last_issue = issue_desc

            # Detailed topology inspection against actual game entities
            missing_entities: List[EntitySpec] = []
            if game_state and "entities" in game_state:
                map_entities = {(e["x"], e["y"]): e for e in game_state.get("entities", [])}
                for (tx, ty), spec in line.entity_map.items():
                    if (tx, ty) not in map_entities:
                        missing_entities.append(spec)

            is_blocked = line.repair_attempts >= 3
            return {
                "has_line": True,
                "line_id": line.line_id,
                "status": "stalled" if not is_blocked else "blocked",
                "is_healthy": False,
                "stalled": True,
                "is_blocked": is_blocked,
                "throughput": current_throughput,
                "delivered": current_delivered,
                "time_since_progress": time_since_progress,
                "repair_attempts": line.repair_attempts,
                "missing_entities_count": len(missing_entities),
                "missing_entities": [m.model_dump() for m in missing_entities[:10]],
                "message": issue_desc
            }

        # Waiting inside grace period
        return {
            "has_line": True,
            "line_id": line.line_id,
            "status": "monitoring",
            "is_healthy": True,
            "stalled": False,
            "throughput": current_throughput,
            "delivered": current_delivered,
            "elapsed": elapsed,
            "time_since_progress": time_since_progress,
            "message": "Monitoring line delivery buffer."
        }

    async def handle_destruction_event(
        self,
        event_data: Dict[str, Any],
        ws_server: Any
    ):
        """
        Handle push event 'event:entity_destroyed'.
        If it was manual destruction of an active production line, trigger rapid self-healing.
        """
        if not event_data.get("manual", False):
            return

        x = event_data.get("x")
        y = event_data.get("y")
        building = event_data.get("building", "unknown")
        destroyed_tile = (x, y)

        logger.warning(f"[Watchdog] Manual destruction detected: {building} at ({x}, {y})")

        affected_line: Optional[ProductionLine] = None
        original_spec: Optional[EntitySpec] = None

        for line in self.lines.values():
            if line.contains_tile(destroyed_tile):
                affected_line = line
                original_spec = line.get_spec_at(destroyed_tile)
                break

        if not affected_line:
            logger.info(f"[Watchdog] Destroyed entity at ({x}, {y}) is not part of tracked lines.")
            return

        logger.info(f"[Watchdog] Affected production line '{affected_line.line_id}'. Initiating repair protocol...")
        async with self._repair_lock:
            await self._repair_single_component(affected_line, destroyed_tile, original_spec, ws_server)

    async def _repair_single_component(
        self,
        line: ProductionLine,
        destroyed_tile: Tuple[int, int],
        original_spec: Optional[EntitySpec],
        ws_server: Any
    ):
        """Quickly rebuilds a single deleted component if valid."""
        try:
            try:
                await ws_server.call("set_hud_status", {
                    "status": "Repairing",
                    "thought": f"Восстановление разрушенного компонента в ({destroyed_tile[0]}, {destroyed_tile[1]})..."
                })
            except Exception:
                pass

            await asyncio.sleep(0.3)

            if original_spec:
                preflight = await ws_server.call("preflight_check", {
                    "entities": [original_spec.model_dump()]
                })

                if preflight and preflight.get("valid"):
                    logger.info(f"[Watchdog] Restoring exact entity {original_spec.building} at {destroyed_tile}")
                    res = await ws_server.call("execute_batch", {
                        "entities": [original_spec.model_dump()]
                    })
                    if res and res.get("success"):
                        exec_ms = res.get("executionTimeMs", 0.0)
                        logger.info(f"[Watchdog] Restored component at {destroyed_tile} in {exec_ms}ms")
                        line.created_at = time.time()
                        line.last_progress_time = time.time()
                        line.status = "operational"
                        try:
                            await ws_server.call("set_hud_status", {
                                "status": "Operational",
                                "thought": f"Компонент успешно восстановлен ({exec_ms}мс) в ({destroyed_tile[0]}, {destroyed_tile[1]})!"
                            })
                        except Exception:
                            pass
                        return

            # Fallback to full repair
            await self.repair_active_line(ws_server, line)

        except Exception as e:
            logger.error(f"[Watchdog] Error in _repair_single_component: {e}", exc_info=True)

    async def repair_active_line(
        self,
        ws_server: Any,
        target_line: Optional[ProductionLine] = None
    ) -> Dict[str, Any]:
        """
        Executes full autonomous repair of the active line:
        1. Checks retry count (escalation guardrail).
        2. Scans current world map.
        3. Identifies missing pieces or computes clean orthogonal re-routing.
        4. Validates preflight check.
        5. Executes batch placement.
        6. Resets transit latency timer for closed-loop verification.
        """
        line = target_line or self.get_active_line()
        if not line:
            return {"success": False, "error": "No active line to repair"}

        if line.repair_attempts >= 3:
            logger.warning(f"[Watchdog] Escalation triggered: Line '{line.line_id}' failed 3 repair attempts.")
            line.status = "blocked"
            return {
                "success": False,
                "error": "escalation_limit_reached",
                "message": f"Линия {line.line_id} не восстанавливается после 3 попыток. Требуется смена стратегии или ручной выбор залежи."
            }

        async with self._repair_lock:
            try:
                line.repair_attempts += 1
                logger.info(f"[Watchdog] Executing repair attempt #{line.repair_attempts} for '{line.line_id}'...")

                try:
                    await ws_server.call("set_hud_status", {
                        "status": "Repairing",
                        "thought": f"Попытка ремонта #{line.repair_attempts}: восстановление связности конвейера..."
                    })
                except Exception:
                    pass

                game_state = await ws_server.call("get_game_state")
                all_obstacles = set()
                map_entities = {}
                if game_state and "entities" in game_state:
                    for ent in game_state["entities"]:
                        pos = (ent["x"], ent["y"])
                        map_entities[pos] = ent
                        if pos != line.patch_tile:
                            all_obstacles.add(pos)

                # Strategy 1: Find missing specs from the original plan and replace them
                missing_specs = []
                for (tx, ty), spec in line.entity_map.items():
                    if (tx, ty) not in map_entities:
                        missing_specs.append(spec)

                if missing_specs:
                    logger.info(f"[Watchdog] Strategy 1: Placing {len(missing_specs)} missing components...")
                    pre_res = await ws_server.call("preflight_check", {
                        "entities": [s.model_dump() for s in missing_specs]
                    })
                    if pre_res and pre_res.get("valid"):
                        exec_res = await ws_server.call("execute_batch", {
                            "entities": [s.model_dump() for s in missing_specs]
                        })
                        if exec_res and exec_res.get("success"):
                            exec_ms = exec_res.get("executionTimeMs", 0.0)
                            logger.info(f"[Watchdog] Missing components placed successfully in {exec_ms}ms!")
                            line.created_at = time.time()
                            line.last_progress_time = time.time()
                            line.status = "transit_in_progress"
                            return {
                                "success": True,
                                "strategy": "missing_components",
                                "placedCount": len(missing_specs),
                                "executionTimeMs": exec_ms
                            }

                # Strategy 2: Full re-route from patch to nearest free Hub slot
                logger.info(f"[Watchdog] Strategy 2: Re-planning full path from patch {line.patch_tile}...")
                old_coords = [{"x": x, "y": y} for (x, y) in line.entity_map.keys()]
                if old_coords:
                    await ws_server.call("delete_batch", {"coords": old_coords})

                clear_obstacles = all_obstacles - set(line.entity_map.keys())
                hub_slot, entry_dir = self.router.find_nearest_hub_slot(line.patch_tile, obstacles=clear_obstacles)
                new_specs = self.router.plan_miner_and_conveyor(
                    line.patch_tile,
                    hub_slot,
                    entry_dir,
                    clear_obstacles
                )

                if not new_specs:
                    return {"success": False, "error": "No valid re-route path found"}

                pre_res = await ws_server.call("preflight_check", {
                    "entities": [s.model_dump() for s in new_specs]
                })
                if not pre_res or not pre_res.get("valid"):
                    return {"success": False, "error": f"Preflight failed: {pre_res}"}

                exec_res = await ws_server.call("execute_batch", {
                    "entities": [s.model_dump() for s in new_specs]
                })

                if exec_res and exec_res.get("success"):
                    exec_ms = exec_res.get("executionTimeMs", 0.0)
                    logger.info(f"[Watchdog] Full re-route placed successfully ({len(new_specs)} entities in {exec_ms}ms)!")
                    line.update_entities(new_specs)
                    line.hub_slot = hub_slot
                    line.status = "transit_in_progress"
                    return {
                        "success": True,
                        "strategy": "full_reroute",
                        "placedCount": len(new_specs),
                        "executionTimeMs": exec_ms
                    }
                else:
                    return {"success": False, "error": f"Execute batch failed: {exec_res}"}

            except Exception as e:
                logger.error(f"[Watchdog] Exception during repair_active_line: {e}", exc_info=True)
                return {"success": False, "error": str(e)}
