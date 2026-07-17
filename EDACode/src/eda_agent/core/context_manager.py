"""Context management with token budgeting and compaction for EDA Agent.

Inspired by Claude Code's context compaction system, adapted for EDA workflows.
Supports:
- Token budget tracking and estimation
- Automatic context compaction when approaching budget
- Manual compaction triggers
- Summarization of tool execution history
- Preservation of critical design state across compaction
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from eda_agent.providers.base import Message


@dataclass
class CompactionResult:
    """Result of a context compaction operation."""

    success: bool
    original_count: int
    compacted_count: int
    tokens_saved: int
    summary: str = ""
    error: str = ""


class ContextManager:
    """Manages conversation context with token budgeting and automatic compaction.

    Token budget strategy:
    - Reserve tokens for system prompt (~2000)
    - Reserve tokens for current turn (~4000)
    - Remaining budget for conversation history
    - When history exceeds 70% of remaining budget, trigger compaction
    """

    def __init__(
        self,
        system_prompt: str,
        max_tokens: int = 128000,
        reserve_tokens: int = 8000,
        compaction_threshold: float = 0.6,
        min_messages_before_compaction: int = 10,
        estimate_tokens_fn: Optional[Callable[[str], int]] = None,
    ) -> None:
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.compaction_threshold = compaction_threshold
        self.min_messages_before_compaction = min_messages_before_compaction
        self._messages: List[Message] = []
        self._compaction_count = 0
        self._total_tokens_ever = 0
        self._summaries: List[Dict[str, Any]] = []
        self._estimate_tokens_fn = estimate_tokens_fn or self._default_token_estimator
        self._active_task: Optional[str] = None
        self._task_number: int = 0
        self._snapshot_path: Optional[str] = None
        self._eda_api_injected: bool = False

        # Initialize with system message
        self._messages.append(Message(role="system", content=system_prompt))

    @property
    def messages(self) -> List[Message]:
        """Get current message list with active task injected if present.

        Uses a lightweight list wrapper instead of deep-copy to avoid O(n)
        overhead on every LLM call. The task injection is cached until
        _active_task or _messages changes.
        """
        # Fast path: no task lock, no copy needed (messages are immutable-ish)
        if not self._active_task:
            return self._messages

        # Cached injection: only rebuild when dirty
        if hasattr(self, "_cached_messages") and getattr(self, "_cached_messages_rev", None) == id(self._messages):
            if getattr(self, "_cached_task", None) == self._active_task:
                return self._cached_messages

        result = list(self._messages)  # shallow copy of references only
        if len(result) > 0 and result[0].role == "system":
            task_prompt = (
                f"\n\n[当前任务主线]\n"
                f"你正在执行以下任务，后续所有操作必须围绕此主线展开，不得偏离：\n"
                f"{self._active_task}\n"
                f"[任务主线结束]"
            )
            result[0] = Message(
                role="system",
                content=result[0].content + task_prompt,
            )
        self._cached_messages = result
        self._cached_messages_rev = id(self._messages)
        self._cached_task = self._active_task
        return result

    @property
    def message_count(self) -> int:
        """Number of messages in context (excluding system)."""
        return len(self._messages) - 1  # Exclude system

    @property
    def compaction_count(self) -> int:
        """Number of times compaction has been performed."""
        return self._compaction_count

    def set_task(self, task_description: str) -> None:
        """Lock the current task description into the system prompt.

        The task will be appended to the system message on every messages()
        call until clear_task() is called, ensuring the agent stays on track.
        """
        self._active_task = task_description

    def clear_task(self) -> None:
        """Clear the active task lock."""
        self._active_task = None

    def _invalidate_cache(self) -> None:
        """Invalidate the messages cache when _messages mutates."""
        self._cached_messages_rev = None

    def add_user_message(self, content: str) -> None:
        """Add a user message to the context."""
        self._messages.append(Message(role="user", content=content))
        self._invalidate_cache()

    def add_assistant_message(self, content: Optional[str], tool_calls: Optional[List[Dict]] = None) -> None:
        """Add an assistant message to the context."""
        self._messages.append(Message(
            role="assistant",
            content=content,
            tool_calls=tool_calls,
        ))
        self._invalidate_cache()

    def add_tool_result(self, content: Any, tool_call_id: str, name: str) -> None:
        """Add a tool result message to the context."""
        self._messages.append(Message(
            role="tool",
            content=content if isinstance(content, str) else json.dumps(content, default=str),
            tool_call_id=tool_call_id,
            name=name,
        ))
        self._invalidate_cache()

    def add_system_message(self, content: str) -> None:
        """Add a temporary system message to guide the model mid-conversation.

        Used for convergence nudges (e.g. "Please synthesize and reply now").
        These messages are preserved during normal operation but cleared on reset.
        """
        self._messages.append(Message(role="system", content=content))
        self._invalidate_cache()

    def inject_eda_api(self, api_text: str) -> bool:
        """Inject EDA API reference into the system prompt (first message).

        This is done once per conversation to avoid bloating the system
        prompt for non-EDA queries. The API text is appended to the
        existing system prompt content.

        Returns:
            True if injected, False if already present.
        """
        if self._eda_api_injected:
            return False
        if not self._messages or self._messages[0].role != "system":
            return False

        existing = self._messages[0].content or ""
        # Guard against double-injection in case of manual tampering
        if "EDA Python API Reference" in existing:
            self._eda_api_injected = True
            return False

        self._messages[0] = Message(
            role="system",
            content=existing + "\n\n" + api_text,
        )
        self._eda_api_injected = True
        self._invalidate_cache()
        return True

    def is_eda_api_injected(self) -> bool:
        """Check whether EDA API reference has been injected."""
        return self._eda_api_injected

    def inject_knowledge(self, knowledge_text: str, tag: str = "") -> bool:
        """Inject arbitrary knowledge text into the system prompt.

        Unlike inject_eda_api, this allows multiple tagged injections
        and appends without replacing. Each tag can only be injected once.

        Args:
            knowledge_text: The text to inject.
            tag: A unique identifier for deduplication (e.g., "pyae:layout").

        Returns:
            True if injected, False if already present (by tag).
        """
        if not self._messages or self._messages[0].role != "system":
            return False

        # Lazy init injected tags set
        if not hasattr(self, "_injected_knowledge_tags"):
            self._injected_knowledge_tags: set = set()

        if tag and tag in self._injected_knowledge_tags:
            return False

        existing = self._messages[0].content or ""
        # Extra guard: check if exact text already present
        if knowledge_text.strip() in existing:
            if tag:
                self._injected_knowledge_tags.add(tag)
            return False

        self._messages[0] = Message(
            role="system",
            content=existing + "\n\n" + knowledge_text,
        )
        if tag:
            self._injected_knowledge_tags.add(tag)
        self._invalidate_cache()
        return True

    def has_knowledge_tag(self, tag: str) -> bool:
        """Check whether a specific knowledge tag has been injected."""
        return hasattr(self, "_injected_knowledge_tags") and tag in self._injected_knowledge_tags

    def get_injected_knowledge_tags(self) -> List[str]:
        """Return list of all injected knowledge tags."""
        if hasattr(self, "_injected_knowledge_tags"):
            return list(self._injected_knowledge_tags)
        return []

    def estimate_tokens(self, text: Optional[str] = None) -> int:
        """Estimate token count for text or entire context."""
        if text is not None:
            return self._estimate_tokens_fn(text)
        return sum(self._estimate_tokens_fn(m.content or "") for m in self._messages)

    def estimate_tokens_for_messages(self, messages: List[Message]) -> int:
        """Estimate tokens for a specific message list."""
        return sum(self._estimate_tokens_fn(m.content or "") for m in messages)

    def _get_actual_system_tokens(self) -> int:
        """Get the actual token count of the current system message(s).

        This may be larger than the original system_prompt because EDA API
        references and knowledge base chunks have been injected into it.
        """
        system_tokens = 0
        for m in self._messages:
            if m.role == "system":
                system_tokens += self._estimate_tokens_fn(m.content or "")
        return system_tokens

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current token budget status."""
        actual_system_tokens = self._get_actual_system_tokens()
        current_tokens = self.estimate_tokens()
        available = self.max_tokens - self.reserve_tokens - actual_system_tokens
        usage_ratio = current_tokens / available if available > 0 else 1.0

        return {
            "max_tokens": self.max_tokens,
            "reserve_tokens": self.reserve_tokens,
            "system_tokens": actual_system_tokens,
            "current_tokens": current_tokens,
            "available_tokens": available,
            "usage_ratio": usage_ratio,
            "message_count": self.message_count,
            "compaction_count": self._compaction_count,
            "should_compact": self._should_compact(),
        }

    def _should_compact(self) -> bool:
        """Check if compaction should be triggered."""
        total = self.estimate_tokens_for_messages(self._messages)
        actual_system_tokens = self._get_actual_system_tokens()
        available = self.max_tokens - self.reserve_tokens - actual_system_tokens
        if available <= 0:
            return True
        ratio = total / available
        if ratio >= self.compaction_threshold:
            return True
        if self.message_count < self.min_messages_before_compaction:
            return False
        # Near-threshold pre-emptive compact: if usage >85% of threshold, compact early
        return ratio >= self.compaction_threshold * 0.85

    def _compute_recent_keep_count(self) -> int:
        """Dynamically compute how many recent messages to keep.

        Keeps recent messages until their total token count reaches ~35% of the
        available budget, capped at 12 messages (6 turns). This prevents both
        the scenario where recent messages alone exceed the budget and the
        opposite case where keeping too many short messages defeats compaction.
        """
        actual_system_tokens = self._get_actual_system_tokens()
        available = self.max_tokens - self.reserve_tokens - actual_system_tokens
        target_recent_tokens = int(available * 0.35)

        kept = 0
        accumulated = 0
        # Walk from the end backward (skip system at index 0)
        for i in range(len(self._messages) - 1, 0, -1):
            msg_tokens = self._estimate_tokens_fn(self._messages[i].content or "")
            if accumulated + msg_tokens > target_recent_tokens and kept >= 4:
                break
            accumulated += msg_tokens
            kept += 1
            if kept >= 12:  # Cap at 12 messages (6 turns)
                break
        return max(kept, 4)  # Always keep at least 4 (2 turns)

    def compact(self, provider: Optional[Any] = None, aggressive: bool = False) -> CompactionResult:
        """Compact the conversation history by summarizing old messages.

        Strategy:
        1. Keep system prompt (always first)
        2. Keep last N turns (dynamic based on token budget)
        3. Summarize middle section via LLM or heuristic
        4. Replace summarized section with a compact summary message

        Args:
            provider: Optional LLM provider for intelligent summarization.
                      If None, uses heuristic summarization.
            aggressive: If True, keep only the bare minimum (system + last 2 msgs).

        Returns:
            CompactionResult with statistics.
        """
        if len(self._messages) <= self.min_messages_before_compaction + 1:
            return CompactionResult(
                success=False,
                original_count=len(self._messages),
                compacted_count=len(self._messages),
                tokens_saved=0,
                error="Not enough messages to compact",
            )

        original_count = len(self._messages)
        original_tokens = self.estimate_tokens()

        try:
            # Partition messages
            system_msg = self._messages[0]

            if aggressive:
                # Aggressive: keep only system + last 1 message
                keep_count = min(1, len(self._messages) - 1)
            else:
                keep_count = self._compute_recent_keep_count()

            recent_messages = self._messages[-keep_count:] if len(self._messages) > keep_count else []
            old_messages = self._messages[1:-keep_count] if len(self._messages) > keep_count + 1 else []

            if not old_messages:
                return CompactionResult(
                    success=False,
                    original_count=original_count,
                    compacted_count=original_count,
                    tokens_saved=0,
                    error="Not enough old messages to compact",
                )

            # Generate summary
            if provider:
                summary = self._generate_llm_summary(old_messages, provider)
            else:
                summary = self._generate_heuristic_summary(old_messages)

            # Build compacted context
            self._messages = [system_msg]
            if summary:
                mode_label = "aggressive" if aggressive else "standard"
                self._messages.append(Message(
                    role="user",
                    content=f"[Previous conversation summary ({mode_label}, {len(old_messages)} messages compacted)]\n\n{summary}",
                ))
                self._messages.append(Message(
                    role="assistant",
                    content="Understood. I have the context from our previous conversation.",
                ))

            self._messages.extend(recent_messages)
            self._compaction_count += 1

            new_tokens = self.estimate_tokens()
            tokens_saved = original_tokens - new_tokens

            self._summaries.append({
                "compaction_number": self._compaction_count,
                "original_messages": original_count - 1,  # Excluding system
                "summarized_messages": len(old_messages),
                "summary_length": len(summary),
                "tokens_saved": tokens_saved,
            })
            # Keep only the most recent 50 summaries to prevent unbounded growth
            if len(self._summaries) > 50:
                self._summaries = self._summaries[-50:]

            # Save snapshot of compacted context to file
            self._save_context_snapshot()

            return CompactionResult(
                success=True,
                original_count=original_count,
                compacted_count=len(self._messages),
                tokens_saved=tokens_saved,
                summary=summary[:200] + "..." if len(summary) > 200 else summary,
            )

        except Exception as e:
            return CompactionResult(
                success=False,
                original_count=original_count,
                compacted_count=original_count,
                tokens_saved=0,
                error=str(e),
            )

    def compact_if_needed(self, provider: Optional[Any] = None) -> Optional[CompactionResult]:
        """Check budget and compact if threshold exceeded."""
        if self._should_compact():
            return self.compact(provider)
        return None

    def force_compact(self, provider: Optional[Any] = None) -> CompactionResult:
        """Force compaction regardless of threshold."""
        return self.compact(provider)

    def force_compact_aggressive(self, provider: Optional[Any] = None) -> CompactionResult:
        """Force aggressive compaction keeping only the most recent messages."""
        return self.compact(provider, aggressive=True)

    def reset(self) -> None:
        """Clear all conversation history, keeping only system prompt."""
        self._messages = [Message(role="system", content=self.system_prompt)]
        self._compaction_count = 0
        self._summaries = []
        self._eda_api_injected = False
        if hasattr(self, "_injected_knowledge_tags"):
            self._injected_knowledge_tags.clear()
        self._invalidate_cache()

    def get_summary_history(self) -> List[Dict[str, Any]]:
        """Get history of all compaction operations."""
        return self._summaries.copy()

    # ── Task snapshot management ──

    def set_task_number(self, task_no: int) -> None:
        """Set the current task number for snapshot file naming."""
        self._task_number = task_no
        self._snapshot_path = f".context-task#{task_no}.md"

    def clear_task_snapshot(self) -> None:
        """Delete the snapshot file for the current task."""
        if self._snapshot_path and os.path.exists(self._snapshot_path):
            try:
                os.remove(self._snapshot_path)
            except OSError:
                pass
        self._snapshot_path = None

    def _save_context_snapshot(self) -> None:
        """Save current compacted context to a markdown file."""
        if not self._snapshot_path:
            return
        try:
            lines = [
                f"# Context Snapshot — Task #{self._task_number}",
                "",
                f"**Compaction count:** {self._compaction_count}",
                f"**Messages:** {len(self._messages)}",
                f"**Tokens:** {self.estimate_tokens()}",
                "",
                "## Messages",
                "",
            ]
            for msg in self._messages:
                role = msg.role.upper()
                content = msg.content or ""
                lines.append(f"### {role}")
                lines.append("")
                lines.append(content)
                lines.append("")
                if msg.tool_calls:
                    lines.append("**Tool calls:**")
                    for tc in msg.tool_calls:
                        name = tc.get("function", {}).get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                        lines.append(f"- `{name}`")
                    lines.append("")
                lines.append("---")
                lines.append("")
            with open(self._snapshot_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception:
            pass  # Snapshot is best-effort

    def _generate_heuristic_summary(self, messages: List[Message]) -> str:
        """Generate a summary without LLM (fast, no extra API call).

        Extracts key information:
        - Designs opened/created
        - Tools executed
        - Files modified
        - Key decisions
        """
        designs = []
        tools_used = []
        files_modified = []
        key_exchanges = []

        for msg in messages:
            content = msg.content or ""
            role = msg.role

            if role == "user":
                # Keep the essence of user requests
                if len(content) < 200:
                    key_exchanges.append(f"User: {content}")

            elif role == "assistant":
                # Extract assistant's key conclusions
                if "已完成" in content or "Done" in content or "success" in content.lower():
                    key_exchanges.append(f"Agent completed: {content[:150]}")

            elif role == "tool":
                # Extract tool execution results
                try:
                    data = json.loads(content) if isinstance(content, str) else content
                    if isinstance(data, dict):
                        if "lib" in data and "cell" in data:
                            designs.append(f"{data['lib']}/{data['cell']}/{data.get('view', '')}")
                        if "status" in data:
                            tools_used.append(f"{msg.name}: {data['status']}")
                        if "filePath" in data:
                            files_modified.append(data["filePath"])
                except:
                    pass

        parts = []
        if designs:
            parts.append(f"Designs worked on: {', '.join(set(designs))}")
        if tools_used:
            parts.append(f"Tools executed: {', '.join(set(tools_used))}")
        if files_modified:
            parts.append(f"Files modified: {', '.join(set(files_modified))}")
        if key_exchanges:
            parts.append("Key exchanges:")
            parts.extend(key_exchanges[-5:])  # Keep last 5

        return "\n".join(parts) if parts else "Previous conversation about analog circuit design tasks."

    async def _generate_llm_summary(self, messages: List[Message], provider: Any) -> str:
        """Generate an intelligent summary using the LLM.

        Preserves original message roles so the provider (especially Anthropic)
        doesn't reject the request due to role alternation violations.
        """
        system_msg = Message(
            role="system",
            content=(
                "You are summarizing a conversation between a user and an EDA design assistant. "
                "Focus on: designs opened, tools used, key decisions, and current state. "
                "Be concise (under 500 tokens). Reply with the summary only."
            ),
        )
        # Truncate long content to avoid blowing up the summary API call's token budget
        truncated = [
            Message(
                role=msg.role,
                content=(msg.content or "")[:500],
            )
            for msg in messages
        ]

        try:
            from eda_agent.providers.base import Message as ProviderMessage
            response = await provider.chat_completion(
                messages=[system_msg] + truncated,
                temperature=0.1,
                max_tokens=1000,
            )
            return response.message.content or ""
        except Exception:
            return self._generate_heuristic_summary(messages)

    @staticmethod
    def _default_token_estimator(text: str) -> int:
        """Estimate token count from text.

        Fast approximation optimized for mixed CJK/Latin text.
        CJK chars ≈ 1.0 token each; Latin chars ≈ 0.25 token each.
        """
        if not text:
            return 0
        asian_chars = 0
        for c in text:
            cp = ord(c)
            if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF:
                asian_chars += 1
        latin_chars = len(text) - asian_chars
        estimated = int(asian_chars * 1.0 + latin_chars * 0.25)
        return max(1, estimated)

    def to_debug_info(self) -> Dict[str, Any]:
        """Generate debug information about context state."""
        budget = self.get_budget_status()
        return {
            "budget": budget,
            "compaction_count": self._compaction_count,
            "summaries": self._summaries,
            "message_breakdown": {
                "system": 1,
                "user": sum(1 for m in self._messages if m.role == "user"),
                "assistant": sum(1 for m in self._messages if m.role == "assistant"),
                "tool": sum(1 for m in self._messages if m.role == "tool"),
            },
        }
