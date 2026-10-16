"""
Provider-agnostic LLM Client for Shapez AI.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List
import httpx

logger = logging.getLogger("ShapezAI.LLM")

class LLMClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:18088/v1",
        api_key: str = "local",
        model: str = "default",
        timeout: float = 60.0
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """Send chat request and parse JSON response along with true reasoning text and timing."""
        import time
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        duration_ms = (time.perf_counter() - t0) * 1000.0

        message_obj = data["choices"][0]["message"]
        content = message_obj.get("content", "") or ""

        # 1. Check native reasoning_content field
        reasoning = message_obj.get("reasoning_content", "") or ""

        # 2. Check embedded <think> tag if reasoning_content is empty
        if not reasoning:
            think_match = re.search(r"<think>([\s\S]*?)</think>", content)
            if think_match:
                reasoning = think_match.group(1).strip()

        plan_dict = self._extract_json(content)
        plan_dict["_meta"] = {
            "reasoning_content": reasoning,
            "duration_ms": round(duration_ms, 2),
            "model": self.model,
            "timestamp": time.time()
        }
        return plan_dict

    def _extract_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        # Strip <think>...</think> if present
        text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
        # Find json block inside ```json ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
        else:
            # Match first { to last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start:end+1]

        return json.loads(text)
