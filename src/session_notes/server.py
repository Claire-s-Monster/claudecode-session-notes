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
import os
import platform
import sys
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
app: FastMCP = FastMCP("session-notes", version="0.1.0")


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


class AgentMetadata(BaseModel):
    """Agent metadata and registration information"""

    agent_id: str = Field(description="Unique agent identifier")
    agent_type: str = Field(description="Type/category of agent")
    timestamp: str = Field(description="Agent registration timestamp")
    purpose: str | None = Field(None, description="Agent's intended purpose or role")
    capabilities: list[str] = Field(
        default_factory=list, description="List of agent capabilities"
    )
    session_id: str = Field(description="Session this agent belongs to")
    status: str = Field(default="active", description="Agent status")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional agent-specific metadata"
    )
    registration_context: dict[str, Any] = Field(
        default_factory=dict, description="Context information at registration time"
    )


# =============================================================================
# ENVIRONMENT COLLECTION UTILITIES
# =============================================================================


def collect_environment_metadata() -> dict[str, Any]:
    """
    Collect comprehensive environment metadata automatically.

    Returns:
        Dictionary containing detailed environment information
    """
    env_data = {
        # System information
        "system": {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.architecture()[0],
            "machine": platform.machine(),
            "processor": platform.processor(),
            "node": platform.node(),
        },
        # Python information
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler(),
            "build": platform.python_build(),
            "executable": sys.executable,
        },
        # Process information
        "process": {
            "pid": os.getpid(),
            "working_directory": str(Path.cwd()),
            "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
        },
        # Environment variables (selected safe ones)
        "environment_vars": {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", os.environ.get("USERPROFILE", "")),
            "SHELL": os.environ.get("SHELL", ""),
            "TERM": os.environ.get("TERM", ""),
            "LANG": os.environ.get("LANG", ""),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        },
        # Collection metadata
        "collection_metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "collector_version": "session-notes-0.1.0",
        },
    }

    return env_data


def merge_environment_metadata(
    provided_env: dict[str, Any] | None, auto_collect: bool = True
) -> dict[str, Any]:
    """
    Merge provided environment data with automatically collected metadata.

    Args:
        provided_env: User provided environment data (takes precedence)
        auto_collect: Whether to automatically collect system metadata

    Returns:
        Merged environment metadata dictionary
    """
    result = {}

    # Start with auto-collected data if enabled
    if auto_collect:
        result.update(collect_environment_metadata())

    # Merge provided environment data (overrides auto-collected)
    if provided_env:
        # Deep merge for nested dictionaries
        for key, value in provided_env.items():
            if (
                isinstance(value, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
                result[key].update(value)
            else:
                result[key] = value

    return result


def calculate_session_metrics(
    session_id: str, session_dir: Path, duration: float | None
) -> dict[str, Any]:
    """
    Calculate comprehensive metrics for a session.

    Args:
        session_id: Session identifier
        session_dir: Path to session directory
        duration: Session duration in seconds

    Returns:
        Dictionary containing calculated session metrics
    """
    metrics: dict[str, Any] = {
        "calculation_timestamp": datetime.now(UTC).isoformat(),
        "session_duration": duration,
    }

    # Count agents and their activities
    agents_dir = session_dir / "agents"
    agent_count = 0
    total_executions = 0
    total_tool_requests = 0
    agent_types = set()

    if agents_dir.exists():
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir():
                agent_count += 1

                # Count executions
                execution_file = agent_dir / "execution.json"
                executions = load_json_data(execution_file, [])
                total_executions += len(executions)

                # Collect agent types
                for execution in executions:
                    if isinstance(execution, dict) and "agent_type" in execution:
                        agent_types.add(execution["agent_type"])

                # Count tool requests
                tools_file = agent_dir / "tools.json"
                tool_requests = load_json_data(tools_file, [])
                total_tool_requests += len(tool_requests)

    metrics.update(
        {
            "agent_count": agent_count,
            "total_executions": total_executions,
            "total_tool_requests": total_tool_requests,
            "unique_agent_types": list(agent_types),
            "agent_type_count": len(agent_types),
        }
    )

    # Calculate rates if duration is available
    if duration and duration > 0:
        metrics.update(
            {
                "executions_per_minute": (total_executions / duration) * 60,
                "tool_requests_per_minute": (total_tool_requests / duration) * 60,
            }
        )

    return metrics


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
# HIGH-LEVEL JSON DATA I/O HANDLERS
# =============================================================================


def read_session_json(session_id: str, filename: str, default: Any = None) -> Any:
    """
    Read JSON data from a session file.

    Args:
        session_id: Session identifier
        filename: JSON filename (e.g., 'session.json')
        default: Default value if file doesn't exist or can't be read

    Returns:
        Loaded JSON data or default value
    """
    session_dir = get_session_directory(session_id)
    file_path = session_dir / filename
    return load_json_data(file_path, default)


def write_session_json(session_id: str, filename: str, data: Any) -> None:
    """
    Write JSON data to a session file.

    Args:
        session_id: Session identifier
        filename: JSON filename (e.g., 'session.json')
        data: Data to write
    """
    session_dir = get_session_directory(session_id)
    file_path = session_dir / filename
    save_json_data(file_path, data)


def read_agent_json(
    session_id: str, agent_id: str, filename: str, default: Any = None
) -> Any:
    """
    Read JSON data from an agent file.

    Args:
        session_id: Session identifier
        agent_id: Agent identifier
        filename: JSON filename (e.g., 'execution.json', 'tools.json')
        default: Default value if file doesn't exist or can't be read

    Returns:
        Loaded JSON data or default value
    """
    agent_dir = get_agent_directory(session_id, agent_id)
    file_path = agent_dir / filename
    return load_json_data(file_path, default)


def write_agent_json(session_id: str, agent_id: str, filename: str, data: Any) -> None:
    """
    Write JSON data to an agent file.

    Args:
        session_id: Session identifier
        agent_id: Agent identifier
        filename: JSON filename (e.g., 'execution.json', 'tools.json')
        data: Data to write
    """
    agent_dir = get_agent_directory(session_id, agent_id)
    file_path = agent_dir / filename
    save_json_data(file_path, data)


def session_exists(session_id: str) -> bool:
    """
    Check if a session exists by verifying the session.json file.

    Args:
        session_id: Session identifier

    Returns:
        True if session exists (has session.json file), False otherwise
    """
    session_file = get_session_directory(session_id) / "session.json"
    return session_file.exists() and session_file.is_file()


def agent_exists(session_id: str, agent_id: str) -> bool:
    """
    Check if an agent directory exists within a session.

    Args:
        session_id: Session identifier
        agent_id: Agent identifier

    Returns:
        True if agent directory exists, False otherwise
    """
    agent_dir = get_agent_directory(session_id, agent_id)
    return agent_dir.exists() and agent_dir.is_dir()


def list_session_agents(session_id: str) -> list[str]:
    """
    List all agent IDs within a session.

    Args:
        session_id: Session identifier

    Returns:
        List of agent IDs
    """
    session_dir = get_session_directory(session_id)
    agents_dir = session_dir / "agents"

    if not agents_dir.exists():
        return []

    return [d.name for d in agents_dir.iterdir() if d.is_dir()]


# =============================================================================
# INTERNAL BUSINESS LOGIC FUNCTIONS (Direct callable - for testing)
# =============================================================================


def _start_session_impl(
    session_id: str | None = None,
    environment_info: dict[str, Any] | None = None,
    auto_collect_environment: bool = True,
) -> str:
    """
    Internal implementation for starting a session.
    This function contains the actual business logic and is directly callable.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    session_dir = get_session_directory(session_id)
    ensure_directory(session_dir)

    # Merge environment metadata (auto-collected + provided)
    environment_data = merge_environment_metadata(
        environment_info, auto_collect_environment
    )

    # Create session metadata
    session_info = SessionInfo(
        session_id=session_id,
        timestamp=datetime.now(UTC).isoformat(),
        duration=None,
        environment=environment_data,
        status="active",
    )

    # Save session metadata
    session_file = session_dir / "session.json"
    save_json_data(session_file, session_info.model_dump())

    logger.info(f"Started session tracking: {session_id} with comprehensive metadata")
    return f"Session {session_id} started successfully with comprehensive metadata collection"


def _end_session_impl(
    session_id: str,
    outcome: str | None = None,
    outcome_metrics: dict[str, Any] | None = None,
) -> str:
    """
    Internal implementation for ending a session.
    This function contains the actual business logic and is directly callable.
    """
    session_dir = get_session_directory(session_id)
    session_file = session_dir / "session.json"

    if not session_file.exists():
        return f"Session {session_id} not found"

    # Load existing session data
    session_data = load_json_data(session_file, {})
    end_time = datetime.now(UTC)

    # Calculate duration if start timestamp exists
    duration = None
    if "timestamp" in session_data:
        start_time = datetime.fromisoformat(session_data["timestamp"])
        duration = (end_time - start_time).total_seconds()
        session_data["duration"] = duration

    # Add end timestamp and status
    session_data["status"] = "completed"
    session_data["end_timestamp"] = end_time.isoformat()

    # Add outcome information
    if outcome:
        session_data["outcome"] = outcome
    if outcome_metrics:
        session_data["outcome_metrics"] = outcome_metrics

    # Calculate comprehensive session metrics
    session_metrics = calculate_session_metrics(session_id, session_dir, duration)
    session_data["session_metrics"] = session_metrics

    # Save updated session data
    save_json_data(session_file, session_data)

    # Create summary for return message
    metrics_summary = f"Duration: {duration:.1f}s" if duration else "Duration: unknown"
    if session_metrics:
        metrics_summary += f", Agents: {session_metrics.get('agent_count', 0)}"
        metrics_summary += f", Executions: {session_metrics.get('total_executions', 0)}"
        metrics_summary += (
            f", Tool Requests: {session_metrics.get('total_tool_requests', 0)}"
        )

    logger.info(f"Ended session tracking: {session_id} - {metrics_summary}")
    return f"Session {session_id} ended successfully - {metrics_summary}"


def _update_session_metadata_impl(
    session_id: str, metadata_updates: dict[str, Any], merge_environment: bool = True
) -> str:
    """
    Internal implementation for updating session metadata.
    This function contains the actual business logic and is directly callable.
    """
    session_dir = get_session_directory(session_id)
    session_file = session_dir / "session.json"

    if not session_file.exists():
        return f"Session {session_id} not found"

    # Load existing session data
    session_data = load_json_data(session_file, {})

    # Update metadata fields
    for key, value in metadata_updates.items():
        if key == "environment" and merge_environment and key in session_data:
            # Merge environment data
            if isinstance(session_data[key], dict) and isinstance(value, dict):
                session_data[key].update(value)
            else:
                session_data[key] = value
        else:
            # Direct update for other fields
            session_data[key] = value

    # Add update timestamp
    session_data["last_updated"] = datetime.now(UTC).isoformat()

    # Save updated session data
    save_json_data(session_file, session_data)

    logger.info(f"Updated session metadata: {session_id}")
    return f"Session {session_id} metadata updated successfully"


def _get_session_status_impl(session_id: str) -> dict[str, Any]:
    """
    Internal implementation for getting session status.
    This function contains the actual business logic and is directly callable.
    """
    session_dir = get_session_directory(session_id)
    session_file = session_dir / "session.json"

    if not session_file.exists():
        return {"error": f"Session {session_id} not found"}

    # Load session data
    session_data = load_json_data(session_file, {})

    # Calculate current metrics if session is active
    current_metrics = {}
    if session_data.get("status") == "active":
        current_duration = None
        if "timestamp" in session_data:
            start_time = datetime.fromisoformat(session_data["timestamp"])
            current_duration = (datetime.now(UTC) - start_time).total_seconds()

        current_metrics = calculate_session_metrics(
            session_id, session_dir, current_duration
        )

    # Create status summary
    status_info = {
        "session_id": session_id,
        "status": session_data.get("status", "unknown"),
        "start_timestamp": session_data.get("timestamp"),
        "current_duration": current_metrics.get("session_duration"),
        "agent_count": current_metrics.get("agent_count", 0),
        "total_executions": current_metrics.get("total_executions", 0),
        "total_tool_requests": current_metrics.get("total_tool_requests", 0),
        "environment_collected": bool(session_data.get("environment")),
    }

    return status_info


def _log_agent_execution_impl(
    session_id: str,
    agent_id: str,
    agent_type: str,
    action: str,
    parameters: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    execution_time: float | None = None,
    auto_register: bool = True,
) -> str:
    """
    Internal implementation for logging agent execution.
    This function contains the actual business logic and is directly callable.
    """
    # Auto-register agent if it doesn't exist and auto_register is enabled
    if auto_register and not agent_exists(session_id, agent_id):
        logger.info(f"Auto-registering agent {agent_id} of type {agent_type}")
        _register_agent_impl(
            session_id=session_id,
            agent_id=agent_id,
            agent_type=agent_type,
            purpose=f"Auto-registered during execution logging for action: {action}",
            registration_context={
                "auto_registered": True,
                "first_action": action,
                "registration_trigger": "log_agent_execution",
            },
        )

    # Create agent directory if it doesn't exist
    agent_dir = get_agent_directory(session_id, agent_id)
    ensure_directory(agent_dir)

    # Create execution entry
    execution = AgentExecution(
        agent_id=agent_id,
        agent_type=agent_type,
        timestamp=datetime.now(UTC).isoformat(),
        action=action,
        parameters=parameters or {},
        result=result,
        execution_time=execution_time,
    )

    # Load existing execution log
    execution_file = agent_dir / "execution.json"
    executions = load_json_data(execution_file, [])

    # Add new execution
    executions.append(execution.model_dump())

    # Save updated execution log
    save_json_data(execution_file, executions)

    logger.info(f"Logged agent execution: {agent_id} - {action}")
    return f"Logged execution for agent {agent_id}: {action}"


def _log_tool_request_impl(
    session_id: str,
    agent_id: str,
    tool_name: str,
    available: bool,
    parameters: dict[str, Any] | None = None,
    success: bool | None = None,
) -> str:
    """
    Internal implementation for logging tool request.
    This function contains the actual business logic and is directly callable.
    """
    # Create agent directory if it doesn't exist
    agent_dir = get_agent_directory(session_id, agent_id)
    ensure_directory(agent_dir)

    # Create tool request entry
    tool_request = ToolRequest(
        tool_name=tool_name,
        available=available,
        parameters=parameters or {},
        success=success if success is not None else available,
        timestamp=datetime.now(UTC).isoformat(),
    )

    # Load existing tool request log
    tools_file = agent_dir / "tools.json"
    tools = load_json_data(tools_file, [])

    # Add new tool request
    tools.append(tool_request.model_dump())

    # Save updated tool request log
    save_json_data(tools_file, tools)

    logger.info(
        f"Logged tool request: {agent_id} - {tool_name} (available: {available})"
    )
    return f"Logged tool request for agent {agent_id}: {tool_name}"


def _register_agent_impl(
    session_id: str,
    agent_id: str | None = None,
    agent_type: str = "unknown",
    purpose: str | None = None,
    capabilities: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    registration_context: dict[str, Any] | None = None,
    auto_register_on_execution: bool = True,
) -> str:
    """
    Internal implementation for registering an agent.
    This function contains the actual business logic and is directly callable.
    """
    # Validate session exists (check session.json file specifically)
    session_file = get_session_directory(session_id) / "session.json"
    if not session_file.exists():
        return f"Session {session_id} not found"

    # Generate agent ID if not provided
    if agent_id is None:
        agent_id = str(uuid.uuid4())

    # Create agent directory if it doesn't exist
    agent_dir = get_agent_directory(session_id, agent_id)
    ensure_directory(agent_dir)

    # Create agent metadata
    agent_metadata = AgentMetadata(
        agent_id=agent_id,
        agent_type=agent_type,
        timestamp=datetime.now(UTC).isoformat(),
        purpose=purpose,
        capabilities=capabilities or [],
        session_id=session_id,
        status="active",
        metadata=metadata or {},
        registration_context=registration_context or {},
    )

    # Save agent metadata
    metadata_file = agent_dir / "metadata.json"
    save_json_data(metadata_file, agent_metadata.model_dump())

    # Initialize empty execution and tools logs if they don't exist
    execution_file = agent_dir / "execution.json"
    if not execution_file.exists():
        save_json_data(execution_file, [])

    tools_file = agent_dir / "tools.json"
    if not tools_file.exists():
        save_json_data(tools_file, [])

    logger.info(f"Registered agent: {agent_id} ({agent_type}) in session {session_id}")
    return f"Agent {agent_id} registered successfully in session {session_id}"


def _get_agent_metadata_impl(session_id: str, agent_id: str) -> dict[str, Any]:
    """
    Internal implementation for getting agent metadata.
    This function contains the actual business logic and is directly callable.
    """
    # Check if session exists by verifying session.json file
    session_file = get_session_directory(session_id) / "session.json"
    if not session_file.exists():
        return {"error": f"Session {session_id} not found"}

    if not agent_exists(session_id, agent_id):
        return {"error": f"Agent {agent_id} not found in session {session_id}"}

    # Load agent metadata
    agent_dir = get_agent_directory(session_id, agent_id)
    metadata_file = agent_dir / "metadata.json"

    agent_metadata = load_json_data(metadata_file, {})
    if not agent_metadata:
        return {"error": f"Agent {agent_id} metadata not found"}

    # Add current statistics
    execution_count = len(load_json_data(agent_dir / "execution.json", []))
    tool_request_count = len(load_json_data(agent_dir / "tools.json", []))

    agent_metadata["statistics"] = {
        "execution_count": execution_count,
        "tool_request_count": tool_request_count,
        "last_activity": get_last_agent_activity(session_id, agent_id),
    }

    return agent_metadata  # type: ignore[no-any-return]


def get_last_agent_activity(session_id: str, agent_id: str) -> str | None:
    """
    Get the timestamp of the last activity for an agent.

    Args:
        session_id: Session identifier
        agent_id: Agent identifier

    Returns:
        ISO timestamp of last activity or None if no activity found
    """
    if not agent_exists(session_id, agent_id):
        return None

    agent_dir = get_agent_directory(session_id, agent_id)
    last_timestamp = None

    # Check execution log
    executions = load_json_data(agent_dir / "execution.json", [])
    if executions:
        execution_timestamps = [
            exec_data.get("timestamp")
            for exec_data in executions
            if isinstance(exec_data, dict) and "timestamp" in exec_data
        ]
        if execution_timestamps:
            last_timestamp = max(execution_timestamps)  # type: ignore[type-var]

    # Check tool requests log
    tools = load_json_data(agent_dir / "tools.json", [])
    if tools:
        tool_timestamps = [
            tool_data.get("timestamp")
            for tool_data in tools
            if isinstance(tool_data, dict) and "timestamp" in tool_data
        ]
        if tool_timestamps:
            tool_last = max(tool_timestamps)  # type: ignore[type-var]
            if last_timestamp is None or (tool_last and tool_last > last_timestamp):
                last_timestamp = tool_last

    return last_timestamp


def _get_session_impl(session_id: str) -> dict[str, Any]:
    """
    Internal implementation for getting session data.
    This function contains the actual business logic and is directly callable.
    """
    session_dir = get_session_directory(session_id)
    session_file = session_dir / "session.json"

    if not session_file.exists():
        return {"error": f"Session {session_id} not found"}

    # Load session data
    session_data: dict[str, Any] = load_json_data(session_file, {})

    # Add agent data
    agents_dir = session_dir / "agents"
    session_data["agents"] = {}

    if agents_dir.exists():
        for agent_path in agents_dir.iterdir():
            if agent_path.is_dir():
                agent_id = agent_path.name
                agent_data = {
                    "metadata": load_json_data(agent_path / "metadata.json", {}),
                    "executions": load_json_data(agent_path / "execution.json", []),
                    "tool_requests": load_json_data(agent_path / "tools.json", []),
                }
                session_data["agents"][agent_id] = agent_data

    return session_data


def _list_sessions_impl() -> list[dict[str, Any]]:
    """
    Internal implementation for listing sessions.
    This function contains the actual business logic and is directly callable.
    """
    sessions_dir = Path(".claude/session-notes")

    if not sessions_dir.exists():
        return []

    sessions = []
    for session_path in sessions_dir.iterdir():
        if session_path.is_dir():
            session_file = session_path / "session.json"
            if session_file.exists():
                session_data = load_json_data(session_file, {})

                # Create session summary
                summary = {
                    "session_id": session_data.get("session_id", session_path.name),
                    "timestamp": session_data.get("timestamp"),
                    "status": session_data.get("status", "unknown"),
                    "duration": session_data.get("duration"),
                }

                # Add agent count
                agents_dir = session_path / "agents"
                if agents_dir.exists():
                    summary["agent_count"] = len(
                        [d for d in agents_dir.iterdir() if d.is_dir()]
                    )
                else:
                    summary["agent_count"] = 0

                sessions.append(summary)

    return sessions


# =============================================================================
# PUBLIC API FOR TESTING (Export internal implementations as callable functions)
# =============================================================================

# Test environment detection
TESTING_MODE = (
    "pytest" in sys.modules or os.getenv("CLAUDECODE") == "0" or "test" in sys.argv[0]
    if sys.argv
    else False
)

# Note: Function definitions below are conditionally created based on TESTING_MODE
# In test mode, regular callable functions are created
# In normal mode, FastMCP tool decorators wrap the functions

# Note: Testing mode overrides are placed after FastMCP function definitions
# to ensure they take precedence over the decorated functions


# =============================================================================
# FASTMCP 2.0 TOOLS - SESSION MANAGEMENT
# =============================================================================

# Always define FastMCP tools (for both test and non-test mode)
# This ensures that FastMCP app.get_tools() and app.get_resources() work correctly in tests


@app.tool()
def start_session(
    session_id: str | None = None,
    environment_info: dict[str, Any] | None = None,
    auto_collect_environment: bool = True,
) -> str:
    """
    Start tracking a new ClaudeCode session with comprehensive metadata collection.

    Args:
        session_id: Optional session ID (will generate if not provided)
        environment_info: Optional environment metadata (merged with auto-collected data)
        auto_collect_environment: Whether to automatically collect system environment details

    Returns:
        Started session ID
    """
    return _start_session_impl(session_id, environment_info, auto_collect_environment)


@app.tool()
def end_session(
    session_id: str,
    outcome: str | None = None,
    outcome_metrics: dict[str, Any] | None = None,
) -> str:
    """
    End session tracking and calculate comprehensive final metrics.

    Args:
        session_id: Session ID to end
        outcome: Optional session outcome description (e.g., "completed", "interrupted", "error")
        outcome_metrics: Optional custom metrics about the session outcome

    Returns:
        Session end confirmation with metrics summary
    """
    return _end_session_impl(session_id, outcome, outcome_metrics)


@app.tool()
def update_session_metadata(
    session_id: str,
    metadata_updates: dict[str, Any],
    merge_environment: bool = True,
) -> str:
    """
    Update session metadata during the session lifecycle.

    Args:
        session_id: Session ID to update
        metadata_updates: Dictionary of metadata fields to update
        merge_environment: Whether to merge environment updates (vs replace)

    Returns:
        Update confirmation
    """
    return _update_session_metadata_impl(
        session_id, metadata_updates, merge_environment
    )


@app.tool()
def get_session_status(session_id: str) -> dict[str, Any]:
    """
    Get current session status and basic metrics.

    Args:
        session_id: Session ID to check

    Returns:
        Session status information
    """
    return _get_session_status_impl(session_id)


# =============================================================================
# FASTMCP 2.0 TOOLS - AGENT LOGGING
# =============================================================================


@app.tool()
def register_agent(
    session_id: str,
    agent_id: str | None = None,
    agent_type: str = "unknown",
    purpose: str | None = None,
    capabilities: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    registration_context: dict[str, Any] | None = None,
) -> str:
    """
    Register an agent within a session with comprehensive metadata.

    Args:
        session_id: Session ID where the agent will be registered
        agent_id: Optional unique agent identifier (will generate if not provided)
        agent_type: Type/category of agent (e.g., "code-reviewer", "task-executor")
        purpose: Optional description of the agent's intended purpose or role
        capabilities: Optional list of agent capabilities or skills
        metadata: Optional additional agent-specific metadata
        registration_context: Optional context information at registration time

    Returns:
        Registration confirmation with agent ID
    """
    return _register_agent_impl(
        session_id,
        agent_id,
        agent_type,
        purpose,
        capabilities,
        metadata,
        registration_context,
    )


@app.tool()
def get_agent_metadata(session_id: str, agent_id: str) -> dict[str, Any]:
    """
    Get comprehensive metadata for a specific agent including current statistics.

    Args:
        session_id: Session ID containing the agent
        agent_id: Agent identifier

    Returns:
        Agent metadata with current statistics
    """
    return _get_agent_metadata_impl(session_id, agent_id)


@app.tool()
def log_agent_execution(
    session_id: str,
    agent_id: str,
    agent_type: str,
    action: str,
    parameters: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    execution_time: float | None = None,
    auto_register: bool = True,
) -> str:
    """
    Log an agent execution within a session with optional auto-registration.

    Args:
        session_id: Session ID
        agent_id: Unique agent identifier
        agent_type: Type of agent (e.g., "code-reviewer", "task-executor")
        action: Action performed by the agent
        parameters: Optional action parameters
        result: Optional execution result
        execution_time: Optional execution time in milliseconds
        auto_register: Whether to automatically register the agent if it doesn't exist

    Returns:
        Logging confirmation
    """
    return _log_agent_execution_impl(
        session_id,
        agent_id,
        agent_type,
        action,
        parameters,
        result,
        execution_time,
        auto_register,
    )


@app.tool()
def log_tool_request(
    session_id: str,
    agent_id: str,
    tool_name: str,
    available: bool,
    parameters: dict[str, Any] | None = None,
    success: bool | None = None,
) -> str:
    """
    Log a tool request by an agent.

    Args:
        session_id: Session ID
        agent_id: Agent making the request
        tool_name: Name of the requested tool
        available: Whether the tool was available
        parameters: Optional tool parameters
        success: Whether the tool execution succeeded (defaults to available)

    Returns:
        Logging confirmation
    """
    return _log_tool_request_impl(
        session_id, agent_id, tool_name, available, parameters, success
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
    return _get_session_impl(session_id)


@app.resource("sessions://list")
def list_sessions() -> list[dict[str, Any]]:
    """
    List all tracked sessions.

    Returns:
        List of session summaries
    """
    return _list_sessions_impl()


@app.resource("agent://{session_id}/{agent_id}")
def get_agent_data(session_id: str, agent_id: str) -> dict[str, Any]:
    """
    Get complete agent data including metadata, executions, and tool requests.

    Args:
        session_id: Session ID containing the agent
        agent_id: Agent identifier

    Returns:
        Complete agent data
    """
    return _get_agent_metadata_impl(session_id, agent_id)


@app.resource("agents://{session_id}")
def list_session_agents_resource(session_id: str) -> list[str]:
    """
    List all agent IDs within a session.

    Args:
        session_id: Session identifier

    Returns:
        List of agent IDs
    """
    return list_session_agents(session_id)


# =============================================================================
# TESTING MODE OVERRIDES
# =============================================================================

# For testing: Override FastMCP-wrapped functions with direct callable implementations
# This allows tests to call functions directly while maintaining FastMCP registration
if TESTING_MODE:
    # Tool functions (override FastMCP-wrapped functions for direct testing)
    start_session = _start_session_impl  # type: ignore[assignment]
    end_session = _end_session_impl  # type: ignore[assignment]
    update_session_metadata = _update_session_metadata_impl  # type: ignore[assignment]
    get_session_status = _get_session_status_impl  # type: ignore[assignment]
    register_agent = _register_agent_impl  # type: ignore[assignment]
    get_agent_metadata = _get_agent_metadata_impl  # type: ignore[assignment]
    log_agent_execution = _log_agent_execution_impl  # type: ignore[assignment]
    log_tool_request = _log_tool_request_impl  # type: ignore[assignment]

    # Resource functions (override FastMCP-wrapped functions for direct testing)
    get_session = _get_session_impl  # type: ignore[assignment]
    list_sessions = _list_sessions_impl  # type: ignore[assignment]


# =============================================================================
# SERVER STARTUP
# =============================================================================


def main() -> None:
    """Main entry point for the MCP server"""
    logger.info("Starting Session Notes MCP Server with FastMCP 2.0")
    logger.info(
        "Available tools: start_session, end_session, update_session_metadata, "
        "get_session_status, register_agent, get_agent_metadata, "
        "log_agent_execution, log_tool_request"
    )
    logger.info(
        "Available resources: session://{id}, sessions://list, "
        "agent://{session_id}/{agent_id}, agents://{session_id}"
    )

    # Run the FastMCP server
    app.run()


if __name__ == "__main__":
    main()
