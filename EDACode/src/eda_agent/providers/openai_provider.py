"""OpenAI-compatible provider implementation."""

from __future__ import annotations

import os
from typing import Any, AsyncIterator, Dict, List, Optional

from eda_agent.providers.base import BaseProvider, Choice, Message, StreamChunk


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI and OpenAI-compatible APIs (e.g., vLLM, llama.cpp server)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "gpt-4o",
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self.default_model = default_model
        self._client: Optional[Any] = None

    @property
    def client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI
            kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    def _convert_message(self, msg: Message) -> Dict[str, Any]:
        result: Dict[str, Any] = {"role": msg.role}
        if msg.content:
            result["content"] = msg.content
        if msg.tool_calls:
            result["tool_calls"] = msg.tool_calls
        if msg.tool_call_id:
            result["tool_call_id"] = msg.tool_call_id
        if msg.name:
            result["name"] = msg.name
        return result

    def _convert_chunk(self, chunk: Any) -> StreamChunk:
        delta = Message(role="assistant")
        if chunk.choices and chunk.choices[0].delta:
            d = chunk.choices[0].delta
            if d.content:
                delta.content = d.content
            if d.tool_calls:
                delta.tool_calls = [tc.model_dump() for tc in d.tool_calls]
        finish = chunk.choices[0].finish_reason if chunk.choices else None
        return StreamChunk(delta=delta, finish_reason=finish)

    async def chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Choice:
        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=[self._convert_message(m) for m in messages],
            tools=tools or [],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        msg = response.choices[0].message
        tool_calls = None
        if msg.tool_calls:
            tool_calls = [tc.model_dump() for tc in msg.tool_calls]
        return Choice(
            message=Message(
                role=msg.role,
                content=msg.content,
                tool_calls=tool_calls,
            ),
            finish_reason=response.choices[0].finish_reason,
        )

    async def chat_completion_stream(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        stream = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=[self._convert_message(m) for m in messages],
            tools=tools or [],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            yield self._convert_chunk(chunk)

    def get_default_model(self) -> str:
        return self.default_model
