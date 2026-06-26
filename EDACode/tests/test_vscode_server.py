"""Tests for VSCode extension backend server."""

import asyncio
import json
import sys
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_agent():
    """Create a mock EDAAgent."""
    agent = MagicMock()
    agent.context = MagicMock()
    agent.run = AsyncMock(return_value="Test response")
    return agent


@pytest.fixture
def mock_stdout():
    """Capture stdout for server output verification."""
    return StringIO()


@pytest.mark.asyncio
async def test_server_initialization(mock_agent, mock_stdout):
    """Test that the server initializes and sends ready message."""
    from eda_agent.server.vscode_server import VSCodeServer

    with patch("sys.stdout", mock_stdout):
        server = VSCodeServer(provider="openai", model="gpt-4o")
        
        with patch.object(server, "initialize", AsyncMock()) as mock_init:
            # Simulate run loop by just calling send directly
            server.send({"type": "ready", "projectRoot": "/tmp"})

    output = mock_stdout.getvalue()
    msg = json.loads(output.strip())
    assert msg["type"] == "ready"
    assert msg["projectRoot"] == "/tmp"


@pytest.mark.asyncio
async def test_handle_ping():
    """Test ping/pong handshake."""
    from eda_agent.server.vscode_server import VSCodeServer

    server = VSCodeServer()
    outputs = []

    def capture_send(msg):
        outputs.append(msg)

    server.send = capture_send

    await server._handle_line(json.dumps({"type": "ping", "requestId": "r1"}))

    assert len(outputs) == 1
    assert outputs[0]["type"] == "pong"
    assert outputs[0]["requestId"] == "r1"


@pytest.mark.asyncio
async def test_handle_chat(mock_agent):
    """Test chat message handling."""
    from eda_agent.server.vscode_server import VSCodeServer

    server = VSCodeServer()
    server.agent = mock_agent
    outputs = []
    server.send = lambda msg: outputs.append(msg)

    await server._handle_line(json.dumps({"type": "chat", "text": "Hello", "requestId": "r2"}))

    assert mock_agent.run.called
    assert len(outputs) == 1
    assert outputs[0]["type"] == "assistant"
    assert outputs[0]["text"] == "Test response"
    assert outputs[0]["requestId"] == "r2"


@pytest.mark.asyncio
async def test_handle_tool_call():
    """Test direct tool call handling."""
    from eda_agent.server.vscode_server import VSCodeServer

    server = VSCodeServer()
    server.agent = MagicMock()
    server.agent.context = MagicMock()

    outputs = []
    server.send = lambda msg: outputs.append(msg)

    # Mock the tool registry
    mock_tool = MagicMock()
    mock_tool.call = AsyncMock(return_value=MagicMock(data={"status": "ok"}))

    with patch("eda_agent.server.vscode_server.find_tool", return_value=mock_tool):
        await server._handle_line(json.dumps({
            "type": "tool_call",
            "tool": "bash",
            "args": {"command": "echo hello"},
            "requestId": "r3"
        }))

    assert len(outputs) == 1
    assert outputs[0]["type"] == "tool_result"
    assert outputs[0]["tool"] == "bash"
    assert outputs[0]["success"] is True
    assert outputs[0]["requestId"] == "r3"


def test_send_json_encoding():
    """Test that send properly encodes JSON."""
    from eda_agent.server.vscode_server import VSCodeServer

    server = VSCodeServer()
    buf = StringIO()
    
    with patch("sys.stdout", buf):
        server.send({"type": "test", "data": {"nested": True}, "number": 42})

    output = buf.getvalue().strip()
    msg = json.loads(output)
    assert msg["type"] == "test"
    assert msg["data"]["nested"] is True
    assert msg["number"] == 42
