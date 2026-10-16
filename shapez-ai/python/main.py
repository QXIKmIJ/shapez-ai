"""
Shapez AI Master Orchestrator (N-0.3.0).
Coordinates Game Bridge, Local LLM Inference, Conveyor Router, Closed-Loop Production Watchdog,
Pause/Resume Engine, Persistent History, Two-Way Agentic Chat with Real Tool Calling, and Mod Registry.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, Any, Optional, List

from bridge.ws_server import ShapezBridgeServer
from bridge.protocol import GameState
from llm.client import LLMClient
from llm.prompts import (
    SYSTEM_PROMPT,
    make_planning_prompt,
    make_chat_prompt,
    make_chat_tool_feedback_prompt
)
from planner.router import ConveyorRouter
from planner.shape_analyzer import ParsedShape, analyze_target_goal, ProductionRequirement
from aiohttp import web
from supervisor.watchdog import FactoryWatchdog
from supervisor.session_manager import SessionManager, ReasoningEntry, ActionRecord, ChatMessage
from supervisor.tools import AgentToolExecutor
from supervisor.monitor_html import MONITOR_HTML
from mods.mod_registry import ModRegistry
from move_window import move_shapez

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ShapezAI.Main")

class ShapezAiOrchestrator:
    def __init__(
        self,
        ws_port: int = 8765,
        llm_url: str = "http://127.0.0.1:18088/v1",
        session_id: str = "session_primary"
    ):
        self.session_id = session_id
        self.session_mgr = SessionManager()
        self.session_state = self.session_mgr.get_or_create(self.session_id, port=ws_port)
        self.mod_registry = ModRegistry()

        self.server = ShapezBridgeServer(host="127.0.0.1", port=ws_port)
        self.llm = LLMClient(base_url=llm_url)
        self.router = ConveyorRouter()
        self.watchdog = FactoryWatchdog(self.router)
        self.tool_executor = AgentToolExecutor(self)

        self.current_state: Optional[Dict[str, Any]] = None
        self.planning_lock = asyncio.Lock()
        self.transition_lock = asyncio.Lock()
        self.is_running = True

        # Explicit State Machine
        # States: "PAUSED", "IDLE", "PLANNING", "CONSTRUCTING", "VERIFYING_PRODUCTION",
        #         "MONITORING_PROGRESS", "DIAGNOSING", "REPAIRING", "LEVEL_TRANSITION"
        self.state = "PAUSED" if self.session_mgr.is_paused(self.session_id) else "IDLE"
        self.active_level = self.session_state.level
        self.active_goal_shape = self.session_state.goal.get("shape", "")

        # Register Game Bridge push event handlers
        self.server.on_event("bridge:connected", self._on_bridge_connected)
        self.server.on_event("game:ready", self._on_game_ready)
        self.server.on_event("event:pause_toggle", self._on_pause_toggle)
        self.server.on_event("event:entity_destroyed", self._on_entity_destroyed)
        self.server.on_event("event:goal_completed", self._on_goal_completed)
        self.server.on_event("event:throughput_heartbeat", self._on_heartbeat)
        self.server.on_event("event:upgrade_purchased", self._on_upgrade_purchased)

        # Register HTTP routes for monitor dashboard and multi-session management
        self.server.app.router.add_get("/api/sessions", self._handle_get_sessions)
        self.server.app.router.add_get("/api/session", self._handle_get_session)
        self.server.app.router.add_post("/api/pause", self._handle_post_pause)
        self.server.app.router.add_post("/api/chat", self._handle_post_chat)
        self.server.app.router.add_get("/api/history", self._handle_get_history)
        self.server.app.router.add_get("/api/mods", self._handle_get_mods)
        self.server.app.router.add_get("/api/upgrades", self._handle_get_upgrades)
        self.server.app.router.add_post("/api/upgrade/unlock", self._handle_post_unlock_upgrade)
        self.server.app.router.add_post("/api/plan", self._handle_post_plan)
        self.server.app.router.add_post("/api/move_window", self._handle_move_window)
        self.server.app.router.add_get("/monitor", self._handle_get_monitor)
        self.server.app.router.add_get("/api/current_state", self._handle_get_current_state)

    async def _handle_get_current_state(self, request):
        if not self.current_state:
            return web.json_response({"ready": False})
        return web.json_response(self.current_state)

    async def _handle_get_sessions(self, request):
        return web.json_response({"sessions": self.session_mgr.list_all_sessions()})

    async def _handle_get_session(self, request):
        sid = request.query.get("session_id", self.session_id)
        session = self.session_mgr.get_or_create(sid)
        session_dict = session.model_dump()
        session_dict["state_machine_stage"] = self.state
        return web.json_response(session_dict)

    async def _handle_post_pause(self, request):
        try:
            body = await request.json()
            sid = body.get("session_id", self.session_id)
            paused = bool(body.get("paused", True))
            self.session_mgr.set_paused(sid, paused)
            self.state = "PAUSED" if paused else "IDLE"

            try:
                if self.server.active_ws and not self.server.active_ws.closed:
                    await self.server.call("set_ai_paused", {"paused": paused})
            except Exception as e:
                logger.debug(f"Could not forward pause state to game bridge: {e}")

            if not paused:
                asyncio.create_task(self.plan_and_build_factory(session_id=sid))
            return web.json_response({"success": True, "paused": paused, "session_id": sid})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)

    async def _handle_post_chat(self, request):
        """
        Two-Way Agentic Chat with REAL tool calling.
        If user asks to diagnose, fix, inspect, or rebuild:
        1. Calls appropriate tool via AgentToolExecutor
        2. Records actual executed action in ActionRecord and ReasoningEntry (visible in Monitor)
        3. Returns fact-grounded response to player
        """
        try:
            body = await request.json()
            user_msg = body.get("message", "").strip()
            sid = body.get("session_id", self.session_id)
            if not user_msg:
                return web.json_response({"error": "Empty message"}, status=400)

            # Record player message in session
            player_chat = ChatMessage(sender="player", text=user_msg)
            self.session_mgr.add_chat_message(sid, player_chat)

            session = self.session_mgr.get_or_create(sid)
            mods_summary = self.mod_registry.get_prompt_summary()

            chat_prompt = make_chat_prompt(
                user_message=user_msg,
                current_state=self.current_state,
                current_preferences=session.preferences,
                mods_summary=mods_summary,
                recent_history=[m.model_dump() for m in session.chat_history],
                is_paused=session.is_paused,
                orchestrator_state=self.state
            )

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": chat_prompt}
            ]

            try:
                llm_res = await self.llm.chat_json(messages, temperature=0.1)
                tool_calls = llm_res.get("tool_calls", [])
                new_prefs = llm_res.get("update_preferences", {})
                if new_prefs:
                    self.session_mgr.update_preferences(sid, new_prefs)

                executed_actions = []

                if tool_calls:
                    tool_results = []
                    action_records = []

                    for tc in tool_calls:
                        t_name = tc.get("name")
                        t_args = tc.get("args", {})
                        t_res = await self.tool_executor.execute_tool(t_name, t_args, session_id=sid)
                        tool_results.append({"tool": t_name, "args": t_args, "result": t_res})
                        action_records.append(
                            ActionRecord(
                                action_type="chat_tool_call",
                                command=t_name,
                                params=t_args,
                                result=t_res,
                                duration_ms=t_res.get("duration_ms", 0.0)
                            )
                        )
                    executed_actions = tool_results

                    # Record reasoning entry for monitor and SQLite persistence
                    reasoning_entry = ReasoningEntry(
                        level=session.level,
                        goal_shape=session.goal.get("shape", ""),
                        model=self.llm.model,
                        thought=f"Указание игрока: «{user_msg}». Вызов реальных инструментов: {', '.join(tc.get('name') for tc in tool_calls)}",
                        plan_action="chat_tool_execution",
                        dispatched_actions=action_records,
                        status="success"
                    )
                    self.session_mgr.record_reasoning(sid, reasoning_entry)

                    # Feed tool execution output back to LLM for factual verbal response
                    feedback_prompt = make_chat_tool_feedback_prompt(
                        user_message=user_msg,
                        tool_results=tool_results,
                        current_preferences=session.preferences,
                        is_paused=session.is_paused,
                        orchestrator_state=self.state
                    )
                    feedback_msgs = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": feedback_prompt}
                    ]
                    final_llm_res = await self.llm.chat_json(feedback_msgs, temperature=0.1)
                    reply_text = final_llm_res.get("reply", "Действие выполнено на основе полученных диагностических данных.")

                else:
                    reply_text = llm_res.get("reply", "Ваше указание принято.")

                ai_chat = ChatMessage(sender="ai", text=reply_text, applied_preferences=new_prefs)
                self.session_mgr.add_chat_message(sid, ai_chat)

                return web.json_response({
                    "success": True,
                    "reply": reply_text,
                    "preferences": session.preferences,
                    "actions_executed": executed_actions
                })

            except Exception as e:
                logger.error(f"Chat processing error: {e}", exc_info=True)
                fallback = f"Принято: «{user_msg}». Ошибка вызова: {e}"
                ai_chat = ChatMessage(sender="ai", text=fallback)
                self.session_mgr.add_chat_message(sid, ai_chat)
                return web.json_response({"success": True, "reply": fallback, "preferences": session.preferences})

        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)

    async def _handle_get_history(self, request):
        sid = request.query.get("session_id", self.session_id)
        query = request.query.get("query", "")
        level_str = request.query.get("level", "0")
        level = int(level_str) if level_str.isdigit() else 0
        status = request.query.get("status", "all")
        limit = int(request.query.get("limit", 50))
        offset = int(request.query.get("offset", 0))

        entries = self.session_mgr.history_db.search_history(
            session_id=sid,
            query=query,
            level=level if level > 0 else None,
            status=status if status != "all" else None,
            limit=limit,
            offset=offset
        )
        stats = self.session_mgr.history_db.get_stats(session_id=sid)
        return web.json_response({"entries": entries, "stats": stats})

    async def _handle_get_mods(self, request):
        return web.json_response({"mods": self.mod_registry.to_dict_list()})

    async def _handle_get_upgrades(self, request):
        try:
            if not self.server.active_ws or self.server.active_ws.closed:
                return web.json_response({"success": False, "reason": "Game bridge not connected"})
            res = await self.server.call("get_upgrades")
            return web.json_response(res or {"success": False})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)})

    async def _handle_post_unlock_upgrade(self, request):
        try:
            if not self.server.active_ws or self.server.active_ws.closed:
                return web.json_response({"success": False, "reason": "Game bridge not connected"})
            body = await request.json()
            key = body.get("upgradeKey")
            res = await self.server.call("try_unlock_upgrade", {"upgradeKey": key})
            return web.json_response(res or {"success": False})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)

    async def _handle_post_plan(self, request):
        sid = request.query.get("session_id", self.session_id)
        asyncio.create_task(self.plan_and_build_factory(session_id=sid))
        return web.json_response({"status": "planning_triggered", "session_id": sid})

    async def _handle_move_window(self, request):
        try:
            body = await request.json()
            mon = int(body.get("monitor", 1))
            res = move_shapez(mon)
            return web.json_response({"success": res, "monitor": mon})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)

    async def _handle_get_monitor(self, request):
        return web.Response(text=MONITOR_HTML, content_type="text/html")

    async def _on_bridge_connected(self, data: Dict[str, Any]):
        logger.info(f"Game Bridge connected (v{data.get('version')}).")
        is_paused = self.session_mgr.is_paused(self.session_id)
        try:
            await self.server.call("set_ai_paused", {"paused": is_paused})
        except Exception as e:
            logger.debug(f"Could not forward pause state on bridge connect: {e}")

    async def _on_game_ready(self, data: Dict[str, Any]):
        logger.info("Game world is initialized and ready.")
        self.current_state = data
        self.active_level = data.get("level", 1)
        self.active_goal_shape = data.get("goal", {}).get("shape", "")

        is_paused = self.session_mgr.is_paused(self.session_id)
        if not is_paused:
            logger.info("AI is active. Initiating autonomous planning...")
            self.state = "PLANNING"
            asyncio.create_task(self.plan_and_build_factory())
        else:
            self.state = "PAUSED"
            logger.info("AI is in PAUSED state (default safe mode). Awaiting user resume command.")
            await self.server.call("set_hud_status", {
                "status": "PAUSED",
                "thought": "ИИ в режиме ожидания. Нажмите [▶ Возобновить], чтобы начать."
            })

    async def _on_pause_toggle(self, data: Dict[str, Any]):
        paused = data.get("paused", True)
        logger.info(f"Received in-game HUD pause toggle: paused={paused}")
        self.session_mgr.set_paused(self.session_id, paused)
        self.state = "PAUSED" if paused else "IDLE"
        if not paused:
            asyncio.create_task(self.plan_and_build_factory(session_id=self.session_id))

    async def _on_entity_destroyed(self, data: Dict[str, Any]):
        if self.session_mgr.is_paused(self.session_id):
            logger.info("Entity destroyed while AI is paused. Watchdog recorded destruction without auto-rebuild.")
            return
        await self.watchdog.handle_destruction_event(data, self.server)

    async def _on_upgrade_purchased(self, data: Dict[str, Any]):
        logger.info(f"Upgrade purchased event: {data}")
        upgrades = await self.server.call("get_upgrades")
        if upgrades and upgrades.get("success"):
            self.session_mgr.update_upgrades_status(self.session_id, upgrades)

    async def _on_goal_completed(self, data: Dict[str, Any]):
        """Signal received from game engine when level completes."""
        await self._handle_level_transition(data.get("state") or self.current_state or {})

    async def _on_heartbeat(self, data: Dict[str, Any]):
        rate = data.get("throughput", 0.0)
        delivered = data.get("delivered", 0)
        required = data.get("required", 0)
        fps = data.get("fps", 60.0)
        level = data.get("level", self.active_level)
        goal_shape = data.get("goalShape", self.active_goal_shape)

        self.session_mgr.update_metrics(
            self.session_id,
            fps=fps,
            throughput=rate,
            revision=self.current_state.get("revision", 1) if self.current_state else 1,
            level=level,
            goal={"shape": goal_shape, "delivered": delivered, "required": required}
        )

        # Check for level completion directly inside heartbeat
        if required > 0 and delivered >= required:
            asyncio.create_task(self._handle_level_transition({
                "level": level + 1,
                "goal": {"shape": goal_shape, "delivered": delivered, "required": required}
            }))

    async def _supervisory_loop(self):
        """
        Continuous Supervisory & State Reconciliation Loop (Every 1.5s):
        1. Guarantees Zero-Drop Level Transitions even if signals were skipped or dropped.
        2. Closed-Loop Production Watchdog monitoring (detects stalls, zero progress, missing belts).
        3. Maintains accurate in-game HUD status.
        """
        logger.info("[Supervisory] Started autonomous reconciliation loop.")
        while self.is_running:
            try:
                await asyncio.sleep(1.5)
                if not self.server.active_ws or self.server.active_ws.closed:
                    continue

                state_data = await self.server.call("get_game_state")
                if not state_data or not state_data.get("ready"):
                    continue

                self.current_state = state_data
                game_lvl = state_data.get("level", 1)
                goal = state_data.get("goal", {})
                delivered = goal.get("delivered", 0)
                required = goal.get("required", 0)
                throughput = state_data.get("throughput", 0.0)

                # 1. Zero-Drop Level Reconciliation
                if game_lvl > self.active_level or (required > 0 and delivered >= required):
                    await self._handle_level_transition(state_data)
                    continue

                # 2. Closed-Loop Watchdog Verification
                if self.state in ["VERIFYING_PRODUCTION", "MONITORING_PROGRESS"]:
                    health = self.watchdog.check_health(
                        current_throughput=throughput,
                        current_delivered=delivered,
                        game_state=state_data
                    )
                    if health.get("status") == "operational":
                        self.state = "MONITORING_PROGRESS"
                    elif health.get("stalled"):
                        logger.warning(f"[Watchdog] Production stall detected: {health.get('message')}")
                        self.state = "DIAGNOSING"
                        if not self.session_mgr.is_paused(self.session_id):
                            logger.info("[Watchdog] Initiating self-healing repair...")
                            self.state = "REPAIRING"
                            repair_res = await self.watchdog.repair_active_line(self.server)
                            if repair_res.get("success"):
                                logger.info("[Watchdog] Repair successful. Returning to production verification.")
                                self.state = "VERIFYING_PRODUCTION"
                            else:
                                logger.error(f"[Watchdog] Repair failed: {repair_res}")
                                if health.get("is_blocked"):
                                    logger.warning("[Watchdog] Escalation: 3 attempts failed. Initiating full replan...")
                                    self.state = "PLANNING"
                                    asyncio.create_task(self.plan_and_build_factory())
                        else:
                            await self.server.call("set_hud_status", {
                                "status": "PAUSED (Stall)",
                                "thought": "Обнаружен простой фабрики. Для авторемонта нажмите [▶ Возобновить ИИ]."
                            })

            except Exception as e:
                logger.debug(f"[Supervisory] Loop iteration error: {e}")

    async def _handle_level_transition(self, state_data: Dict[str, Any]):
        """
        Deduplicated, deterministic level advancement handler:
        Works whether triggered by bridge signal, player manual fix, or background factory completion.
        """
        async with self.transition_lock:
            game_lvl = state_data.get("level", self.active_level)
            goal = state_data.get("goal", {})
            delivered = goal.get("delivered", 0)
            required = goal.get("required", 0)

            # Determine target next level
            if game_lvl > self.active_level:
                target_lvl = game_lvl
            elif required > 0 and delivered >= required:
                target_lvl = self.active_level + 1
            else:
                return

            if target_lvl <= self.active_level and self.state == "LEVEL_TRANSITION":
                return

            prev_lvl = self.active_level
            self.active_level = target_lvl
            self.state = "LEVEL_TRANSITION"

            logger.info(f"*** LEVEL ADVANCED: Level {prev_lvl} -> Level {target_lvl} ***")

            # Record reasoning entry for history
            actions_list = [
                ActionRecord(
                    action_type="level_transition",
                    command="advance_level",
                    params={"previous_level": prev_lvl, "new_level": target_lvl},
                    result={"success": True}
                )
            ]
            reasoning_entry = ReasoningEntry(
                level=prev_lvl,
                goal_shape=goal.get("shape", ""),
                model=self.llm.model,
                thought=f"Уровень {prev_lvl} успешно завершен! Автономный переход к Уровню {target_lvl}.",
                plan_action=f"advance_to_level_{target_lvl}",
                dispatched_actions=actions_list,
                status="success"
            )
            self.session_mgr.record_reasoning(self.session_id, reasoning_entry)

            await self.server.call("set_hud_status", {
                "status": f"Level {prev_lvl} Complete!",
                "thought": f"Уровень {prev_lvl} завершен! Запуск автономного цикла для Уровня {target_lvl}..."
            })

            await asyncio.sleep(2.0)

            fresh_state = await self.server.call("get_game_state")
            self.current_state = fresh_state

            if not self.session_mgr.is_paused(self.session_id):
                self.state = "PLANNING"
                asyncio.create_task(self.plan_and_build_factory())
            else:
                self.state = "PAUSED"
                logger.info(f"Level {target_lvl} ready, but AI is paused. Awaiting user resume.")
                await self.server.call("set_hud_status", {
                    "status": "PAUSED",
                    "thought": f"Уровень {target_lvl} доступен. Нажмите [▶ Возобновить ИИ] для продолжения."
                })

    async def plan_and_build_factory(self, session_id: Optional[str] = None):
        """Strategic AI Planning & Execution Cycle."""
        sid = session_id or self.session_id

        # Cancel-in-flight check: ensure AI is not paused
        if self.session_mgr.is_paused(sid):
            logger.info(f"AI for session '{sid}' is paused. Skipping autonomous planning cycle.")
            self.state = "PAUSED"
            return

        if not self.server.active_ws or self.server.active_ws.closed:
            logger.info("Game bridge is not connected. Awaiting game connection before planning.")
            return

        async with self.planning_lock:
            try:
                self.state = "PLANNING"
                # 1. Fetch fresh game state
                state_data = await self.server.call("get_game_state")
                if not state_data or not state_data.get("ready"):
                    logger.warning("Game state not ready yet.")
                    return

                self.current_state = state_data
                level = state_data.get("level", 1)
                goal = state_data.get("goal", {})
                target_shape = goal.get("shape", "CuCuCuCu")
                patches = state_data.get("patches", [])
                fps = state_data.get("fps", 60.0)

                self.active_level = level
                self.active_goal_shape = target_shape

                self.session_mgr.update_metrics(
                    sid,
                    fps=fps,
                    throughput=0.0,
                    revision=state_data.get("revision", 1),
                    level=level,
                    goal=goal
                )

                logger.info(f"Starting planning for Level {level} (Target Shape: '{target_shape}', FPS: {fps})")
                await self.server.call("set_hud_status", {
                    "status": "Analyzing Goal",
                    "thought": f"Анализ цели уровня {level}: {target_shape}. Консультация с Qwen3.5..."
                })

                # 2. Consult LLM for strategic decision
                session_obj = self.session_mgr.get_or_create(sid)
                user_prompt = make_planning_prompt(
                    state_data,
                    preferences=session_obj.preferences,
                    mods_summary=self.mod_registry.get_prompt_summary()
                )
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]

                reasoning_text = ""
                llm_latency = 0.0
                try:
                    llm_plan = await self.llm.chat_json(messages, temperature=0.1)
                    thought = llm_plan.get("thought", "Планирование компактной линии добычи и доставки")
                    meta = llm_plan.get("_meta", {})
                    reasoning_text = meta.get("reasoning_content", "")
                    llm_latency = meta.get("duration_ms", 0.0)
                    logger.info(f"LLM Decision ({llm_latency:.0f}ms): {thought}")
                    if reasoning_text:
                        logger.info(f"LLM Native CoT: {reasoning_text[:120]}...")
                    await self.server.call("set_hud_status", {
                        "status": "Strategy Formulated",
                        "thought": f"ИИ: {thought}"
                    })
                except Exception as e:
                    logger.warning(f"LLM request error ({e}), proceeding with tactical fallback.")
                    thought = f"Автономное тактическое построение для {target_shape}"

                # Cancel-in-flight check: if user paused during LLM generation, discard
                if self.session_mgr.is_paused(sid):
                    logger.info(f"Session '{sid}' was paused during LLM thinking. Halting execution.")
                    self.state = "PAUSED"
                    return

                # 3. Analyze goal requirement (raw vs processed)
                req = analyze_target_goal(target_shape)
                logger.info(f"Goal analysis for '{target_shape}': op={req.op_type}, raw={req.raw_shape}, keep_half={req.keep_half}")

                # Clean up registered active lines from previous levels if obsolete
                active_lines = self.session_mgr.get_active_lines(sid)
                obsolete_line_keys = [
                    k for k in active_lines.keys()
                    if not k.endswith(f"_{target_shape}")
                ]
                if obsolete_line_keys:
                    logger.info(f"Removing {len(obsolete_line_keys)} obsolete production lines from prior levels: {obsolete_line_keys}")
                    obsolete_coords = []
                    for k in obsolete_line_keys:
                        specs = active_lines[k].get("specs", [])
                        for s in specs:
                            obsolete_coords.append({"x": s.get("x"), "y": s.get("y")})
                        self.session_mgr.unregister_active_line(sid, k)
                    if obsolete_coords:
                        try:
                            await self.server.call("delete_batch", {"coords": obsolete_coords})
                            fresh_state = await self.server.call("get_game_state")
                            if fresh_state and fresh_state.get("ready"):
                                state_data = fresh_state
                                self.current_state = fresh_state
                        except Exception as e:
                            logger.warning(f"Could not clear obsolete line batch: {e}")


                # Collect existing obstacle entities
                obstacles = set()
                for ent in state_data.get("entities", []):
                    obstacles.add((ent["x"], ent["y"]))

                if req.op_type == "cut_and_paint":
                    # 1. Locate shape patch (e.g. RuRuRuRu)
                    shape_patches = [
                        p for p in patches
                        if p.get("type") == "shape" and p.get("item") == req.raw_shape
                    ]
                    if not shape_patches:
                        shape_patches = [p for p in patches if p.get("type") == "shape"]
                    shape_patches.sort(key=lambda p: abs(p["tileX"]) + abs(p["tileY"]))
                    chosen_shape = shape_patches[0]
                    shape_pos = (int(round(chosen_shape["tileX"])), int(round(chosen_shape["tileY"])))
                    if shape_pos in obstacles:
                        for radius in range(1, 6):
                            found = False
                            for dy in range(-radius, radius + 1):
                                for dx in range(-radius, radius + 1):
                                    cand = (shape_pos[0] + dx, shape_pos[1] + dy)
                                    if cand not in obstacles:
                                        shape_pos = cand
                                        found = True
                                        break
                                if found:
                                    break
                            if found:
                                break

                    # 2. Locate color patch (e.g. blue)
                    color_patches = [
                        p for p in patches
                        if p.get("type") == "color" and p.get("item") == req.color
                    ]
                    if not color_patches:
                        color_patches = [p for p in patches if p.get("type") == "color"]
                    color_patches.sort(key=lambda p: abs(p["tileX"]) + abs(p["tileY"]))
                    chosen_color = color_patches[0]
                    color_pos = (int(round(chosen_color["tileX"])), int(round(chosen_color["tileY"])))
                    if color_pos in obstacles:
                        for radius in range(1, 6):
                            found = False
                            for dy in range(-radius, radius + 1):
                                for dx in range(-radius, radius + 1):
                                    cand = (color_pos[0] + dx, color_pos[1] + dy)
                                    if cand not in obstacles:
                                        color_pos = cand
                                        found = True
                                        break
                                if found:
                                    break
                            if found:
                                break

                    logger.info(f"Selected shape patch at {shape_pos} ('{chosen_shape.get('item')}'), color patch at {color_pos} ('{chosen_color.get('item')}')")
                    chosen_patch = chosen_shape
                    patch_pos = shape_pos

                    # 3. Find Hub slot and route cut & paint line
                    hub_slot, entry_dir = self.router.find_nearest_hub_slot(color_pos, obstacles=obstacles)
                    logger.info(f"Targeting Hub slot at {hub_slot} with entry direction {entry_dir}")
                    route_specs = self.router.plan_cut_and_paint_line(
                        shape_pos,
                        color_pos,
                        hub_slot,
                        entry_dir,
                        obstacles,
                        keep_half=req.keep_half if req.keep_half is not None else 1,
                        rotation=req.rotation
                    )
                    plan_action = f"cut_paint_and_deliver_{target_shape}"
                    short_plan = [
                        f"Добыча сырья {req.raw_shape} на {shape_pos}",
                        f"Модуль резки (keep half={req.keep_half}) с утилизацией отходов",
                        f"Добыча красителя {req.color} на {color_pos}",
                        f"Модуль окраски (Painter) и подача половины фигуры {target_shape} в слот Хаба {hub_slot}"
                    ]

                elif req.op_type == "mix_and_paint":
                    # 1. Locate shape patch (e.g. CuCuCuCu)
                    shape_patches = [
                        p for p in patches
                        if p.get("type") == "shape" and p.get("item") == req.raw_shape
                    ]
                    if not shape_patches:
                        shape_patches = [p for p in patches if p.get("type") == "shape"]
                    shape_patches.sort(key=lambda p: abs(p["tileX"]) + abs(p["tileY"]))
                    chosen_shape = shape_patches[0]
                    shape_pos = (int(round(chosen_shape["tileX"])), int(round(chosen_shape["tileY"])))
                    if shape_pos in obstacles:
                        for radius in range(1, 6):
                            found = False
                            for dy in range(-radius, radius + 1):
                                for dx in range(-radius, radius + 1):
                                    cand = (shape_pos[0] + dx, shape_pos[1] + dy)
                                    if cand not in obstacles:
                                        shape_pos = cand
                                        found = True
                                        break
                                if found:
                                    break
                            if found:
                                break

                    # 2. Locate color 1 patch (e.g. red)
                    c1_target = req.color_mix[0] if req.color_mix else "red"
                    c1_patches = [
                        p for p in patches
                        if p.get("type") == "color" and p.get("item") == c1_target
                    ]
                    if not c1_patches:
                        c1_patches = [p for p in patches if p.get("type") == "color"]
                    c1_patches.sort(key=lambda p: abs(p["tileX"]) + abs(p["tileY"]))
                    chosen_c1 = c1_patches[0]
                    color1_pos = (int(round(chosen_c1["tileX"])), int(round(chosen_c1["tileY"])))

                    # 3. Locate color 2 patch (e.g. blue)
                    c2_target = req.color_mix[1] if req.color_mix else "blue"
                    c2_patches = [
                        p for p in patches
                        if p.get("type") == "color" and p.get("item") == c2_target
                    ]
                    if not c2_patches:
                        c2_patches = [p for p in patches if p.get("type") == "color"]
                    c2_patches.sort(key=lambda p: abs(p["tileX"]) + abs(p["tileY"]))
                    chosen_c2 = c2_patches[0]
                    color2_pos = (int(round(chosen_c2["tileX"])), int(round(chosen_c2["tileY"])))

                    logger.info(
                        f"Selected shape patch at {shape_pos} ('{chosen_shape.get('item')}'), "
                        f"color1 patch at {color1_pos} ('{c1_target}'), "
                        f"color2 patch at {color2_pos} ('{c2_target}')"
                    )
                    chosen_patch = chosen_shape
                    patch_pos = shape_pos

                    # 4. Find Hub slot and route mix & paint line
                    hub_slot, entry_dir = self.router.find_nearest_hub_slot(color1_pos, obstacles=obstacles)
                    logger.info(f"Targeting Hub slot at {hub_slot} with entry direction {entry_dir}")
                    route_specs = self.router.plan_mix_and_paint_line(
                        shape_pos,
                        color1_pos,
                        color2_pos,
                        hub_slot,
                        entry_dir,
                        obstacles
                    )
                    plan_action = f"mix_paint_and_deliver_{target_shape}"
                    short_plan = [
                        f"Добыча фигур {req.raw_shape} на {shape_pos}",
                        f"Добыча красителя {c1_target} на {color1_pos} и {c2_target} на {color2_pos}",
                        f"Смешивание в Color Mixer для получения красителя {req.color}",
                        f"Окраска фигур в Painter и подача {target_shape} в слот Хаба {hub_slot}"
                    ]

                elif req.op_type == "paint":
                    # 1. Locate shape patch (e.g. CuCuCuCu)
                    shape_patches = [
                        p for p in patches
                        if p.get("type") == "shape" and p.get("item") == req.raw_shape
                    ]
                    if not shape_patches:
                        shape_patches = [p for p in patches if p.get("type") == "shape"]
                    shape_patches.sort(key=lambda p: abs(p["tileX"]) + abs(p["tileY"]))
                    chosen_shape = shape_patches[0]
                    shape_pos = (int(round(chosen_shape["tileX"])), int(round(chosen_shape["tileY"])))
                    if shape_pos in obstacles:
                        for radius in range(1, 6):
                            found = False
                            for dy in range(-radius, radius + 1):
                                for dx in range(-radius, radius + 1):
                                    cand = (shape_pos[0] + dx, shape_pos[1] + dy)
                                    if cand not in obstacles:
                                        shape_pos = cand
                                        found = True
                                        break
                                if found:
                                    break
                            if found:
                                break

                    # 2. Locate color patch (e.g. red)
                    color_patches = [
                        p for p in patches
                        if p.get("type") == "color" and p.get("item") == req.color
                    ]
                    if not color_patches:
                        color_patches = [p for p in patches if p.get("type") == "color"]
                    color_patches.sort(key=lambda p: abs(p["tileX"]) + abs(p["tileY"]))
                    chosen_color = color_patches[0]
                    color_pos = (int(round(chosen_color["tileX"])), int(round(chosen_color["tileY"])))
                    if color_pos in obstacles:
                        for radius in range(1, 6):
                            found = False
                            for dy in range(-radius, radius + 1):
                                for dx in range(-radius, radius + 1):
                                    cand = (color_pos[0] + dx, color_pos[1] + dy)
                                    if cand not in obstacles:
                                        color_pos = cand
                                        found = True
                                        break
                                if found:
                                    break
                            if found:
                                break

                    logger.info(f"Selected shape patch at {shape_pos} ('{chosen_shape.get('item')}'), color patch at {color_pos} ('{chosen_color.get('item')}')")
                    chosen_patch = chosen_shape
                    patch_pos = shape_pos

                    # 3. Find Hub slot and route painting line
                    hub_slot, entry_dir = self.router.find_nearest_hub_slot(color_pos, obstacles=obstacles)
                    logger.info(f"Targeting Hub slot at {hub_slot} with entry direction {entry_dir}")
                    route_specs = self.router.plan_painting_line(
                        shape_pos,
                        color_pos,
                        hub_slot,
                        entry_dir,
                        obstacles
                    )
                    plan_action = f"paint_and_deliver_{target_shape}"
                    short_plan = [
                        f"Добыча фигур {req.raw_shape} на {shape_pos}",
                        f"Добыча красителя {req.color} на {color_pos}",
                        f"Модуль окраски (Painter) и подача в слот Хаба {hub_slot}"
                    ]

                elif req.op_type == "cut":
                    matching_patches = [
                        p for p in patches
                        if p.get("type") == "shape" and p.get("item") == req.raw_shape
                    ]
                    if not matching_patches:
                        matching_patches = [p for p in patches if p.get("type") == "shape"]
                    matching_patches.sort(key=lambda p: abs(p["tileX"]) + abs(p["tileY"]))
                    chosen_patch = matching_patches[0]
                    patch_pos = (int(round(chosen_patch["tileX"])), int(round(chosen_patch["tileY"])))
                    if patch_pos in obstacles:
                        for radius in range(1, 6):
                            found = False
                            for dy in range(-radius, radius + 1):
                                for dx in range(-radius, radius + 1):
                                    cand = (patch_pos[0] + dx, patch_pos[1] + dy)
                                    if cand not in obstacles:
                                        patch_pos = cand
                                        found = True
                                        break
                                if found:
                                    break
                            if found:
                                break

                    hub_slot, entry_dir = self.router.find_nearest_hub_slot(patch_pos, obstacles=obstacles)
                    route_specs = self.router.plan_cutter_and_conveyor(
                        patch_pos,
                        hub_slot,
                        entry_dir,
                        obstacles,
                        keep_half=req.keep_half or 0,
                        rotation=req.rotation
                    )
                    plan_action = f"cutter_and_deliver_{target_shape}"
                    short_plan = [
                        f"Добыча сырья {req.raw_shape} на {patch_pos}",
                        f"Компактный модуль резки (keep half={req.keep_half}) с утилизацией отходов",
                        f"Доставка половины фигуры {target_shape} в слот Хаба {hub_slot}"
                    ]

                else:
                    matching_patches = [
                        p for p in patches
                        if p.get("type") == "shape" and p.get("item") == req.raw_shape
                    ]
                    if not matching_patches:
                        matching_patches = [p for p in patches if p.get("type") == "shape"]
                    matching_patches.sort(key=lambda p: abs(p["tileX"]) + abs(p["tileY"]))
                    chosen_patch = matching_patches[0]
                    patch_pos = (int(round(chosen_patch["tileX"])), int(round(chosen_patch["tileY"])))
                    if patch_pos in obstacles:
                        for radius in range(1, 6):
                            found = False
                            for dy in range(-radius, radius + 1):
                                for dx in range(-radius, radius + 1):
                                    cand = (patch_pos[0] + dx, patch_pos[1] + dy)
                                    if cand not in obstacles:
                                        patch_pos = cand
                                        found = True
                                        break
                                if found:
                                    break
                            if found:
                                break

                    hub_slot, entry_dir = self.router.find_nearest_hub_slot(patch_pos, obstacles=obstacles)
                    route_specs = self.router.plan_miner_and_conveyor(
                        patch_pos,
                        hub_slot,
                        entry_dir,
                        obstacles
                    )
                    plan_action = f"mine_and_deliver_{target_shape}"
                    short_plan = [
                        f"Установка майнера на залежи {patch_pos}",
                        f"Ортогональная магистраль конвейеров до слота Хаба {hub_slot}",
                        "Подача в Хаб и мониторинг темпа доставки"
                    ]

                # Fallback: if routing was blocked by obsolete factory entities, clear corridors and retry
                if not route_specs and len(obstacles) > 40:
                    logger.warning("Corridors crowded by legacy factory. Performing autonomous corridor clearance...")
                    stale_coords = [{"x": ent["x"], "y": ent["y"]} for ent in state_data.get("entities", []) if ent.get("building") != "hub"]
                    if stale_coords:
                        await self.server.call("delete_batch", {"coords": stale_coords})
                        obstacles = set()
                        if req.op_type == "mix_and_paint":
                            hub_slot, entry_dir = self.router.find_nearest_hub_slot(color1_pos, obstacles=obstacles)
                            route_specs = self.router.plan_mix_and_paint_line(shape_pos, color1_pos, color2_pos, hub_slot, entry_dir, obstacles)
                        elif req.op_type == "cut_and_paint":
                            hub_slot, entry_dir = self.router.find_nearest_hub_slot(color_pos, obstacles=obstacles)
                            route_specs = self.router.plan_cut_and_paint_line(shape_pos, color_pos, hub_slot, entry_dir, obstacles, keep_half=req.keep_half if req.keep_half is not None else 1, rotation=req.rotation)
                        elif req.op_type == "paint":
                            hub_slot, entry_dir = self.router.find_nearest_hub_slot(color_pos, obstacles=obstacles)
                            route_specs = self.router.plan_painting_line(shape_pos, color_pos, hub_slot, entry_dir, obstacles)
                        elif req.op_type == "cut":
                            hub_slot, entry_dir = self.router.find_nearest_hub_slot(patch_pos, obstacles=obstacles)
                            route_specs = self.router.plan_cutter_and_conveyor(patch_pos, hub_slot, entry_dir, obstacles, keep_half=req.keep_half if req.keep_half is not None else 0, rotation=req.rotation)
                        else:
                            hub_slot, entry_dir = self.router.find_nearest_hub_slot(patch_pos, obstacles=obstacles)
                            route_specs = self.router.plan_miner_and_conveyor(patch_pos, hub_slot, entry_dir, obstacles)

                self.session_mgr.update_short_term_plan(sid, short_plan)

                if not route_specs:
                    logger.error("A* pathfinder could not find an unblocked path to the Hub!")
                    await self.server.call("set_hud_status", {
                        "status": "Routing Failed",
                        "thought": "Не удалось найти свободный путь от залежи к Хабу."
                    })
                    return

                logger.info(f"Route planned successfully: {len(route_specs)} components ({plan_action}).")

                # Cancel-in-flight check before preflight
                if self.session_mgr.is_paused(sid):
                    logger.info(f"Session '{sid}' was paused. Cancelling batch preflight.")
                    self.state = "PAUSED"
                    return

                # 5. Preflight verification
                self.state = "CONSTRUCTING"
                await self.server.call("set_hud_status", {
                    "status": "Validating Plan",
                    "thought": f"Проверка возможности строительства {len(route_specs)} объектов..."
                })

                preflight_res = await self.server.call("preflight_check", {
                    "entities": [s.model_dump() for s in route_specs]
                })

                if not preflight_res or not preflight_res.get("valid"):
                    logger.error(f"Preflight check rejected plan: {preflight_res}")
                    await self.server.call("set_hud_status", {
                        "status": "Preflight Failed",
                        "thought": f"Ошибка валидации: {preflight_res.get('reason', 'Unknown')}"
                    })
                    return

                # Cancel-in-flight check before actual execution
                if self.session_mgr.is_paused(sid):
                    logger.info(f"Session '{sid}' was paused. Cancelling batch execution.")
                    self.state = "PAUSED"
                    return

                # 6. Execute atomic batch placement
                await self.server.call("set_hud_status", {
                    "status": "Constructing",
                    "thought": f"Строительство фабрики ({len(route_specs)} компонентов)..."
                })

                exec_res = await self.server.call("execute_batch", {
                    "entities": [s.model_dump() for s in route_specs]
                })

                exec_time_ms = exec_res.get("executionTimeMs", 0.0) if exec_res else 0.0

                # Record reasoning entry for monitor and persistence
                actions_list = [
                    ActionRecord(
                        action_type="preflight_check",
                        command="preflight_check",
                        params={"count": len(route_specs)},
                        result=preflight_res
                    ),
                    ActionRecord(
                        action_type="execute_batch",
                        command="execute_batch",
                        params={"placedCount": len(route_specs)},
                        result=exec_res,
                        duration_ms=exec_time_ms
                    )
                ]

                reasoning_entry = ReasoningEntry(
                    level=level,
                    goal_shape=target_shape,
                    model=self.llm.model,
                    reasoning_content=reasoning_text,
                    thought=thought,
                    plan_action=plan_action,
                    chosen_patch=chosen_patch,
                    dispatched_actions=actions_list,
                    llm_latency_ms=llm_latency,
                    execution_latency_ms=exec_time_ms,
                    status="success" if (exec_res and exec_res.get("success")) else "failed"
                )
                self.session_mgr.record_reasoning(sid, reasoning_entry)

                if exec_res and exec_res.get("success"):
                    line_id = f"line_lvl_{level}_{target_shape}"
                    self.watchdog.register_line(line_id, target_shape, patch_pos, route_specs, hub_slot=hub_slot)
                    self.session_mgr.register_active_line(sid, line_id, route_specs)
                    logger.info(f"Successfully constructed production line '{line_id}' ({exec_time_ms}ms)!")
                    self.state = "VERIFYING_PRODUCTION"
                    await self.server.call("set_hud_status", {
                        "status": "Operational",
                        "thought": f"Фабрика запущена ({exec_time_ms}мс)! Верификация поставки '{target_shape}'..."
                    })
                else:
                    logger.error(f"Batch execution failed: {exec_res}")
                    self.state = "IDLE"
                    await self.server.call("set_hud_status", {
                        "status": "Build Failed",
                        "thought": f"Сбой размещения: {exec_res.get('detail', 'Unknown error')}"
                    })

            except Exception as e:
                logger.error(f"Error during plan_and_build_factory: {e}", exc_info=True)
                self.state = "IDLE"

    async def start(self):
        """Start the orchestrator services."""
        logger.info("Initializing Shapez AI Orchestrator N-0.3.0...")
        await self.server.start()
        logger.info("Awaiting game launch and connection...")

        # Start continuous supervisory and reconciliation loop
        asyncio.create_task(self._supervisory_loop())

        try:
            while self.is_running:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass
        finally:
            await self.server.stop()

def main():
    orchestrator = ShapezAiOrchestrator()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown():
        orchestrator.is_running = False
        for task in asyncio.all_tasks(loop):
            task.cancel()

    try:
        loop.run_until_complete(orchestrator.start())
    except KeyboardInterrupt:
        logger.info("Shutting down Shapez AI Orchestrator...")
    finally:
        loop.close()

if __name__ == "__main__":
    main()
