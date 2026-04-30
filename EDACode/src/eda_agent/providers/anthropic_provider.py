"""Anthropic Claude provider implementation."""

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional

from eda_agent.providers.base import BaseProvider, Choice, Message, StreamChunk


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "claude-3-5-sonnet-20241022",
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = base_url
        self.default_model = default_model
        self._client: Optional[Any] = None

    @property
    def client(self) -> Any:
        if self._client is None:
            from anthropic import AsyncAnthropic
            kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = AsyncAnthropic(**kwargs)
        return self._client

    def _convert_messages(self, messages: List[Message]) -> tuple[str, List[Dict[str, Any]]]:
        """Convert to Anthropic format: system prompt + conversation."""
        system = ""
        convo: List[Dict[str, Any]] = []
        for msg in messages:
            if msg.role == "system":
                system = msg.content or ""
            elif msg.role == "tool":
                convo.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id or "",
                        "content": msg.content or "",
                    }],
                })
            else:
                content = msg.content or ""
                if msg.tool_calls:
                    # Assistant with tool calls
                    content_blocks: List[Dict[str, Any]] = []
                    if content:
                        content_blocks.append({"type": "text", "text": content})
                    for tc in msg.tool_calls:
                        args = tc.get("function", {}).get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args) if args else {}
                            except json.JSONDecodeError:
                                args = {}
                        elif not isinstance(args, dict):
                            args = {}
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": tc.get("function", {}).get("name", ""),
                            "input": args,
                        })
                    convo.append({"role": msg.role, "content": content_blocks})
                else:
                    convo.append({"role": msg.role, "content": content})
        return system, convo

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI-style tools to Anthropic tools."""
        result = []
        for t in tools:
            func = t.get("function", {})
            result.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {}),
            })
        return result

    async def chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Choice:
        system, convo = self._convert_messages(messages)
        kwargs: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": convo,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = await self.client.messages.create(**kwargs)

        content = ""
        tool_calls = None
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": block.input,
                    },
                })

        return Choice(
            message=Message(
                role="assistant",
                content=content or None,
                tool_calls=tool_calls,
            ),
            finish_reason=response.stop_reason,
        )

    async def chat_completion_stream(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        """True streaming implementation for Anthropic API.

        Yields text tokens as they arrive. Tool-use blocks are accumulated
        and yielded as a single final chunk so that the caller can process
        tool calls normally.
        """
        system, convo = self._convert_messages(messages)
        kwargs: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": convo,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": True,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        current_tool: Optional[Dict[str, Any]] = None
        tool_calls: List[Dict[str, Any]] = []
        finish_reason: Optional[str] = None
        tool_call_index = 0

        stream = await self.client.messages.create(**kwargs)
        async with stream:
            async for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    if block.type == "tool_use":
                        current_tool = {
                            "index": tool_call_index,
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": "",
                            },
                        }
                        # Notify immediately so frontend can show "calling tool..."
                        yield StreamChunk(
                            delta=Message(
                                role="assistant",
                                content=None,
                                tool_calls=[current_tool],
                            ),
                        )
                        tool_call_index += 1

                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        yield StreamChunk(
                            delta=Message(role="assistant", content=delta.text)
                        )
                    elif delta.type == "input_json_delta" and current_tool is not None:
                        current_tool["function"]["arguments"] += delta.partial_json

                elif event.type == "content_block_stop":
                    if current_tool is not None:
                        # Parse accumulated JSON arguments
                        args_str = current_tool["function"]["arguments"]
                        try:
                            current_tool["function"]["arguments"] = json.loads(args_str)
                        except json.JSONDecodeError:
                            pass
                        tool_calls.append(current_tool)
                        current_tool = None

                elif event.type == "message_delta":
                    finish_reason = event.delta.stop_reason

        # Yield final chunk with tool calls (if any) so agent.run() can process them
        if tool_calls:
            yield StreamChunk(
                delta=Message(
                    role="assistant",
                    content=None,
                    tool_calls=tool_calls,
                ),
                finish_reason=finish_reason,
            )
        else:
            yield StreamChunk(
                delta=Message(role="assistant", content=None),
                finish_reason=finish_reason,
            )

    def get_default_model(self) -> str:
        return self.default_model
