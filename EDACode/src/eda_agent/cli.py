"""CLI entry point for EDA Agent.

Provides an interactive REPL and one-shot execution modes.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from eda_agent.core.agent import EDAAgent
from eda_agent.core.context import AgentContext
from eda_agent.providers.anthropic_provider import AnthropicProvider
from eda_agent.providers.openai_provider import OpenAIProvider
from eda_agent.tools.bash import BashTool
from eda_agent.tools.file_tools import (
    DiffTool,
    FileEditTool,
    FileReadTool,
    FileWriteTool,
    GlobTool,
    GrepTool,
)
from eda_agent.tools.registry import get_default_registry
from eda_agent.tools.background_tools import (
    BackgroundResultsTool,
    BackgroundStatusTool,
    BackgroundSubmitTool,
)
from eda_agent.tools.eda.planning_tools import TaskPlanTool
from eda_agent.tools.todo_tools import SetTodoListTool


def register_all_tools(registry: Any) -> None:
    """Register all built-in tools to the registry."""
    # Code tools
    registry.register(BashTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(FileEditTool())
    registry.register(GlobTool())
    registry.register(GrepTool())
    registry.register(DiffTool())

    # Planning & task tracking (pure Python, no EDA SDK dependency)
    registry.register(TaskPlanTool())
    registry.register(SetTodoListTool())

    # Background execution (pure Python)
    registry.register(BackgroundSubmitTool())
    registry.register(BackgroundStatusTool())
    registry.register(BackgroundResultsTool())


async def interactive_repl(agent: EDAAgent, console: Console) -> None:
    """Run the interactive REPL."""
    console.print(Panel.fit(
        "[bold cyan]EDA Agent[/bold cyan] — EDA Agent for Analog Circuit Design\n"
        "Type 'exit' or 'quit' to leave, 'reset' to clear history.",
        title="Welcome",
    ))

    while True:
        try:
            user_input = Prompt.ask("[bold green]>>>[/bold green]")
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!")
            break

        user_input = user_input.strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            console.print("Goodbye!")
            break
        if user_input.lower() == "reset":
            agent.reset()
            console.print("[yellow]Conversation history cleared.[/yellow]")
            continue

        with console.status("[bold blue]Thinking...[/bold blue]"):
            response = await agent.run(user_input, on_progress=lambda stage, data: None)

        console.print(Markdown(response))
        console.print()


async def run_once(agent: EDAAgent, query: str, console: Console) -> str:
    """Run a single query and return the response."""
    response = await agent.run(query, on_progress=lambda stage, data: None)
    console.print(Markdown(response))
    return response


def create_provider(args: argparse.Namespace) -> Any:
    """Create the LLM provider based on CLI arguments."""
    if args.provider == "anthropic":
        return AnthropicProvider(
            api_key=args.api_key or os.environ.get("ANTHROPIC_API_KEY"),
            default_model=args.model or "claude-3-5-sonnet-20241022",
        )
    else:
        return OpenAIProvider(
            api_key=args.api_key or os.environ.get("OPENAI_API_KEY"),
            base_url=args.base_url or os.environ.get("OPENAI_BASE_URL"),
            default_model=args.model or "gpt-4o",
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EDA Agent — EDA-focused code agent for analog circuit design",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM provider to use",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model identifier (e.g., gpt-4o, claude-3-5-sonnet-20241022)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for the selected provider",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Base URL for OpenAI-compatible APIs",
    )
    parser.add_argument(
        "--project-root",
        default=os.getcwd(),
        help="Project root directory",
    )
    parser.add_argument(
        "-q", "--query",
        default=None,
        help="Single query mode (non-interactive)",
    )

    args = parser.parse_args()

    # Check API key
    if args.provider == "anthropic" and not (args.api_key or os.environ.get("ANTHROPIC_API_KEY")):
        print("Error: ANTHROPIC_API_KEY not set. Use --api-key or set the environment variable.")
        sys.exit(1)
    if args.provider == "openai" and not (args.api_key or os.environ.get("OPENAI_API_KEY")):
        print("Error: OPENAI_API_KEY not set. Use --api-key or set the environment variable.")
        sys.exit(1)

    # Setup
    console = Console()
    registry = get_default_registry()
    register_all_tools(registry)

    provider = create_provider(args)
    context = AgentContext(project_root=args.project_root)

    agent = EDAAgent(
        provider=provider,
        registry=registry,
        context=context,
    )

    if args.query:
        asyncio.run(run_once(agent, args.query, console))
    else:
        asyncio.run(interactive_repl(agent, console))


if __name__ == "__main__":
    main()
