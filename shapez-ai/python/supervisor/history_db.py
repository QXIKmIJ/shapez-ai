"""
Persistent SQLite Decision & Action History Database for Shapez AI.
Ensures zero data loss across restarts with full-text search, level and status filtering.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

logger = logging.getLogger("ShapezAI.HistoryDB")

DB_DIR = Path(__file__).parent.parent / "data"
DB_FILE = DB_DIR / "history.db"

class HistoryDB:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_FILE
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decision_history (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    level INTEGER NOT NULL,
                    goal_shape TEXT NOT NULL,
                    model TEXT NOT NULL,
                    reasoning_content TEXT,
                    thought TEXT NOT NULL,
                    plan_action TEXT NOT NULL,
                    chosen_patch TEXT,
                    dispatched_actions TEXT,
                    llm_latency_ms REAL,
                    execution_latency_ms REAL,
                    status TEXT NOT NULL,
                    error_detail TEXT
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_session_ts
                ON decision_history(session_id, timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_level
                ON decision_history(level)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_status
                ON decision_history(status)
            """)
            conn.commit()

    def insert_entry(self, session_id: str, entry_data: Dict[str, Any]):
        """Inserts a reasoning/decision entry into the persistent database."""
        entry_id = entry_data.get("id") or str(uuid.uuid4())[:8]
        timestamp = entry_data.get("timestamp", time.time())
        level = entry_data.get("level", 1)
        goal_shape = entry_data.get("goal_shape", "")
        model = entry_data.get("model", "local")
        reasoning_content = entry_data.get("reasoning_content", "")
        thought = entry_data.get("thought", "")
        plan_action = entry_data.get("plan_action", "")
        chosen_patch = json.dumps(entry_data.get("chosen_patch", {}), ensure_ascii=False)
        dispatched_actions = json.dumps(entry_data.get("dispatched_actions", []), ensure_ascii=False)
        llm_latency_ms = float(entry_data.get("llm_latency_ms", 0.0))
        execution_latency_ms = float(entry_data.get("execution_latency_ms", 0.0))
        status = entry_data.get("status", "success")
        error_detail = entry_data.get("error_detail", "")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO decision_history (
                    id, session_id, timestamp, level, goal_shape, model,
                    reasoning_content, thought, plan_action, chosen_patch,
                    dispatched_actions, llm_latency_ms, execution_latency_ms,
                    status, error_detail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id, session_id, timestamp, level, goal_shape, model,
                reasoning_content, thought, plan_action, chosen_patch,
                dispatched_actions, llm_latency_ms, execution_latency_ms,
                status, error_detail
            ))
            conn.commit()
            logger.debug(f"Saved decision {entry_id} to persistent history database.")

    def search_history(
        self,
        session_id: Optional[str] = None,
        query: str = "",
        level: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Searches decision history with filters and text search."""
        clauses = []
        params = []

        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)

        if level is not None and level > 0:
            clauses.append("level = ?")
            params.append(level)

        if status and status != "all":
            clauses.append("status = ?")
            params.append(status)

        if query and query.strip():
            clauses.append("(thought LIKE ? OR plan_action LIKE ? OR goal_shape LIKE ? OR reasoning_content LIKE ?)")
            pattern = f"%{query.strip()}%"
            params.extend([pattern, pattern, pattern, pattern])

        where_sql = " AND ".join(clauses) if clauses else "1=1"
        sql = f"""
            SELECT * FROM decision_history
            WHERE {where_sql}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        results = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                d = dict(row)
                try:
                    d["chosen_patch"] = json.loads(d["chosen_patch"]) if d["chosen_patch"] else {}
                except Exception:
                    pass
                try:
                    d["dispatched_actions"] = json.loads(d["dispatched_actions"]) if d["dispatched_actions"] else []
                except Exception:
                    pass
                results.append(d)
        return results

    def get_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates historical performance metrics."""
        sql = """
            SELECT 
                COUNT(*) as total_decisions,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as failed,
                AVG(llm_latency_ms) as avg_llm_latency,
                AVG(execution_latency_ms) as avg_exec_latency,
                MAX(level) as highest_level
            FROM decision_history
        """
        params = []
        if session_id:
            sql += " WHERE session_id = ?"
            params.append(session_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            if row:
                return {
                    "total_decisions": row["total_decisions"] or 0,
                    "successful": row["successful"] or 0,
                    "failed": row["failed"] or 0,
                    "avg_llm_latency_ms": round(row["avg_llm_latency"] or 0.0, 1),
                    "avg_exec_latency_ms": round(row["avg_exec_latency"] or 0.0, 1),
                    "highest_level": row["highest_level"] or 1
                }
            return {
                "total_decisions": 0, "successful": 0, "failed": 0,
                "avg_llm_latency_ms": 0.0, "avg_exec_latency_ms": 0.0, "highest_level": 1
            }
