"""
Session and Controller State Persistence for Shapez AI (N-0.3.0).
Supports pause/resume, user preferences, interactive chat history, and persistent SQLite index.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from supervisor.history_db import HistoryDB

logger = logging.getLogger("ShapezAI.Session")

SESSIONS_DIR = Path(__file__).parent.parent / "data" / "sessions"

class ActionRecord(BaseModel):
    action_type: str
    command: str
    params: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: float = Field(default_factory=time.time)

class ReasoningEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = Field(default_factory=time.time)
    level: int = 1
    goal_shape: str = ""
    model: str = "local"
    # True internal reasoning (Chain-of-Thought / <think>)
    reasoning_content: str = ""
    # Model's high-level synthetic explanation
    thought: str = ""
    plan_action: str = ""
    chosen_patch: Dict[str, Any] = Field(default_factory=dict)
    dispatched_actions: List[ActionRecord] = Field(default_factory=list)
    llm_latency_ms: float = 0.0
    execution_latency_ms: float = 0.0
    status: str = "success"  # "success", "failed", "rolled_back"
    error_detail: str = ""

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str  # "player" or "ai"
    text: str
    timestamp: float = Field(default_factory=time.time)
    intent: Optional[str] = None
    applied_preferences: Dict[str, Any] = Field(default_factory=dict)

class SessionState(BaseModel):
    session_id: str
    created_at: float = Field(default_factory=time.time)
    last_updated: float = Field(default_factory=time.time)
    game_ws_port: int = 8765
    level: int = 1
    goal: Dict[str, Any] = Field(default_factory=dict)
    fps: float = 60.0
    throughput: float = 0.0
    world_revision: int = 1
    is_paused: bool = True  # Defaults to paused on startup to give player direct control
    preferences: Dict[str, Any] = Field(default_factory=lambda: {
        "compact": True,
        "aesthetic": True,
        "symmetric": True,
        "reuse_lines": True
    })
    chat_history: List[ChatMessage] = Field(default_factory=list)
    long_term_goals: List[str] = Field(default_factory=lambda: [
        "Построить базовую добычу и доставку (Lvl 1-3)",
        "Организовать централизованную резку и сортировку (Lvl 4-7)",
        "Развернуть модульную окраску и смешивание красок (Lvl 8-11)",
        "Построить многослойный сборочный комплекс (Lvl 12+)",
        "Автоматизировать поставку форм для апгрейдов скорости конвейеров"
    ])
    short_term_plan: List[str] = Field(default_factory=list)
    upgrades_status: Dict[str, Any] = Field(default_factory=dict)
    active_lines: Dict[str, Any] = Field(default_factory=dict)
    history: List[ReasoningEntry] = Field(default_factory=list)

class SessionManager:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or SESSIONS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, SessionState] = {}
        self.history_db = HistoryDB()

    def get_or_create(self, session_id: Optional[str] = None, port: int = 8765) -> SessionState:
        sid = session_id or "session_primary"
        if sid in self.sessions:
            return self.sessions[sid]

        file_path = self.storage_dir / f"{sid}.json"
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                state = SessionState(**data)
                self.sessions[sid] = state
                logger.info(f"Loaded existing session '{sid}' from disk (is_paused={state.is_paused}).")
                return state
            except Exception as e:
                logger.warning(f"Could not load session '{sid}': {e}. Creating fresh.")

        state = SessionState(session_id=sid, game_ws_port=port, is_paused=True)
        self.sessions[sid] = state
        self.save(sid)
        logger.info(f"Created new session '{sid}' (defaults to paused).")
        return state

    def set_paused(self, session_id: str, paused: bool) -> bool:
        session = self.get_or_create(session_id)
        session.is_paused = paused
        session.last_updated = time.time()
        self.save(session_id)
        logger.info(f"Session '{session_id}' paused status set to: {paused}")
        return session.is_paused

    def is_paused(self, session_id: str) -> bool:
        session = self.get_or_create(session_id)
        return session.is_paused

    def update_preferences(self, session_id: str, new_prefs: Dict[str, Any]):
        session = self.get_or_create(session_id)
        session.preferences.update(new_prefs)
        session.last_updated = time.time()
        self.save(session_id)
        logger.info(f"Updated preferences for '{session_id}': {session.preferences}")

    def add_chat_message(self, session_id: str, msg: ChatMessage):
        session = self.get_or_create(session_id)
        session.chat_history.append(msg)
        # Keep last 50 chat messages in state
        if len(session.chat_history) > 50:
            session.chat_history = session.chat_history[-50:]
        session.last_updated = time.time()
        self.save(session_id)

    def record_reasoning(self, session_id: str, entry: ReasoningEntry):
        session = self.get_or_create(session_id)
        session.history.append(entry)
        if len(session.history) > 100:
            session.history = session.history[-100:]
        session.last_updated = time.time()
        self.save(session_id)

        # Store in permanent SQLite history database
        try:
            self.history_db.insert_entry(session_id, entry.model_dump())
        except Exception as e:
            logger.error(f"Failed to record entry to SQLite history DB: {e}")

    def update_metrics(
        self,
        session_id: str,
        fps: float,
        throughput: float,
        revision: int,
        level: Optional[int] = None,
        goal: Optional[Dict[str, Any]] = None
    ):
        session = self.get_or_create(session_id)
        session.fps = fps
        session.throughput = throughput
        session.world_revision = revision
        if level is not None:
            session.level = level
        if goal is not None:
            session.goal = goal
        session.last_updated = time.time()

    def update_short_term_plan(self, session_id: str, plan_steps: List[str]):
        session = self.get_or_create(session_id)
        session.short_term_plan = plan_steps
        session.last_updated = time.time()
        self.save(session_id)

    def update_upgrades_status(self, session_id: str, upgrades: Dict[str, Any]):
        session = self.get_or_create(session_id)
        session.upgrades_status = upgrades
        session.last_updated = time.time()
        self.save(session_id)

    def register_active_line(self, session_id: str, line_id: str, specs: List[Any]):
        session = self.get_or_create(session_id)
        session.active_lines[line_id] = {
            "registered_at": time.time(),
            "specs": [s.model_dump() if hasattr(s, "model_dump") else s for s in specs]
        }
        session.last_updated = time.time()
        self.save(session_id)

    def unregister_active_line(self, session_id: str, line_id: str):
        session = self.get_or_create(session_id)
        if line_id in session.active_lines:
            del session.active_lines[line_id]
            session.last_updated = time.time()
            self.save(session_id)

    def get_active_lines(self, session_id: str) -> Dict[str, Any]:
        session = self.get_or_create(session_id)
        return dict(session.active_lines)


    def save(self, session_id: str):
        if session_id not in self.sessions:
            return
        state = self.sessions[session_id]
        file_path = self.storage_dir / f"{session_id}.json"
        try:
            file_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save session '{session_id}': {e}")

    def list_all_sessions(self) -> List[Dict[str, Any]]:
        known_ids = set(self.sessions.keys())
        for p in self.storage_dir.glob("*.json"):
            known_ids.add(p.stem)

        results = []
        for sid in sorted(known_ids):
            state = self.get_or_create(sid)
            results.append({
                "session_id": sid,
                "created_at": state.created_at,
                "last_updated": state.last_updated,
                "game_ws_port": state.game_ws_port,
                "level": state.level,
                "goal": state.goal,
                "fps": state.fps,
                "throughput": state.throughput,
                "is_paused": state.is_paused,
                "preferences": state.preferences,
                "history_count": len(state.history),
                "chat_count": len(state.chat_history)
            })
        return results
