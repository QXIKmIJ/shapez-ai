"""
Agent Tool Execution Engine for Shapez AI.
Empowers Two-Way Chat and Autonomous Loops with real, non-fictitious game tools:
- diagnose_factory: Deep real-time topology, miner, belt, and Hub delivery diagnostic scan.
- repair_factory: Autonomous self-healing and re-routing (respects Pause AI).
- replan_factory: Re-plans current level with updated preferences (respects Pause AI).
- inspect_tile: Inspects exact tile entity and layer contents.
- get_game_status: Retrieves level, target shape, throughput, and line status.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger("ShapezAI.Tools")

class AgentToolExecutor:
    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator

    @property
    def server(self):
        return self.orchestrator.server

    @property
    def watchdog(self):
        return self.orchestrator.watchdog

    @property
    def session_mgr(self):
        return self.orchestrator.session_mgr

    async def execute_tool(self, tool_name: str, args: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Dispatches and executes a real tool call."""
        t0 = time.time()
        logger.info(f"[ToolExecutor] Executing '{tool_name}' with args={args} (session: {session_id})")

        try:
            if tool_name == "diagnose_factory":
                res = await self.diagnose_factory(session_id=session_id)
            elif tool_name == "repair_factory":
                res = await self.repair_factory(session_id=session_id, reason=args.get("reason", "Player request"))
            elif tool_name == "replan_factory":
                res = await self.replan_factory(session_id=session_id, preferences=args.get("preferences"))
            elif tool_name == "inspect_tile":
                res = await self.inspect_tile(x=int(args.get("x", 0)), y=int(args.get("y", 0)))
            elif tool_name == "get_game_status":
                res = await self.get_game_status(session_id=session_id)
            else:
                res = {"success": False, "error": f"Unknown tool: {tool_name}"}

            duration_ms = round((time.time() - t0) * 1000.0, 1)
            res["duration_ms"] = duration_ms
            return res

        except Exception as e:
            duration_ms = round((time.time() - t0) * 1000.0, 1)
            logger.error(f"[ToolExecutor] Error executing '{tool_name}': {e}", exc_info=True)
            return {"success": False, "error": str(e), "duration_ms": duration_ms}

    async def diagnose_factory(self, session_id: str) -> Dict[str, Any]:
        """
        Runs full diagnostic inspection of the active factory and world state:
        - Scans miner placement and resource extraction
        - Scans processing equipment (cutters, rotaters)
        - Scans conveyor continuity and Hub entries
        - Inspects current delivery throughput and goal progress
        - Queries Watchdog health report
        """
        if not self.server.active_ws or self.server.active_ws.closed:
            return {"success": False, "error": "Game bridge is not connected"}

        # 1. Query rich in-game diagnosis RPC
        bridge_diag = await self.server.call("diagnose_factory")
        # 2. Query game state
        game_state = await self.server.call("get_game_state")

        level = bridge_diag.get("level", 1) if bridge_diag else 1
        goal = bridge_diag.get("goal", {}) if bridge_diag else {}
        target_shape = goal.get("shape", "unknown")
        delivered = goal.get("delivered", 0)
        required = goal.get("required", 0)
        throughput = goal.get("throughput", 0.0)

        miners = bridge_diag.get("miners", []) if bridge_diag else []
        processors = bridge_diag.get("processors", []) if bridge_diag else []
        hub_entrances = bridge_diag.get("hubEntrances", []) if bridge_diag else []
        belt_count = bridge_diag.get("beltCount", 0) if bridge_diag else 0

        # 3. Check watchdog health
        watchdog_report = self.watchdog.check_health(
            current_throughput=throughput,
            current_delivered=delivered,
            game_state=game_state
        )

        issues: List[str] = []
        is_working = throughput > 0.05 or delivered > 0

        if not miners:
            issues.append("На карте отсутствуют майнеры (нет добычи сырья).")
        else:
            # Check if miners are extracting the right raw shape
            has_matching_miner = False
            for m in miners:
                if m.get("minedItem"):
                    has_matching_miner = True
                    break
            if not has_matching_miner:
                issues.append("Майнеры установлены вне залежей ресурсов или заблокированы.")

        if belt_count == 0:
            issues.append("Конвейерные ленты отсутствуют на карте.")

        if not hub_entrances:
            issues.append("Нет ни одного конвейера, направленного во вход Хаба.")

        if watchdog_report.get("stalled"):
            issues.append(f"Зафиксирован простой: нет доставки в течение {watchdog_report.get('time_since_progress', 0):.1f}с.")
            missing_cnt = watchdog_report.get("missing_entities_count", 0)
            if missing_cnt > 0:
                issues.append(f"Обнаружено {missing_cnt} отсутствующих/разрушенных компонентов фабрики.")

        is_paused = self.session_mgr.is_paused(session_id)
        orch_state = getattr(self.orchestrator, "state", "IDLE")

        # Summary text
        pause_note = "ИИ активен (не на паузе)" if not is_paused else "ИИ на паузе игроком"
        if is_working:
            summary = (
                f"Фабрика функционирует нормально. Уровень {level}, цель: '{target_shape}'. "
                f"Прогресс: {delivered}/{required} доставлено. Текущий темп поставки: {throughput:.1f} шт/с. "
                f"Активно майнеров: {len(miners)}, оборудования: {len(processors)}, входов в Хаб: {len(hub_entrances)}. {pause_note}."
            )
        else:
            issues_str = "; ".join(issues) if issues else "Темп поставки 0.0 шт/с, фигуры не поступают в Хаб."
            summary = (
                f"Диагностика выявила сбой в работе фабрики. Уровень {level}, цель: '{target_shape}'. "
                f"Прогресс: {delivered}/{required}. Темп поставки: 0.0 шт/с. Проблемы: {issues_str}. {pause_note}."
            )

        return {
            "success": True,
            "level": level,
            "target_shape": target_shape,
            "delivered": delivered,
            "required": required,
            "throughput": throughput,
            "is_working": is_working,
            "is_paused": is_paused,
            "orchestrator_state": orch_state,
            "miners_count": len(miners),
            "miners": miners,
            "processors_count": len(processors),
            "processors": processors,
            "belt_count": belt_count,
            "hub_entrances": hub_entrances,
            "watchdog": watchdog_report,
            "issues": issues,
            "summary": summary
        }

    async def repair_factory(self, session_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Attempts autonomous repair of the active factory line.
        CRITICAL: Honors Pause AI. World mutations are strictly forbidden while paused!
        """
        is_paused = self.session_mgr.is_paused(session_id)
        if is_paused:
            logger.info("[ToolExecutor] Repair blocked by Pause AI.")
            return {
                "success": False,
                "paused": True,
                "error": "ИИ на паузе. Модификация игрового мира заблокирована. Возобновите ИИ для проведения ремонта.",
                "reason": reason
            }

        if not self.server.active_ws or self.server.active_ws.closed:
            return {"success": False, "error": "Game bridge is not connected"}

        repair_res = await self.watchdog.repair_active_line(self.server)
        return {
            "success": repair_res.get("success", False),
            "paused": False,
            "detail": repair_res,
            "reason": reason
        }

    async def replan_factory(self, session_id: str, preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Re-plans and rebuilds the factory from scratch for the current level.
        CRITICAL: Honors Pause AI.
        """
        is_paused = self.session_mgr.is_paused(session_id)
        if is_paused:
            logger.info("[ToolExecutor] Replan blocked by Pause AI.")
            return {
                "success": False,
                "paused": True,
                "error": "ИИ на паузе. Перепланирование со строительством заблокировано. Возобновите ИИ для перестройки фабрики."
            }

        if preferences:
            self.session_mgr.update_preferences(session_id, preferences)

        asyncio.create_task(self.orchestrator.plan_and_build_factory(session_id=session_id))
        return {
            "success": True,
            "paused": False,
            "action": "replan_initiated",
            "message": "Запущено полное перепланирование фабрики с учетом новых параметров."
        }

    async def inspect_tile(self, x: int, y: int) -> Dict[str, Any]:
        """Inspects tile entity and resource at coordinates (x, y)."""
        if not self.server.active_ws or self.server.active_ws.closed:
            return {"success": False, "error": "Game bridge is not connected"}

        res = await self.server.call("inspect_tile", {"x": x, "y": y})
        return res or {"success": False, "error": "No response"}

    async def get_game_status(self, session_id: str) -> Dict[str, Any]:
        """Returns high-level game operational state."""
        session = self.session_mgr.get_or_create(session_id)
        return {
            "session_id": session_id,
            "level": session.level,
            "goal": session.goal,
            "throughput": session.throughput,
            "fps": session.fps,
            "is_paused": session.is_paused,
            "preferences": session.preferences,
            "active_line": self.watchdog.get_active_line().line_id if self.watchdog.get_active_line() else None
        }
