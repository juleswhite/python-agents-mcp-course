"""
LLM Abstraction Layer - Tutorial 02

Provides a unified interface for different LLM providers.
Supports OpenAI, Anthropic (Claude), and Google (Gemini).
"""

import os
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx


# === Types ===

@dataclass
class Message:
    """A message in the conversation."""
    role: Literal["user", "assistant", "system"]
    content: str


@dataclass
class Tool:
    """A tool definition for the LLM."""
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCall:
    """A tool call made by the LLM."""
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Response from the LLM."""
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(self, messages: list[Message], tools: list[Tool] | None = None) -> LLMResponse:
        """Send messages to the LLM and get a response."""
        pass


# === Providers ===

class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model

    async def chat(self, messages: list[Message], tools: list[Tool] | None = None) -> LLMResponse:
        system_message = next((m for m in messages if m.role == "system"), None)
        other_messages = [m for m in messages if m.role != "system"]

        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": m.role, "content": m.content} for m in other_messages],
        }

        if system_message:
            body["system"] = system_message.content

        if tools:
            body["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in tools
            ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json=body,
                timeout=60.0,
            )

            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.status_code} - {response.text}")

            data = response.json()

        content: str | None = None
        tool_calls: list[ToolCall] = []

        for block in data["content"]:
            if block["type"] == "text":
                content = block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append(ToolCall(
                    name=block["name"],
                    arguments=block["input"],
                ))

        return LLMResponse(content=content, tool_calls=tool_calls)


class OpenAIProvider(LLMProvider):
    """OpenAI provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model

    async def chat(self, messages: list[Message], tools: list[Tool] | None = None) -> LLMResponse:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }

        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=body,
                timeout=60.0,
            )

            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

            data = response.json()

        choice = data["choices"][0]
        message = choice["message"]

        tool_calls: list[ToolCall] = []
        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                tool_calls.append(ToolCall(
                    name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"]),
                ))

        return LLMResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
        )


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model

    async def chat(self, messages: list[Message], tools: list[Tool] | None = None) -> LLMResponse:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in messages if m.role != "system"
        ]

        system_instruction = next((m for m in messages if m.role == "system"), None)

        body: dict[str, Any] = {
            "contents": contents,
        }

        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction.content}]}

        if tools:
            body["tools"] = [{
                "functionDeclarations": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    }
                    for t in tools
                ],
            }]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json=body,
                timeout=60.0,
            )

            if response.status_code != 200:
                raise Exception(f"Gemini API error: {response.status_code} - {response.text}")

            data = response.json()

        candidate = data["candidates"][0]
        parts = candidate["content"]["parts"]

        content: str | None = None
        tool_calls: list[ToolCall] = []

        for part in parts:
            if "text" in part:
                content = part["text"]
            elif "functionCall" in part:
                tool_calls.append(ToolCall(
                    name=part["functionCall"]["name"],
                    arguments=part["functionCall"].get("args", {}),
                ))

        return LLMResponse(content=content, tool_calls=tool_calls)


# === Factory ===

def create_llm_from_env() -> LLMProvider:
    """Create an LLM provider based on environment variables."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("Using Anthropic Claude")
        return AnthropicProvider(os.environ["ANTHROPIC_API_KEY"])
    if os.environ.get("OPENAI_API_KEY"):
        print("Using OpenAI")
        return OpenAIProvider(os.environ["OPENAI_API_KEY"])
    if os.environ.get("GEMINI_API_KEY"):
        print("Using Google Gemini")
        return GeminiProvider(os.environ["GEMINI_API_KEY"])
    raise Exception(
        "No API key found. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY"
    )
