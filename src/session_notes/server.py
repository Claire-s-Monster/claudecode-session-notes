#!/usr/bin/env python3
"""
Session Notes MCP Server - FastMCP 2.0 Implementation

A Model Context Protocol server for collecting and analyzing ClaudeCode session data,
agent behavior, tool usage patterns, and missing capabilities.

This server provides comprehensive session workbook collection and analysis capabilities
for optimizing AI-assisted development workflows.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("session_notes.server")

# Initialize FastMCP application
app = FastMCP("session-notes", version="0.1.0")


# =============================================================================
# DATA MODELS
# =============================================================================


class SessionInfo(BaseModel):
    """Session metadata information"""

    session_id: str = Field(description="Unique session identifier")
    timestamp: str = Field(description="Session start timestamp (ISO8601)")
    duration: float | None = Field(None, description="Session duration in seconds")
    environment: dict[str, Any] = Field(
        default_factory=dict, description="Environment metadata"
    )
    status: str = Field(default="active", description="Session status")


class AgentExecution(BaseModel):
    """Agent execution information"""

    agent_id: str = Field(description="Unique agent identifier")
    agent_type: str = Field(description="Type of agent")
    timestamp: str = Field(description="Execution timestamp")
    action: str = Field(description="Action performed")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )
    result: dict[str, Any] | None = Field(None, description="Execution result")
    execution_time: float | None = Field(
        None, description="Execution time in milliseconds"
    )


class ToolRequest(BaseModel):
    """Tool usage request information"""

    tool_name: str = Field(description="Name of the tool requested")
    available: bool = Field(description="Whether the tool was available")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    success: bool = Field(description="Whether the tool execution succeeded")
    timestamp: str = Field(description="Request timestamp")


# =============================================================================
# STORAGE UTILITIES
# =============================================================================


def get_session_directory(session_id: str) -> Path:
    """Get the session directory path"""
    return Path(".claude/session-notes") / session_id


def get_agent_directory(session_id: str, agent_id: str) -> Path:
    """Get the agent directory path within a session"""
    return get_session_directory(session_id) / "agents" / agent_id


def ensure_directory(path: Path) -> None:
    """Ensure directory exists, creating if necessary"""
    path.mkdir(parents=True, exist_ok=True)


def save_json_data(file_path: Path, data: Any) -> None:
    """Save data to JSON file with proper formatting"""
    ensure_directory(file_path.parent)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json_data(file_path: Path, default: Any = None) -> Any:
    """Load data from JSON file, returning default if file doesn't exist"""
    if not file_path.exists():
        return default
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return default


# =============================================================================
# FASTMCP 2.0 TOOLS - SESSION MANAGEMENT
# =============================================================================


@app.tool()
def start_session(
    session_id: str | None = None, environment_info: dict[str, Any] | None = None
) -> str:
    """
    Start tracking a new ClaudeCode session.

    Args:
        session_id: Optional session ID (will generate if not provided)
        environment_info: Optional environment metadata

    Returns:
        Started session ID
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    session_dir = get_session_directory(session_id)
    ensure_directory(session_dir)

    # Create session metadata
    session_info = SessionInfo(
        session_id=session_id,
        timestamp=datetime.now(UTC).isoformat(),
        duration=None,
        environment=environment_info or {},
        status="active",
    )

    # Save session metadata
    session_file = session_dir / "session.json"
    save_json_data(session_file, session_info.model_dump())

    logger.info(f"Started session tracking: {session_id}")
    return f"Session {session_id} started successfully"


@app.tool()
def end_session(session_id: str) -> str:
    """
    End session tracking and calculate final metrics.

    Args:
        session_id: Session ID to end

    Returns:
        Session end confirmation
    """
    session_dir = get_session_directory(session_id)
    session_file = session_dir / "session.json"

    if not session_file.exists():
        return f"Session {session_id} not found"

    # Load existing session data
    session_data = load_json_data(session_file, {})

    # Calculate duration if start timestamp exists
    if "timestamp" in session_data:
        start_time = datetime.fromisoformat(session_data["timestamp"])
        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()
        session_data["duration"] = duration

    session_data["status"] = "completed"
    session_data["end_timestamp"] = datetime.now(UTC).isoformat()

    # Save updated session data
    save_json_data(session_file, session_data)

    logger.info(f"Ended session tracking: {session_id}")
    return f"Session {session_id} ended successfully"


# =============================================================================
# FASTMCP 2.0 TOOLS - AGENT LOGGING
# =============================================================================


@app.tool()
def log_agent_execution(
    session_id: str,
    agent_id: str,
    agent_type: str,
    action: str,
    parameters: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    execution_time: float | None = None,
) -> str:
    """
    Log an agent execution within a session.

    Args:
        session_id: Session ID
        agent_id: Unique agent identifier
        agent_type: Type of agent (e.g., "code-reviewer", "task-executor")
        action: Action performed by the agent
        parameters: Optional action parameters
        result: Optional execution result
        execution_time: Optional execution time in milliseconds

    Returns:
        Logging confirmation
    """
    agent_dir = get_agent_directory(session_id, agent_id)
    ensure_directory(agent_dir)

    # Create agent execution record
    execution = AgentExecution(
        agent_id=agent_id,
        agent_type=agent_type,
        timestamp=datetime.now(UTC).isoformat(),
        action=action,
        parameters=parameters or {},
        result=result,
        execution_time=execution_time,
    )

    # Load existing executions
    execution_file = agent_dir / "execution.json"
    executions = load_json_data(execution_file, [])

    # Append new execution
    executions.append(execution.model_dump())

    # Save updated executions
    save_json_data(execution_file, executions)

    logger.info(f"Logged agent execution: {agent_id} in session {session_id}")
    return f"Logged execution for agent {agent_id}: {action}"


@app.tool()
def log_tool_request(
    session_id: str,
    agent_id: str,
    tool_name: str,
    available: bool,
    success: bool,
    parameters: dict[str, Any] | None = None,
) -> str:
    """
    Log a tool request by an agent.

    Args:
        session_id: Session ID
        agent_id: Agent making the request
        tool_name: Name of the requested tool
        available: Whether the tool was available
        success: Whether the tool execution succeeded
        parameters: Optional tool parameters

    Returns:
        Logging confirmation
    """
    agent_dir = get_agent_directory(session_id, agent_id)
    ensure_directory(agent_dir)

    # Create tool request record
    tool_request = ToolRequest(
        tool_name=tool_name,
        available=available,
        parameters=parameters or {},
        success=success,
        timestamp=datetime.now(UTC).isoformat(),
    )

    # Load existing tool requests
    tools_file = agent_dir / "tools.json"
    tool_requests = load_json_data(tools_file, [])

    # Append new request
    tool_requests.append(tool_request.model_dump())

    # Save updated requests
    save_json_data(tools_file, tool_requests)

    logger.info(f"Logged tool request: {tool_name} by agent {agent_id}")
    return (
        f"Logged tool request: {tool_name} (available: {available}, success: {success})"
    )


# =============================================================================
# FASTMCP 2.0 RESOURCES - DATA ACCESS
# =============================================================================


@app.resource("session://{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    """
    Get complete session data including all agent executions.

    Args:
        session_id: Session ID to retrieve

    Returns:
        Complete session data
    """
    session_dir = get_session_directory(session_id)

    if not session_dir.exists():
        return {"error": f"Session {session_id} not found"}

    # Load session metadata
    session_file = session_dir / "session.json"
    session_data = load_json_data(session_file, {})

    # Load agent data
    agents_dir = session_dir / "agents"
    agents_data = {}

    if agents_dir.exists():
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir():
                agent_id = agent_dir.name
                agent_data = {}

                # Load agent executions
                execution_file = agent_dir / "execution.json"
                agent_data["executions"] = load_json_data(execution_file, [])

                # Load tool requests
                tools_file = agent_dir / "tools.json"
                agent_data["tool_requests"] = load_json_data(tools_file, [])

                agents_data[agent_id] = agent_data

    session_data["agents"] = agents_data
    return dict(session_data)


@app.resource("sessions://list")
def list_sessions() -> list[dict[str, Any]]:
    """
    List all tracked sessions.

    Returns:
        List of session summaries
    """
    sessions_root = Path(".claude/session-notes")
    sessions: list[dict[str, Any]] = []

    if not sessions_root.exists():
        return sessions

    for session_dir in sessions_root.iterdir():
        if session_dir.is_dir():
            session_file = session_dir / "session.json"
            session_data = load_json_data(session_file, {})

            if session_data:
                # Add summary information
                session_summary = {
                    "session_id": session_data.get("session_id", session_dir.name),
                    "timestamp": session_data.get("timestamp"),
                    "status": session_data.get("status", "unknown"),
                    "duration": session_data.get("duration"),
                    "agent_count": len(list((session_dir / "agents").glob("*")))
                    if (session_dir / "agents").exists()
                    else 0,
                }
                sessions.append(session_summary)

    # Sort by timestamp (most recent first)
    sessions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return sessions


# =============================================================================
# SERVER STARTUP
# =============================================================================


def main() -> None:
    """Main entry point for the MCP server"""
    logger.info("Starting Session Notes MCP Server with FastMCP 2.0")
    logger.info(
        "Available tools: start_session, end_session, log_agent_execution, log_tool_request"
    )
    logger.info("Available resources: session://{id}, sessions://list")

    # Run the FastMCP server
    app.run()


if __name__ == "__main__":
    main()
