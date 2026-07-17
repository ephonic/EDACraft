"""Base LLM provider interface.

Abstracts over OpenAI, Anthropic, and local inference backends.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class Message:
    """A chat message."""

    role: str  # system, user, assistant, tool
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class Choice:
    """A completion choice."""

    message: Message
    finish_reason: Optional[str] = None


@dataclass
class StreamChunk:
    """A chunk from a streaming response."""

    delta: Message
    finish_reason: Optional[str] = None


class BaseProvider(abc.ABC):
    """Abstract base class for LLM providers."""

    @abc.abstractmethod
    async def chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Choice:
        """Send a chat completion request.

        Args:
            messages: Conversation history.
            tools: Available tool schemas for function calling.
            model: Model identifier.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            stream: Whether to stream the response.

        Returns:
            A Choice containing the assistant's response.
        """
        ...

    @abc.abstractmethod
    async def chat_completion_stream(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion response."""
        ...

    @abc.abstractmethod
    def get_default_model(self) -> str:
        """Return the default model for this provider."""
        ...
