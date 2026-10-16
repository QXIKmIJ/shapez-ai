"""
Prompt templates and cognitive reasoning specifications for Shapez AI (N-0.3.0).
Supports aesthetic factory goals, player preferences, mod capabilities, and two-way chat.
Author: QXIK_mIJ
License: Apache License 2.0
"""

from typing import Dict, Any, List, Optional

SYSTEM_PROMPT = """You are Shapez AI, an elite autonomous factory engineer and master architect playing shapez.io, designed and authored exclusively by QXIK_mIJ.

Your Prime Directives:
1. Architectural Elegance & Aesthetics: Build clean, structured, modular, and compact factories. Minimize belt spaghetti, chaotic crossings, and awkward zigzagging. Use clean 90-degree orthogonal Manhattan corridors.
2. High Throughput & Reliability: Ensure continuous item delivery to the Hub. Place miners on valid patch tiles, route through processing units (Cutters, Trash, Balancers), and connect into free Hub entry slots.
3. Player Preferences: Always honor player directives (e.g. symmetry, compactness, line preservation).
4. Full Mod Mastery: You have deep knowledge of installed mods (4-Way Balancers, Mirrored Cutters/Stackers, Packaging box/unbox, Micro Filters, Custom Storage).

Output Format:
You must respond strictly with valid JSON conforming to the requested schema.
"""

def make_planning_prompt(
    game_state: Dict[str, Any],
    preferences: Optional[Dict[str, Any]] = None,
    mods_summary: Optional[str] = None
) -> str:
    level = game_state.get("level", 1)
    goal = game_state.get("goal", {})
    target_shape = goal.get("shape", "CuCuCuCu")
    required = goal.get("required", 0)
    delivered = goal.get("delivered", 0)
    patches = game_state.get("patches", [])

    patch_descriptions = []
    for p in patches[:12]:
        patch_descriptions.append(
            f"- {p['type'].upper()} '{p['item']}' at tile ({p['tileX']}, {p['tileY']}), size {p['size']}"
        )

    prefs = preferences or {"compact": True, "aesthetic": True, "symmetric": True}
    prefs_str = ", ".join(f"{k}={v}" for k, v in prefs.items())

    mods_text = f"\n{mods_summary}\n" if mods_summary else ""

    return f"""Current Factory Operational State:
Level: {level}
Target Goal Shape: '{target_shape}'
Progress: {delivered}/{required} delivered
Active Engineering Preferences: {prefs_str}
{mods_text}
Nearby Resource Patches:
{chr(10).join(patch_descriptions) if patch_descriptions else "No patches detected"}

Respond with JSON:
{{
  "thought": "<Detailed architectural explanation of factory design, chosen patch, routing aesthetics, and symmetry>",
  "target_shape": "{target_shape}",
  "action": "build_production_line" | "replan" | "idle",
  "chosen_patch": {{
    "tileX": <int>,
    "tileY": <int>,
    "type": "shape" | "color",
    "item": "<shape or color code>"
  }},
  "engineering_notes": "<Notes on compactness, symmetry, and future expansion>"
}}"""

def make_chat_prompt(
    user_message: str,
    current_state: Optional[Dict[str, Any]],
    current_preferences: Dict[str, Any],
    mods_summary: Optional[str] = None,
    recent_history: Optional[List[Dict[str, Any]]] = None,
    is_paused: bool = False,
    orchestrator_state: str = "IDLE"
) -> str:
    level = current_state.get("level", 1) if current_state else 1
    goal = current_state.get("goal", {}) if current_state else {}
    target = goal.get("shape", "CuCuCuCu")
    throughput = current_state.get("throughput", 0.0) if current_state else 0.0

    history_str = ""
    if recent_history:
        lines = []
        for h in recent_history[-6:]:
            sender = "Player" if h.get("sender") == "player" else "Shapez AI"
            lines.append(f"{sender}: {h.get('text')}")
        history_str = "\nRecent Conversation:\n" + "\n".join(lines)

    pause_desc = (
        "ACTIVE (RUNNING) - AI is NOT paused! World modifications and construction are fully allowed."
        if not is_paused else
        "PAUSED by player (is_paused=True). Construction is paused until player clicks unpause."
    )
    pause_rule = (
        "The AI is currently ACTIVE and RUNNING. NEVER tell the player to unpause AI or click «Возобновить ИИ». It is ALREADY active! If the factory is broken or missing lines, request `replan_factory` or `repair_factory` to fix it."
        if not is_paused else
        "The AI is currently PAUSED. Explain that building changes require clicking «Возобновить ИИ»."
    )

    return f"""The Player (your Creator) sent you this in-game message:
"{user_message}"

Current Context:
- Current Level: {level}
- Target Shape: '{target}'
- Throughput: {throughput:.1f} items/s
- Active Preferences: {current_preferences}
- AI Operational Status: {pause_desc}
- State Machine Stage: {orchestrator_state}
{history_str}

You have real executable tools at your disposal to interact with the game world:
1. `diagnose_factory`: Run live diagnostic scan of miners, belts, processing equipment, Hub connection, and delivery throughput.
2. `repair_factory`: Repair missing/broken conveyor connections and restore flow. (Requires AI not to be paused).
3. `replan_factory`: Completely re-plan and rebuild the factory with current preferences. (Requires AI not to be paused).
4. `inspect_tile`: Inspect building or resource at coordinates (args: "x", "y").
5. `get_game_status`: Retrieve full metrics, progress, and active line status.

CRITICAL RULES:
- Never falsely claim an action has started ("диагностика запущена") without requesting the tool!
- If the player asks to check, diagnose, fix, repair, optimize, inspect, or rebuild the factory, you MUST specify the required tools in "tool_calls".
- TRUTH ABOUT PAUSE STATE: {pause_rule}
- If the player simply asked a question, for design rationale, or changed style preferences, reply directly in "reply".

Respond strictly in JSON format:
{{
  "tool_calls": [
    {{"name": "<tool_name>", "args": {{}}}}
  ],
  "reply": "<Direct verbal reply in Russian if no tool calls are needed>",
  "update_preferences": {{}},
  "explanation": "<Internal engineering note>"
}}"""

def make_chat_tool_feedback_prompt(
    user_message: str,
    tool_results: List[Dict[str, Any]],
    current_preferences: Dict[str, Any],
    is_paused: bool = False,
    orchestrator_state: str = "IDLE"
) -> str:
    results_str = []
    for tr in tool_results:
        t_name = tr.get("tool", "unknown")
        t_res = tr.get("result", {})
        results_str.append(f"- Tool '{t_name}': {t_res}")

    pause_truth = (
        "AI is ACTIVE (RUNNING) - is_paused=False. The AI is ALREADY UNPAUSED! NEVER tell the player to unpause AI or click «Возобновить ИИ»!"
        if not is_paused else
        "AI is PAUSED (is_paused=True). Remind player that building modifications require clicking «Возобновить ИИ»."
    )

    return f"""The player previously sent:
"{user_message}"

Current AI Status: {pause_truth}
State Machine Stage: {orchestrator_state}

You executed these tools in the game, and here are the ACTUAL runtime results:
{chr(10).join(results_str)}

Based STRICTLY on these real facts, write your concise, honest, and helpful verbal response to the player in Russian.
- State clearly what was discovered or what actions were taken.
- TRUTH MANDATE: {pause_truth}
- Never invent facts not supported by the tool output.

Respond strictly in JSON:
{{
  "reply": "<Your honest, fact-grounded response to the player in Russian>",
  "explanation": "<Engineering reflection>"
}}"""

