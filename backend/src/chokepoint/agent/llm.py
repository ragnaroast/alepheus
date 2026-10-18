"""Abstract LLM client with Gemini (free), Groq, and Ollama backends.

Swappable via AGENT_MODEL env var:
  - gemini-2.5-flash (default, free tier)
  - groq/llama-3.3-70b-versatile
  - ollama/qwen3
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from chokepoint.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ToolDef:
    """Tool definition for the agent."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema
    function: Callable


@dataclass
class ToolCall:
    """A tool call request from the LLM."""
    name: str
    arguments: Dict[str, Any]
    call_id: str = ""


@dataclass
class Message:
    """A conversation message."""
    role: str  # user, assistant, tool
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""
    name: str = ""


class LLMClient(ABC):
    """Abstract LLM client interface."""

    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        tools: List[ToolDef],
        temperature: float = 0.0,
    ) -> Message:
        """Send messages and get a response, possibly with tool calls."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Return the model name."""
        ...


class GeminiClient(LLMClient):
    """Google Gemini client using the google-genai SDK."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        self._model = model
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from google import genai
            s = get_settings()
            self._client = genai.Client(api_key=s.gemini_api_key)

    def name(self) -> str:
        return self._model

    def chat(
        self,
        messages: List[Message],
        tools: List[ToolDef],
        temperature: float = 0.0,
    ) -> Message:
        self._ensure_client()
        from google.genai import types

        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            if msg.role == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=msg.content)],
                ))
            elif msg.role == "assistant":
                parts = []
                if msg.content:
                    parts.append(types.Part(text=msg.content))
                for tc in msg.tool_calls:
                    parts.append(types.Part(function_call=types.FunctionCall(
                        name=tc.name,
                        args=tc.arguments,
                    )))
                contents.append(types.Content(role="model", parts=parts))
            elif msg.role == "tool":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(function_response=types.FunctionResponse(
                        name=msg.name,
                        response={"result": msg.content},
                    ))],
                ))

        # Convert tools to Gemini function declarations
        function_declarations = []
        for tool in tools:
            function_declarations.append(types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
            ))

        config = types.GenerateContentConfig(
            temperature=temperature,
            tools=[types.Tool(function_declarations=function_declarations)] if function_declarations else None,
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return Message(role="assistant", content=f"LLM error: {e}")

        # Parse response
        result_msg = Message(role="assistant", content="")

        if response.candidates:
            candidate = response.candidates[0]
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    result_msg.content += part.text
                elif hasattr(part, "function_call") and part.function_call:
                    result_msg.tool_calls.append(ToolCall(
                        name=part.function_call.name,
                        arguments=dict(part.function_call.args) if part.function_call.args else {},
                        call_id=f"call_{len(result_msg.tool_calls)}",
                    ))

        return result_msg


class OllamaClient(LLMClient):
    """Ollama local LLM client."""

    def __init__(self, model: str = "qwen3"):
        self._model = model

    def name(self) -> str:
        return f"ollama/{self._model}"

    def chat(
        self,
        messages: List[Message],
        tools: List[ToolDef],
        temperature: float = 0.0,
    ) -> Message:
        try:
            import ollama
        except ImportError:
            return Message(role="assistant", content="Ollama SDK not installed. pip install ollama")

        # Convert messages
        ollama_msgs = []
        for msg in messages:
            ollama_msgs.append({
                "role": msg.role if msg.role != "tool" else "tool",
                "content": msg.content,
            })

        # Convert tools to Ollama format (OpenAI-compatible)
        ollama_tools = []
        for tool in tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })

        try:
            response = ollama.chat(
                model=self._model,
                messages=ollama_msgs,
                tools=ollama_tools if ollama_tools else None,
            )
        except Exception as e:
            return Message(role="assistant", content=f"Ollama error: {e}")

        result = Message(role="assistant", content=response.message.content or "")

        if response.message.tool_calls:
            for tc in response.message.tool_calls:
                result.tool_calls.append(ToolCall(
                    name=tc.function.name,
                    arguments=tc.function.arguments or {},
                ))

        return result


def create_llm_client(model: Optional[str] = None) -> LLMClient:
    """Factory: create the appropriate LLM client based on model name.

    Args:
        model: model identifier. If None, uses AGENT_MODEL from settings.

    Returns:
        LLMClient instance
    """
    if model is None:
        model = get_settings().agent_model

    if model.startswith("ollama/"):
        return OllamaClient(model.split("/", 1)[1])
    elif model.startswith("groq/"):
        # Groq uses OpenAI-compatible API — could add later
        logger.warning("Groq client not yet implemented, falling back to Gemini")
        return GeminiClient()
    else:
        # Default: Gemini
        return GeminiClient(model)
