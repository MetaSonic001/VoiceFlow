"""
voiceflow.plugins.llm — LLM plugin base class and built-in implementations.

Available implementations:
  GroqLLM       — Groq API (llama-3.1-70b, fast, cheap)
  OpenAILLM     — OpenAI GPT-4o / o1
  AnthropicLLM  — Anthropic Claude
  OllamaLLM     — Local Ollama server
  GeminiLLM     — Google Gemini
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger("voiceflow.llm")


class LLMPlugin(ABC):
    """Base class for all LLM implementations."""

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        context: str = "",
        tools: list[dict] = [],
        history: list[dict] = [],
    ) -> str:
        """Return the assistant reply text."""
        ...


class GroqLLM(LLMPlugin):
    """Groq API — ultra-fast inference for Llama, Mixtral, Gemma."""

    def __init__(self, api_key: str, model: str = "llama-3.1-70b-versatile"):
        self.api_key = api_key
        self.model = model

    async def chat(self, system_prompt: str, user_message: str, context: str = "",
                   tools: list[dict] = [], history: list[dict] = []) -> str:
        import httpx
        messages = [{"role": "system", "content": f"{system_prompt}\n\n{context}".strip()}]
        messages.extend(history[-10:])  # keep last 10 turns
        messages.append({"role": "user", "content": user_message})
        payload: dict[str, Any] = {"model": self.model, "messages": messages,
                                    "max_tokens": 1024, "temperature": 0.4}
        if tools:
            payload["tools"] = tools
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}",
                             "Content-Type": "application/json"},
                    json=payload,
                )
                resp.raise_for_status()
                choice = resp.json()["choices"][0]["message"]
                # handle tool call if returned
                if choice.get("tool_calls"):
                    return json.dumps(choice["tool_calls"][0])
                return choice.get("content", "")
        except Exception as exc:
            logger.error("[GroqLLM] error: %s", exc)
            return ""


class OpenAILLM(LLMPlugin):
    """OpenAI chat completions — GPT-4o, o1, etc."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model

    async def chat(self, system_prompt: str, user_message: str, context: str = "",
                   tools: list[dict] = [], history: list[dict] = []) -> str:
        import httpx
        messages = [{"role": "system", "content": f"{system_prompt}\n\n{context}".strip()}]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_message})
        payload: dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            payload["tools"] = tools
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                choice = resp.json()["choices"][0]["message"]
                if choice.get("tool_calls"):
                    return json.dumps(choice["tool_calls"][0])
                return choice.get("content", "")
        except Exception as exc:
            logger.error("[OpenAILLM] error: %s", exc)
            return ""


class AnthropicLLM(LLMPlugin):
    """Anthropic Claude — claude-3-5-sonnet/haiku."""

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        self.api_key = api_key
        self.model = model

    async def chat(self, system_prompt: str, user_message: str, context: str = "",
                   tools: list[dict] = [], history: list[dict] = []) -> str:
        import httpx
        anthropic_history = [{"role": m["role"], "content": m["content"]}
                             for m in history[-10:] if m.get("role") in ("user", "assistant")]
        anthropic_history.append({"role": "user", "content": user_message})
        system_text = f"{system_prompt}\n\n{context}".strip()
        payload: dict[str, Any] = {"model": self.model, "max_tokens": 1024,
                                    "system": system_text, "messages": anthropic_history}
        if tools:
            payload["tools"] = [{"name": t["function"]["name"],
                                  "description": t["function"].get("description", ""),
                                  "input_schema": t["function"]["parameters"]} for t in tools]
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                    json=payload,
                )
                resp.raise_for_status()
                content = resp.json()["content"]
                for block in content:
                    if block["type"] == "text":
                        return block["text"]
                    if block["type"] == "tool_use":
                        return json.dumps({"name": block["name"], "arguments": block["input"]})
        except Exception as exc:
            logger.error("[AnthropicLLM] error: %s", exc)
        return ""


class OllamaLLM(LLMPlugin):
    """Local Ollama server — any model pulled locally."""

    def __init__(self, model: str = "llama3.2", host: str = "localhost", port: int = 11434):
        self.model = model
        self.base_url = f"http://{host}:{port}"

    async def chat(self, system_prompt: str, user_message: str, context: str = "",
                   tools: list[dict] = [], history: list[dict] = []) -> str:
        import httpx
        messages = [{"role": "system", "content": f"{system_prompt}\n\n{context}".strip()}]
        messages.extend(history[-6:])
        messages.append({"role": "user", "content": user_message})
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": messages, "stream": False},
                )
                resp.raise_for_status()
                return resp.json().get("message", {}).get("content", "")
        except Exception as exc:
            logger.error("[OllamaLLM] error: %s", exc)
            return ""


class GeminiLLM(LLMPlugin):
    """Google Gemini — gemini-2.0-flash, gemini-1.5-pro."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model

    async def chat(self, system_prompt: str, user_message: str, context: str = "",
                   tools: list[dict] = [], history: list[dict] = []) -> str:
        import httpx
        contents = []
        for m in history[-10:]:
            role = "user" if m.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": user_message}]})
        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": f"{system_prompt}\n\n{context}".strip()}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.4},
        }
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model}:generateContent?key={self.api_key}")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                parts = resp.json()["candidates"][0]["content"]["parts"]
                return "".join(p.get("text", "") for p in parts)
        except Exception as exc:
            logger.error("[GeminiLLM] error: %s", exc)
            return ""
