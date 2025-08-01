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


class AgentInteraction(BaseModel):
    """
    Detailed agent interaction information for enhanced behavioral tracking.

    This model captures rich interaction data including decision-making processes,
    communication patterns, and contextual information beyond basic execution logging.
    """

    interaction_id: str = Field(description="Unique interaction identifier")
    agent_id: str = Field(description="Unique agent identifier")
    agent_type: str = Field(description="Type of agent")
    timestamp: str = Field(description="Interaction timestamp (ISO8601)")

    # Core interaction data (similar to AgentExecution but more comprehensive)
    action: str = Field(description="Primary action or behavior performed")
    interaction_type: str = Field(
        description="Type of interaction (e.g., 'decision', 'communication', 'analysis', 'workflow')"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Action parameters and input data"
    )
    result: dict[str, Any] | None = Field(
        None, description="Interaction result and output data"
    )
    execution_time: float | None = Field(
        None, description="Execution time in milliseconds"
    )

    # Enhanced contextual information
    context: dict[str, Any] = Field(
        default_factory=dict, description="Context that triggered this interaction"
    )
    decision_context: dict[str, Any] | None = Field(
        None,
        description="Decision-making context: alternatives considered, reasoning, criteria",
    )
    communication_data: dict[str, Any] | None = Field(
        None, description="Communication patterns and data exchange information"
    )

    # Relationship and workflow information
    parent_interaction_id: str | None = Field(
        None, description="Parent interaction ID for hierarchical interactions"
    )
    related_execution_ids: list[str] = Field(
        default_factory=list, description="Related execution IDs from execution.json"
    )
    workflow_stage: str | None = Field(
        None, description="Stage in a larger workflow or process"
    )

    # Outcome and assessment
    success: bool = Field(
        default=True, description="Whether the interaction was successful"
    )
    outcome_assessment: dict[str, Any] | None = Field(
        None, description="Assessment of interaction outcomes and effectiveness"
    )

    # Additional metadata
    tags: list[str] = Field(
        default_factory=list, description="Categorization tags for this interaction"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional interaction-specific metadata"
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


def _log_agent_interaction_impl(
    session_id: str,
    agent_id: str,
    agent_type: str,
    action: str,
    interaction_type: str = "general",
    parameters: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    execution_time: float | None = None,
    context: dict[str, Any] | None = None,
    decision_context: dict[str, Any] | None = None,
    communication_data: dict[str, Any] | None = None,
    parent_interaction_id: str | None = None,
    related_execution_ids: list[str] | None = None,
    workflow_stage: str | None = None,
    success: bool = True,
    outcome_assessment: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    interaction_id: str | None = None,
    auto_register: bool = True,
) -> str:
    """
    Internal implementation for logging detailed agent interactions.
    This function contains the actual business logic and is directly callable.
    """
    # Auto-register agent if it doesn't exist and auto_register is enabled
    if auto_register and not agent_exists(session_id, agent_id):
        logger.info(f"Auto-registering agent {agent_id} of type {agent_type}")
        _register_agent_impl(
            session_id=session_id,
            agent_id=agent_id,
            agent_type=agent_type,
            purpose=f"Auto-registered during interaction logging for action: {action}",
            registration_context={
                "auto_registered": True,
                "first_action": action,
                "registration_trigger": "log_agent_interaction",
            },
        )

    # Create agent directory if it doesn't exist
    agent_dir = get_agent_directory(session_id, agent_id)
    ensure_directory(agent_dir)

    # Generate interaction ID if not provided
    if interaction_id is None:
        interaction_id = str(uuid.uuid4())

    # Create interaction entry
    interaction = AgentInteraction(
        interaction_id=interaction_id,
        agent_id=agent_id,
        agent_type=agent_type,
        timestamp=datetime.now(UTC).isoformat(),
        action=action,
        interaction_type=interaction_type,
        parameters=parameters or {},
        result=result,
        execution_time=execution_time,
        context=context or {},
        decision_context=decision_context,
        communication_data=communication_data,
        parent_interaction_id=parent_interaction_id,
        related_execution_ids=related_execution_ids or [],
        workflow_stage=workflow_stage,
        success=success,
        outcome_assessment=outcome_assessment,
        tags=tags or [],
        metadata=metadata or {},
    )

    # Load existing interaction log
    interactions_file = agent_dir / "interactions.json"
    interactions = load_json_data(interactions_file, [])

    # Add new interaction
    interactions.append(interaction.model_dump())

    # Save updated interaction log
    save_json_data(interactions_file, interactions)

    logger.info(
        f"Logged agent interaction: {agent_id} - {action} ({interaction_type}) [ID: {interaction_id}]"
    )
    return f"Logged interaction for agent {agent_id}: {action} (ID: {interaction_id})"


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

    # Initialize empty execution, tools, and interactions logs if they don't exist
    execution_file = agent_dir / "execution.json"
    if not execution_file.exists():
        save_json_data(execution_file, [])

    tools_file = agent_dir / "tools.json"
    if not tools_file.exists():
        save_json_data(tools_file, [])

    interactions_file = agent_dir / "interactions.json"
    if not interactions_file.exists():
        save_json_data(interactions_file, [])

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
    interaction_stats = get_agent_interaction_statistics(session_id, agent_id)

    agent_metadata["statistics"] = {
        "execution_count": execution_count,
        "tool_request_count": tool_request_count,
        "last_activity": get_last_agent_activity(session_id, agent_id),
        "interactions": interaction_stats,
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

    # Check interactions log
    interactions = load_json_data(agent_dir / "interactions.json", [])
    if interactions:
        interaction_timestamps = [
            interaction_data.get("timestamp")
            for interaction_data in interactions
            if isinstance(interaction_data, dict) and "timestamp" in interaction_data
        ]
        if interaction_timestamps:
            interaction_last = max(interaction_timestamps)  # type: ignore[type-var]
            if last_timestamp is None or (
                interaction_last and interaction_last > last_timestamp
            ):
                last_timestamp = interaction_last

    return last_timestamp


def get_agent_interaction_statistics(session_id: str, agent_id: str) -> dict[str, Any]:
    """
    Get comprehensive interaction statistics for an agent.

    Args:
        session_id: Session identifier
        agent_id: Agent identifier

    Returns:
        Dictionary containing interaction statistics
    """
    if not agent_exists(session_id, agent_id):
        return {}

    agent_dir = get_agent_directory(session_id, agent_id)
    interactions = load_json_data(agent_dir / "interactions.json", [])

    if not interactions:
        return {
            "total_interactions": 0,
            "interaction_types": {},
            "success_rate": 0.0,
            "avg_execution_time": None,
            "workflow_stages": [],
            "communication_count": 0,
            "decision_count": 0,
        }

    # Basic counts
    total_interactions = len(interactions)
    successful_interactions = sum(
        1 for i in interactions if isinstance(i, dict) and i.get("success", True)
    )
    success_rate = (
        successful_interactions / total_interactions if total_interactions > 0 else 0.0
    )

    # Interaction type analysis
    interaction_types: dict[str, int] = {}
    for interaction in interactions:
        if isinstance(interaction, dict):
            itype = interaction.get("interaction_type", "unknown")
            interaction_types[itype] = interaction_types.get(itype, 0) + 1

    # Execution time analysis
    execution_times: list[float] = []
    for i in interactions:
        if isinstance(i, dict) and i.get("execution_time") is not None:
            exec_time = i.get("execution_time")
            if isinstance(exec_time, (int, float)):
                execution_times.append(float(exec_time))
    avg_execution_time = (
        sum(execution_times) / len(execution_times) if execution_times else None
    )

    # Workflow and communication analysis
    workflow_stages = list(
        set(
            i.get("workflow_stage")
            for i in interactions
            if isinstance(i, dict) and i.get("workflow_stage")
        )
    )

    communication_count = sum(
        1
        for i in interactions
        if isinstance(i, dict) and i.get("communication_data") is not None
    )

    decision_count = sum(
        1
        for i in interactions
        if isinstance(i, dict) and i.get("decision_context") is not None
    )

    return {
        "total_interactions": total_interactions,
        "interaction_types": interaction_types,
        "success_rate": success_rate,
        "avg_execution_time": avg_execution_time,
        "workflow_stages": workflow_stages,
        "communication_count": communication_count,
        "decision_count": decision_count,
    }


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
                    "interactions": load_json_data(
                        agent_path / "interactions.json", []
                    ),
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


@app.tool()
def log_agent_interaction(
    session_id: str,
    agent_id: str,
    agent_type: str,
    action: str,
    interaction_type: str = "general",
    parameters: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    execution_time: float | None = None,
    context: dict[str, Any] | None = None,
    decision_context: dict[str, Any] | None = None,
    communication_data: dict[str, Any] | None = None,
    parent_interaction_id: str | None = None,
    related_execution_ids: list[str] | None = None,
    workflow_stage: str | None = None,
    success: bool = True,
    outcome_assessment: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    interaction_id: str | None = None,
    auto_register: bool = True,
) -> str:
    """
    Log detailed agent interactions with enhanced behavioral tracking.

    This tool captures rich interaction data including decision-making processes,
    communication patterns, and contextual information beyond basic execution logging.

    Args:
        session_id: Session ID
        agent_id: Unique agent identifier
        agent_type: Type of agent (e.g., "code-reviewer", "task-executor")
        action: Primary action or behavior performed
        interaction_type: Type of interaction (e.g., "decision", "communication", "analysis", "workflow")
        parameters: Optional action parameters and input data
        result: Optional interaction result and output data
        execution_time: Optional execution time in milliseconds
        context: Optional context that triggered this interaction
        decision_context: Optional decision-making context (alternatives, reasoning, criteria)
        communication_data: Optional communication patterns and data exchange information
        parent_interaction_id: Optional parent interaction ID for hierarchical interactions
        related_execution_ids: Optional list of related execution IDs from execution.json
        workflow_stage: Optional stage in a larger workflow or process
        success: Whether the interaction was successful (default: True)
        outcome_assessment: Optional assessment of interaction outcomes and effectiveness
        tags: Optional categorization tags for this interaction
        metadata: Optional additional interaction-specific metadata
        interaction_id: Optional unique interaction identifier (will generate if not provided)
        auto_register: Whether to automatically register the agent if it doesn't exist

    Returns:
        Logging confirmation with interaction ID
    """
    return _log_agent_interaction_impl(
        session_id=session_id,
        agent_id=agent_id,
        agent_type=agent_type,
        action=action,
        interaction_type=interaction_type,
        parameters=parameters,
        result=result,
        execution_time=execution_time,
        context=context,
        decision_context=decision_context,
        communication_data=communication_data,
        parent_interaction_id=parent_interaction_id,
        related_execution_ids=related_execution_ids,
        workflow_stage=workflow_stage,
        success=success,
        outcome_assessment=outcome_assessment,
        tags=tags,
        metadata=metadata,
        interaction_id=interaction_id,
        auto_register=auto_register,
    )


# =============================================================================
# INTERNAL CLI DATA QUERY IMPLEMENTATIONS
# =============================================================================


def _list_sessions_cli_impl(
    status_filter: str | None = None,
    sort_by: str = "timestamp",
    reverse: bool = True,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Internal implementation for CLI-friendly session listing with filtering and sorting.
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

                # Apply status filter if specified
                if status_filter and session_data.get("status") != status_filter:
                    continue

                # Create CLI-friendly summary
                summary = {
                    "session_id": session_data.get("session_id", session_path.name),
                    "timestamp": session_data.get("timestamp"),
                    "status": session_data.get("status", "unknown"),
                    "duration": session_data.get("duration"),
                    "end_timestamp": session_data.get("end_timestamp"),
                }

                # Add comprehensive agent information
                agents_dir = session_path / "agents"
                agent_count = 0
                agent_types = set()
                total_executions = 0
                total_tool_requests = 0
                total_interactions = 0

                if agents_dir.exists():
                    for agent_dir in agents_dir.iterdir():
                        if agent_dir.is_dir():
                            agent_count += 1

                            # Load agent metadata for type information
                            metadata = load_json_data(agent_dir / "metadata.json", {})
                            if metadata.get("agent_type"):
                                agent_types.add(metadata["agent_type"])

                            # Count activities
                            executions = load_json_data(
                                agent_dir / "execution.json", []
                            )
                            total_executions += len(executions)

                            tools = load_json_data(agent_dir / "tools.json", [])
                            total_tool_requests += len(tools)

                            interactions = load_json_data(
                                agent_dir / "interactions.json", []
                            )
                            total_interactions += len(interactions)

                summary.update(
                    {
                        "agent_count": agent_count,
                        "agent_types": list(agent_types),
                        "total_executions": total_executions,
                        "total_tool_requests": total_tool_requests,
                        "total_interactions": total_interactions,
                    }
                )

                # Add session metrics if available
                if "session_metrics" in session_data:
                    metrics = session_data["session_metrics"]
                    summary["metrics"] = {
                        "executions_per_minute": metrics.get("executions_per_minute"),
                        "tool_requests_per_minute": metrics.get(
                            "tool_requests_per_minute"
                        ),
                        "unique_agent_types": metrics.get("unique_agent_types", []),
                    }

                sessions.append(summary)

    # Sort sessions
    valid_sort_keys = [
        "timestamp",
        "status",
        "duration",
        "agent_count",
        "total_executions",
    ]
    if sort_by not in valid_sort_keys:
        sort_by = "timestamp"

    # Handle None values in sorting
    def sort_key(session):
        value = session.get(sort_by)
        if value is None:
            return "" if isinstance(session.get("session_id"), str) else 0
        return value

    sessions.sort(key=sort_key, reverse=reverse)

    # Apply limit if specified
    if limit and limit > 0:
        sessions = sessions[:limit]

    return sessions


def _get_session_details_impl(
    session_id: str, include_raw_data: bool = False
) -> dict[str, Any]:
    """
    Internal implementation for CLI-friendly detailed session retrieval.
    """
    session_dir = get_session_directory(session_id)
    session_file = session_dir / "session.json"

    if not session_file.exists():
        return {"error": f"Session {session_id} not found"}

    # Load session data
    session_data: dict[str, Any] = load_json_data(session_file, {})

    # Build comprehensive session details
    details = {
        "session_id": session_data.get("session_id", session_id),
        "timestamp": session_data.get("timestamp"),
        "end_timestamp": session_data.get("end_timestamp"),
        "status": session_data.get("status", "unknown"),
        "duration": session_data.get("duration"),
        "outcome": session_data.get("outcome"),
        "outcome_metrics": session_data.get("outcome_metrics"),
        "session_metrics": session_data.get("session_metrics"),
        "last_updated": session_data.get("last_updated"),
    }

    # Add environment summary (not full environment for CLI readability)
    if "environment" in session_data:
        env = session_data["environment"]
        details["environment_summary"] = {
            "platform": env.get("system", {}).get("platform"),
            "python_version": env.get("python", {}).get("version"),
            "working_directory": env.get("process", {}).get("working_directory"),
            "user": env.get("process", {}).get("user"),
        }

        # Include full environment data if requested
        if include_raw_data:
            details["environment_full"] = env

    # Collect agent information
    agents_dir = session_dir / "agents"
    details["agents"] = {}
    agent_summaries = []

    if agents_dir.exists():
        for agent_path in agents_dir.iterdir():
            if agent_path.is_dir():
                agent_id = agent_path.name

                # Load agent metadata
                metadata = load_json_data(agent_path / "metadata.json", {})
                executions = load_json_data(agent_path / "execution.json", [])
                tools = load_json_data(agent_path / "tools.json", [])
                interactions = load_json_data(agent_path / "interactions.json", [])

                # Create agent summary
                agent_summary = {
                    "agent_id": agent_id,
                    "agent_type": metadata.get("agent_type", "unknown"),
                    "purpose": metadata.get("purpose"),
                    "status": metadata.get("status", "unknown"),
                    "capabilities": metadata.get("capabilities", []),
                    "registration_timestamp": metadata.get("timestamp"),
                    "execution_count": len(executions),
                    "tool_request_count": len(tools),
                    "interaction_count": len(interactions),
                    "last_activity": get_last_agent_activity(session_id, agent_id),
                }

                # Add interaction statistics
                interaction_stats = get_agent_interaction_statistics(
                    session_id, agent_id
                )
                if interaction_stats:
                    agent_summary["interaction_stats"] = interaction_stats

                agent_summaries.append(agent_summary)

                # Include full agent data if requested
                if include_raw_data:
                    details["agents"][agent_id] = {
                        "metadata": metadata,
                        "executions": executions,
                        "tool_requests": tools,
                        "interactions": interactions,
                    }

    details["agent_summaries"] = agent_summaries
    details["agent_count"] = len(agent_summaries)

    return details


def _list_session_agents_cli_impl(
    session_id: str,
    include_stats: bool = True,
    sort_by: str = "registration_timestamp",
    agent_type_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    Internal implementation for CLI-friendly agent listing within a session.
    """
    if not session_exists(session_id):
        return []

    session_dir = get_session_directory(session_id)
    agents_dir = session_dir / "agents"

    if not agents_dir.exists():
        return []

    agents = []
    for agent_path in agents_dir.iterdir():
        if agent_path.is_dir():
            agent_id = agent_path.name

            # Load agent metadata
            metadata = load_json_data(agent_path / "metadata.json", {})
            agent_type = metadata.get("agent_type", "unknown")

            # Apply agent type filter if specified
            if agent_type_filter and agent_type != agent_type_filter:
                continue

            # Build agent information
            agent_info = {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "purpose": metadata.get("purpose"),
                "status": metadata.get("status", "unknown"),
                "capabilities": metadata.get("capabilities", []),
                "registration_timestamp": metadata.get("timestamp"),
                "registration_context": metadata.get("registration_context", {}),
            }

            if include_stats:
                # Load activity counts
                executions = load_json_data(agent_path / "execution.json", [])
                tools = load_json_data(agent_path / "tools.json", [])
                interactions = load_json_data(agent_path / "interactions.json", [])

                agent_info.update(
                    {
                        "execution_count": len(executions),
                        "tool_request_count": len(tools),
                        "interaction_count": len(interactions),
                        "last_activity": get_last_agent_activity(session_id, agent_id),
                    }
                )

                # Include interaction statistics
                interaction_stats = get_agent_interaction_statistics(
                    session_id, agent_id
                )
                if interaction_stats:
                    agent_info["interaction_stats"] = interaction_stats

            agents.append(agent_info)

    # Sort agents
    valid_sort_keys = [
        "registration_timestamp",
        "agent_type",
        "agent_id",
        "execution_count",
        "tool_request_count",
        "interaction_count",
    ]
    if sort_by not in valid_sort_keys:
        sort_by = "registration_timestamp"

    # Handle None values in sorting
    def sort_key(agent):
        value = agent.get(sort_by)
        if value is None:
            return "" if sort_by in ["agent_type", "agent_id"] else 0
        return value

    agents.sort(key=sort_key)

    return agents


def _get_agent_details_impl(
    session_id: str,
    agent_id: str,
    include_executions: bool = False,
    include_tools: bool = False,
    include_interactions: bool = False,
    execution_limit: int | None = None,
) -> dict[str, Any]:
    """
    Internal implementation for CLI-friendly detailed agent data retrieval.
    """
    if not session_exists(session_id):
        return {"error": f"Session {session_id} not found"}

    if not agent_exists(session_id, agent_id):
        return {"error": f"Agent {agent_id} not found in session {session_id}"}

    agent_dir = get_agent_directory(session_id, agent_id)

    # Load all agent data
    metadata = load_json_data(agent_dir / "metadata.json", {})
    executions = load_json_data(agent_dir / "execution.json", [])
    tools = load_json_data(agent_dir / "tools.json", [])
    interactions = load_json_data(agent_dir / "interactions.json", [])

    # Build comprehensive agent details
    details = {
        "agent_id": agent_id,
        "session_id": session_id,
        "agent_type": metadata.get("agent_type", "unknown"),
        "purpose": metadata.get("purpose"),
        "status": metadata.get("status", "unknown"),
        "capabilities": metadata.get("capabilities", []),
        "registration_timestamp": metadata.get("timestamp"),
        "registration_context": metadata.get("registration_context", {}),
        "metadata": metadata.get("metadata", {}),
    }

    # Add activity statistics
    details.update(
        {
            "execution_count": len(executions),
            "tool_request_count": len(tools),
            "interaction_count": len(interactions),
            "last_activity": get_last_agent_activity(session_id, agent_id),
        }
    )

    # Include interaction statistics
    interaction_stats = get_agent_interaction_statistics(session_id, agent_id)
    if interaction_stats:
        details["interaction_stats"] = interaction_stats

    # Include detailed data if requested
    if include_executions:
        limited_executions = executions
        if execution_limit and execution_limit > 0:
            limited_executions = executions[-execution_limit:]  # Get most recent
        details["executions"] = limited_executions

    if include_tools:
        tool_limit = execution_limit if execution_limit else None
        limited_tools = tools
        if tool_limit and tool_limit > 0:
            limited_tools = tools[-tool_limit:]  # Get most recent
        details["tool_requests"] = limited_tools

    if include_interactions:
        interaction_limit = execution_limit if execution_limit else None
        limited_interactions = interactions
        if interaction_limit and interaction_limit > 0:
            limited_interactions = interactions[-interaction_limit:]  # Get most recent
        details["interactions"] = limited_interactions

    return details


# =============================================================================
# FASTMCP 2.0 RESOURCES - CLI DATA ACCESS ENDPOINTS
# =============================================================================


@app.resource("notes://sessions/list/{query}")
def cli_list_sessions(
    query: str = "all",
    status: str | None = None,
    sort_by: str = "timestamp",
    reverse: bool = True,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    CLI-friendly endpoint to list all tracked sessions with filtering and sorting.

    Args:
        query: Query type ("all", "active", "completed", or custom filter)

    Query Parameters:
    - status: Filter by session status ("active", "completed", etc.)
    - sort_by: Sort field ("timestamp", "status", "duration", "agent_count", "total_executions")
    - reverse: Sort in descending order (default: True)
    - limit: Maximum number of sessions to return

    Returns:
        List of session summaries with comprehensive metadata
    """
    # Use query parameter to set status filter if not explicitly provided
    if status is None and query != "all":
        status = query
    return _list_sessions_cli_impl(status, sort_by, reverse, limit)


@app.resource("notes://sessions/get/{session_id}")
def cli_get_session_details(
    session_id: str,
    include_raw_data: bool = False,
) -> dict[str, Any]:
    """
    CLI-friendly endpoint to get detailed session information.

    Args:
        session_id: Session ID to retrieve
        include_raw_data: Include complete raw data (environment, agent data)

    Returns:
        Detailed session information with agent summaries
    """
    return _get_session_details_impl(session_id, include_raw_data)


@app.resource("notes://agents/list/{session_id}")
def cli_list_session_agents(
    session_id: str,
    include_stats: bool = True,
    sort_by: str = "registration_timestamp",
    agent_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    CLI-friendly endpoint to list all agents within a session.

    Args:
        session_id: Session ID to query
        include_stats: Include activity statistics for each agent
        sort_by: Sort field ("registration_timestamp", "agent_type", "agent_id",
                           "execution_count", "tool_request_count", "interaction_count")
        agent_type: Filter by agent type

    Returns:
        List of agent information with statistics
    """
    return _list_session_agents_cli_impl(session_id, include_stats, sort_by, agent_type)


@app.resource("notes://agents/get/{session_id}/{agent_id}")
def cli_get_agent_details(
    session_id: str,
    agent_id: str,
    include_executions: bool = False,
    include_tools: bool = False,
    include_interactions: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """
    CLI-friendly endpoint to get detailed agent information.

    Args:
        session_id: Session ID containing the agent
        agent_id: Agent ID to retrieve
        include_executions: Include execution history
        include_tools: Include tool request history
        include_interactions: Include interaction history
        limit: Limit number of historical records returned (most recent)

    Returns:
        Detailed agent information with optional historical data
    """
    return _get_agent_details_impl(
        session_id,
        agent_id,
        include_executions,
        include_tools,
        include_interactions,
        limit,
    )


@app.resource("notes://search/sessions/{search_term}")
def cli_search_sessions(
    search_term: str = "all",
    query: str | None = None,
    agent_type: str | None = None,
    min_duration: float | None = None,
    max_duration: float | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    """
    CLI-friendly endpoint to search sessions with advanced filtering.

    Args:
        search_term: Primary search term (use "all" for no text filtering)

    Query Parameters:
    - query: Additional search term for session outcomes or environment data
    - agent_type: Filter sessions that contain agents of this type
    - min_duration: Minimum session duration in seconds
    - max_duration: Maximum session duration in seconds
    - date_from: Start date filter (ISO format)
    - date_to: End date filter (ISO format)

    Returns:
        List of matching sessions with relevance scoring
    """
    sessions = _list_sessions_cli_impl()
    filtered_sessions = []

    # Use search_term as primary query if no explicit query provided
    if query is None and search_term != "all":
        query = search_term

    for session in sessions:
        # Apply duration filters
        duration = session.get("duration")
        if min_duration is not None and (duration is None or duration < min_duration):
            continue
        if max_duration is not None and (duration is None or duration > max_duration):
            continue

        # Apply date filters
        timestamp = session.get("timestamp")
        if date_from and timestamp and timestamp < date_from:
            continue
        if date_to and timestamp and timestamp > date_to:
            continue

        # Apply agent type filter
        if agent_type and agent_type not in session.get("agent_types", []):
            continue

        # Apply text search (basic implementation)
        if query:
            search_text = f"{session.get('session_id', '')} {session.get('status', '')}"
            # Load full session data for deeper search
            full_session = _get_session_details_impl(session["session_id"])
            if "outcome" in full_session and full_session["outcome"]:
                search_text += f" {full_session['outcome']}"

            if query.lower() not in search_text.lower():
                continue

        filtered_sessions.append(session)

    return filtered_sessions


# =============================================================================
# LEGACY FASTMCP 2.0 RESOURCES - DATA ACCESS (Maintained for compatibility)
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
    log_agent_interaction = _log_agent_interaction_impl  # type: ignore[assignment]

    # Legacy resource functions (override FastMCP-wrapped functions for direct testing)
    get_session = _get_session_impl  # type: ignore[assignment]
    list_sessions = _list_sessions_impl  # type: ignore[assignment]

    # CLI resource functions (override FastMCP-wrapped functions for direct testing)
    cli_list_sessions = _list_sessions_cli_impl  # type: ignore[assignment]
    cli_get_session_details = _get_session_details_impl  # type: ignore[assignment]
    cli_list_session_agents = _list_session_agents_cli_impl  # type: ignore[assignment]
    cli_get_agent_details = _get_agent_details_impl  # type: ignore[assignment]


# =============================================================================
# SERVER STARTUP
# =============================================================================


def main() -> None:
    """Main entry point for the MCP server"""
    logger.info("Starting Session Notes MCP Server with FastMCP 2.0")
    logger.info(
        "Available tools: start_session, end_session, update_session_metadata, "
        "get_session_status, register_agent, get_agent_metadata, "
        "log_agent_execution, log_tool_request, log_agent_interaction"
    )
    logger.info(
        "Available CLI data access resources: "
        "notes://sessions/list/{query}, notes://sessions/get/{id}, "
        "notes://agents/list/{session_id}, notes://agents/get/{session_id}/{agent_id}, "
        "notes://search/sessions/{search_term}"
    )
    logger.info(
        "Legacy compatibility resources: session://{id}, sessions://list, "
        "agent://{session_id}/{agent_id}, agents://{session_id}"
    )

    # Run the FastMCP server
    app.run()


if __name__ == "__main__":
    main()
