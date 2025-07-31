#!/usr/bin/env python3
"""
Test suite for agent logging framework functionality in the session-notes MCP server.

Tests the comprehensive agent registration, metadata tracking, and integration
with existing execution and tool request logging systems.
"""

import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from session_notes.server import (
    AgentMetadata,
    _get_agent_metadata_impl,
    _get_session_impl,
    _log_agent_execution_impl,
    _log_tool_request_impl,
    _register_agent_impl,
    _start_session_impl,
    agent_exists,
    get_agent_directory,
    get_last_agent_activity,
    list_session_agents,
    session_exists,
)


class TestAgentMetadataModel:
    """Test the AgentMetadata Pydantic model."""

    def test_agent_metadata_creation_minimal(self):
        """Test creating AgentMetadata with minimal required fields."""
        metadata = AgentMetadata(
            agent_id="test-agent-123",
            agent_type="test-agent",
            timestamp="2023-01-01T00:00:00Z",
            session_id="test-session",
        )

        assert metadata.agent_id == "test-agent-123"
        assert metadata.agent_type == "test-agent"
        assert metadata.timestamp == "2023-01-01T00:00:00Z"
        assert metadata.session_id == "test-session"
        assert metadata.purpose is None
        assert metadata.capabilities == []
        assert metadata.status == "active"
        assert metadata.metadata == {}
        assert metadata.registration_context == {}

    def test_agent_metadata_creation_complete(self):
        """Test creating AgentMetadata with all fields populated."""
        metadata = AgentMetadata(
            agent_id="comprehensive-agent",
            agent_type="code-reviewer",
            timestamp="2023-01-01T12:00:00Z",
            purpose="Review code for quality and standards compliance",
            capabilities=["static_analysis", "security_review", "performance_check"],
            session_id="comprehensive-session",
            status="active",
            metadata={"version": "1.0", "config": {"strict_mode": True}},
            registration_context={"trigger": "manual", "user": "developer"},
        )

        assert metadata.agent_id == "comprehensive-agent"
        assert metadata.agent_type == "code-reviewer"
        assert metadata.purpose == "Review code for quality and standards compliance"
        assert len(metadata.capabilities) == 3
        assert "static_analysis" in metadata.capabilities
        assert metadata.metadata["version"] == "1.0"
        assert metadata.registration_context["trigger"] == "manual"

    def test_agent_metadata_serialization(self):
        """Test AgentMetadata serialization to dict."""
        metadata = AgentMetadata(
            agent_id="serialization-test",
            agent_type="test-type",
            timestamp="2023-01-01T00:00:00Z",
            session_id="test-session",
            capabilities=["test-capability"],
            metadata={"test_key": "test_value"},
        )

        data = metadata.model_dump()

        assert isinstance(data, dict)
        assert data["agent_id"] == "serialization-test"
        assert data["capabilities"] == ["test-capability"]
        assert data["metadata"]["test_key"] == "test_value"


class TestAgentRegistration:
    """Test agent registration functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())

        # Patch the session directory to use our temp directory
        self.session_dir_patcher = patch(
            "session_notes.server.get_session_directory",
            return_value=self.test_dir / ".claude" / "session-notes" / self.session_id,
        )
        self.session_dir_patcher.start()

        # Create a test session
        _start_session_impl(self.session_id, auto_collect_environment=False)

    def teardown_method(self):
        """Clean up after each test."""
        self.session_dir_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_register_agent_minimal(self):
        """Test registering an agent with minimal parameters."""
        result = _register_agent_impl(
            session_id=self.session_id,
            agent_id="minimal-agent",
            agent_type="test-agent",
        )

        assert "minimal-agent" in result
        assert "registered successfully" in result
        assert agent_exists(self.session_id, "minimal-agent")

        # Verify directory structure
        agent_dir = get_agent_directory(self.session_id, "minimal-agent")
        assert agent_dir.exists()
        assert (agent_dir / "metadata.json").exists()
        assert (agent_dir / "execution.json").exists()
        assert (agent_dir / "tools.json").exists()

    def test_register_agent_comprehensive(self):
        """Test registering an agent with all parameters."""
        result = _register_agent_impl(
            session_id=self.session_id,
            agent_id="comprehensive-agent",
            agent_type="code-reviewer",
            purpose="Comprehensive code review and analysis",
            capabilities=["linting", "security", "performance"],
            metadata={"version": "2.0", "priority": "high"},
            registration_context={"source": "api", "user": "test-user"},
        )

        assert "comprehensive-agent" in result
        assert "registered successfully" in result

        # Verify metadata was saved correctly
        metadata = _get_agent_metadata_impl(self.session_id, "comprehensive-agent")
        assert metadata["agent_type"] == "code-reviewer"
        assert metadata["purpose"] == "Comprehensive code review and analysis"
        assert len(metadata["capabilities"]) == 3
        assert "linting" in metadata["capabilities"]
        assert metadata["metadata"]["version"] == "2.0"
        assert metadata["registration_context"]["source"] == "api"

    def test_register_agent_auto_id_generation(self):
        """Test that agent ID is auto-generated when not provided."""
        result = _register_agent_impl(
            session_id=self.session_id,
            agent_type="auto-id-agent",
        )

        assert "registered successfully" in result

        # Extract the generated agent ID from the result message
        import re

        match = re.search(r"Agent ([a-f0-9\-]+) registered", result)
        assert match
        generated_id = match.group(1)

        # Verify the agent exists with the generated ID
        assert agent_exists(self.session_id, generated_id)

        # Verify metadata contains the generated ID
        metadata = _get_agent_metadata_impl(self.session_id, generated_id)
        assert metadata["agent_id"] == generated_id

    def test_register_agent_invalid_session(self):
        """Test registering an agent in a non-existent session."""
        # Stop the existing patcher to test real behavior
        self.session_dir_patcher.stop()

        try:
            invalid_session = "non-existent-session"

            result = _register_agent_impl(
                session_id=invalid_session,
                agent_id="test-agent",
                agent_type="test-type",
            )

            assert "not found" in result
            assert invalid_session in result
        finally:
            # Restart the patcher for other tests
            self.session_dir_patcher.start()

    def test_register_agent_duplicate_id(self):
        """Test registering an agent with an existing ID (should succeed, updating metadata)."""
        agent_id = "duplicate-test-agent"

        # Register first time
        result1 = _register_agent_impl(
            session_id=self.session_id,
            agent_id=agent_id,
            agent_type="first-type",
            purpose="First registration",
        )
        assert "registered successfully" in result1

        # Register second time with different metadata
        result2 = _register_agent_impl(
            session_id=self.session_id,
            agent_id=agent_id,
            agent_type="second-type",
            purpose="Second registration",
        )
        assert "registered successfully" in result2

        # Verify the latest metadata
        metadata = _get_agent_metadata_impl(self.session_id, agent_id)
        assert metadata["agent_type"] == "second-type"
        assert metadata["purpose"] == "Second registration"


class TestAgentMetadataRetrieval:
    """Test agent metadata retrieval functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())

        # Patch the session directory to use our temp directory
        self.session_dir_patcher = patch(
            "session_notes.server.get_session_directory",
            return_value=self.test_dir / ".claude" / "session-notes" / self.session_id,
        )
        self.session_dir_patcher.start()

        # Create a test session and register a test agent
        _start_session_impl(self.session_id, auto_collect_environment=False)
        self.agent_id = "test-metadata-agent"
        _register_agent_impl(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_type="metadata-test",
            purpose="Testing metadata retrieval",
            capabilities=["test1", "test2"],
            metadata={"custom": "value"},
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.session_dir_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_agent_metadata_basic(self):
        """Test retrieving basic agent metadata."""
        metadata = _get_agent_metadata_impl(self.session_id, self.agent_id)

        assert metadata["agent_id"] == self.agent_id
        assert metadata["agent_type"] == "metadata-test"
        assert metadata["purpose"] == "Testing metadata retrieval"
        assert metadata["capabilities"] == ["test1", "test2"]
        assert metadata["metadata"]["custom"] == "value"
        assert metadata["status"] == "active"

    def test_get_agent_metadata_with_statistics(self):
        """Test that agent metadata includes activity statistics."""
        # Add some execution and tool request data
        _log_agent_execution_impl(
            self.session_id,
            self.agent_id,
            "metadata-test",
            "test-action",
            auto_register=False,
        )
        _log_tool_request_impl(self.session_id, self.agent_id, "test-tool", True)

        metadata = _get_agent_metadata_impl(self.session_id, self.agent_id)

        assert "statistics" in metadata
        assert metadata["statistics"]["execution_count"] == 1
        assert metadata["statistics"]["tool_request_count"] == 1
        assert metadata["statistics"]["last_activity"] is not None

    def test_get_agent_metadata_nonexistent_agent(self):
        """Test retrieving metadata for a non-existent agent."""
        metadata = _get_agent_metadata_impl(self.session_id, "nonexistent-agent")

        assert "error" in metadata
        assert "not found" in metadata["error"]

    def test_get_agent_metadata_nonexistent_session(self):
        """Test retrieving metadata from a non-existent session."""
        # Stop the existing patcher to test real behavior
        self.session_dir_patcher.stop()

        try:
            metadata = _get_agent_metadata_impl("nonexistent-session", self.agent_id)

            assert "error" in metadata
            assert "Session" in metadata["error"]
            assert "not found" in metadata["error"]
        finally:
            # Restart the patcher for other tests
            self.session_dir_patcher.start()


class TestAgentAutoRegistration:
    """Test automatic agent registration during execution logging."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())

        # Patch the session directory to use our temp directory
        self.session_dir_patcher = patch(
            "session_notes.server.get_session_directory",
            return_value=self.test_dir / ".claude" / "session-notes" / self.session_id,
        )
        self.session_dir_patcher.start()

        # Create a test session
        _start_session_impl(self.session_id, auto_collect_environment=False)

    def teardown_method(self):
        """Clean up after each test."""
        self.session_dir_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_auto_registration_on_execution(self):
        """Test that agents are auto-registered when logging execution."""
        agent_id = "auto-registered-agent"

        # Verify agent doesn't exist initially
        assert not agent_exists(self.session_id, agent_id)

        # Log execution with auto-registration enabled
        result = _log_agent_execution_impl(
            session_id=self.session_id,
            agent_id=agent_id,
            agent_type="auto-test-agent",
            action="first-action",
            auto_register=True,
        )

        assert "Logged execution" in result

        # Verify agent was auto-registered
        assert agent_exists(self.session_id, agent_id)

        # Verify auto-registration metadata
        metadata = _get_agent_metadata_impl(self.session_id, agent_id)
        assert metadata["agent_type"] == "auto-test-agent"
        assert "Auto-registered" in metadata["purpose"]
        assert metadata["registration_context"]["auto_registered"] is True
        assert metadata["registration_context"]["first_action"] == "first-action"

    def test_auto_registration_disabled(self):
        """Test that auto-registration can be disabled."""
        agent_id = "no-auto-register-agent"

        # Log execution with auto-registration disabled
        result = _log_agent_execution_impl(
            session_id=self.session_id,
            agent_id=agent_id,
            agent_type="no-auto-type",
            action="test-action",
            auto_register=False,
        )

        assert "Logged execution" in result

        # Verify agent directory was created for logging but no metadata
        assert agent_exists(self.session_id, agent_id)
        agent_dir = get_agent_directory(self.session_id, agent_id)
        assert (agent_dir / "execution.json").exists()

        # Metadata file should not exist (no registration)
        metadata = _get_agent_metadata_impl(self.session_id, agent_id)
        assert "error" in metadata or not metadata

    def test_no_duplicate_registration(self):
        """Test that already registered agents are not re-registered."""
        agent_id = "already-registered-agent"

        # Register agent manually first
        _register_agent_impl(
            session_id=self.session_id,
            agent_id=agent_id,
            agent_type="manual-type",
            purpose="Manually registered",
        )

        original_metadata = _get_agent_metadata_impl(self.session_id, agent_id)
        original_timestamp = original_metadata["timestamp"]

        # Log execution (should not re-register)
        _log_agent_execution_impl(
            session_id=self.session_id,
            agent_id=agent_id,
            agent_type="execution-type",
            action="test-action",
            auto_register=True,
        )

        # Verify original registration metadata is preserved
        current_metadata = _get_agent_metadata_impl(self.session_id, agent_id)
        assert current_metadata["agent_type"] == "manual-type"
        assert current_metadata["purpose"] == "Manually registered"
        assert current_metadata["timestamp"] == original_timestamp
        assert (
            current_metadata["registration_context"].get("auto_registered") is not True
        )


class TestAgentActivityTracking:
    """Test agent activity tracking and statistics."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())

        # Patch the session directory to use our temp directory
        self.session_dir_patcher = patch(
            "session_notes.server.get_session_directory",
            return_value=self.test_dir / ".claude" / "session-notes" / self.session_id,
        )
        self.session_dir_patcher.start()

        # Create a test session and agent
        _start_session_impl(self.session_id, auto_collect_environment=False)
        self.agent_id = "activity-test-agent"
        _register_agent_impl(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_type="activity-tracker",
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.session_dir_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_last_activity_tracking(self):
        """Test tracking of last agent activity timestamp."""
        # Initially no activity
        assert get_last_agent_activity(self.session_id, self.agent_id) is None

        # Log execution
        _log_agent_execution_impl(
            self.session_id,
            self.agent_id,
            "activity-tracker",
            "test-action",
            auto_register=False,
        )

        # Should have last activity timestamp
        last_activity = get_last_agent_activity(self.session_id, self.agent_id)
        assert last_activity is not None

        # Parse timestamp to verify it's recent
        activity_time = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        time_diff = (now - activity_time).total_seconds()
        assert time_diff < 60  # Should be within last minute

    def test_activity_statistics_in_metadata(self):
        """Test that activity statistics are included in agent metadata."""
        # Log multiple activities
        _log_agent_execution_impl(
            self.session_id,
            self.agent_id,
            "activity-tracker",
            "action1",
            auto_register=False,
        )
        _log_agent_execution_impl(
            self.session_id,
            self.agent_id,
            "activity-tracker",
            "action2",
            auto_register=False,
        )
        _log_tool_request_impl(self.session_id, self.agent_id, "tool1", True)
        _log_tool_request_impl(self.session_id, self.agent_id, "tool2", False)

        metadata = _get_agent_metadata_impl(self.session_id, self.agent_id)
        stats = metadata["statistics"]

        assert stats["execution_count"] == 2
        assert stats["tool_request_count"] == 2
        assert stats["last_activity"] is not None

    def test_multiple_agents_activity(self):
        """Test activity tracking with multiple agents in same session."""
        # Register second agent
        agent2_id = "activity-test-agent-2"
        _register_agent_impl(
            session_id=self.session_id,
            agent_id=agent2_id,
            agent_type="activity-tracker-2",
        )

        # Log different activities for each agent
        _log_agent_execution_impl(
            self.session_id,
            self.agent_id,
            "activity-tracker",
            "agent1-action",
            auto_register=False,
        )
        _log_agent_execution_impl(
            self.session_id,
            agent2_id,
            "activity-tracker-2",
            "agent2-action",
            auto_register=False,
        )

        # Verify independent tracking
        metadata1 = _get_agent_metadata_impl(self.session_id, self.agent_id)
        metadata2 = _get_agent_metadata_impl(self.session_id, agent2_id)

        assert metadata1["statistics"]["execution_count"] == 1
        assert metadata2["statistics"]["execution_count"] == 1
        assert (
            metadata1["statistics"]["last_activity"]
            != metadata2["statistics"]["last_activity"]
        )


class TestSessionAgentIntegration:
    """Test integration of agent logging with session data retrieval."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())

        # Patch the session directory to use our temp directory
        self.session_dir_patcher = patch(
            "session_notes.server.get_session_directory",
            return_value=self.test_dir / ".claude" / "session-notes" / self.session_id,
        )
        self.session_dir_patcher.start()

        # Create a test session
        _start_session_impl(self.session_id, auto_collect_environment=False)

    def teardown_method(self):
        """Clean up after each test."""
        self.session_dir_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_session_includes_agent_metadata(self):
        """Test that get_session includes agent metadata."""
        # Register agent and log some activity
        agent_id = "integration-test-agent"
        _register_agent_impl(
            session_id=self.session_id,
            agent_id=agent_id,
            agent_type="integration-test",
            purpose="Testing session integration",
        )
        _log_agent_execution_impl(
            self.session_id,
            agent_id,
            "integration-test",
            "test-action",
            auto_register=False,
        )

        # Get session data
        session_data = _get_session_impl(self.session_id)

        assert "agents" in session_data
        assert agent_id in session_data["agents"]

        agent_data = session_data["agents"][agent_id]
        assert "metadata" in agent_data
        assert "executions" in agent_data
        assert "tool_requests" in agent_data

        # Verify metadata content
        assert agent_data["metadata"]["agent_type"] == "integration-test"
        assert agent_data["metadata"]["purpose"] == "Testing session integration"

        # Verify execution data
        assert len(agent_data["executions"]) == 1
        assert agent_data["executions"][0]["action"] == "test-action"

    def test_list_session_agents(self):
        """Test listing agents within a session."""
        # Initially no agents
        agents = list_session_agents(self.session_id)
        assert agents == []

        # Register multiple agents
        agent_ids = ["agent1", "agent2", "agent3"]
        for agent_id in agent_ids:
            _register_agent_impl(
                session_id=self.session_id,
                agent_id=agent_id,
                agent_type=f"test-{agent_id}",
            )

        # Verify all agents are listed
        agents = list_session_agents(self.session_id)
        assert len(agents) == 3
        for agent_id in agent_ids:
            assert agent_id in agents

    def test_session_agent_statistics(self):
        """Test that session statistics include agent information."""
        # Register agents and log activities
        for i in range(3):
            agent_id = f"stats-agent-{i}"
            _register_agent_impl(
                session_id=self.session_id,
                agent_id=agent_id,
                agent_type=f"stats-type-{i}",
            )
            # Log different numbers of executions per agent
            for j in range(i + 1):
                _log_agent_execution_impl(
                    self.session_id,
                    agent_id,
                    f"stats-type-{i}",
                    f"action-{j}",
                    auto_register=False,
                )

        session_data = _get_session_impl(self.session_id)

        # Verify we have 3 agents
        assert len(session_data["agents"]) == 3

        # Verify execution counts are different for each agent
        execution_counts = []
        for agent_data in session_data["agents"].values():
            execution_counts.append(len(agent_data["executions"]))

        assert sorted(execution_counts) == [1, 2, 3]


class TestUtilityFunctions:
    """Test utility functions related to agent logging."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())

        # Patch the session directory to use our temp directory
        self.session_dir_patcher = patch(
            "session_notes.server.get_session_directory",
            return_value=self.test_dir / ".claude" / "session-notes" / self.session_id,
        )
        self.session_dir_patcher.start()

        # Create a test session
        _start_session_impl(self.session_id, auto_collect_environment=False)

    def teardown_method(self):
        """Clean up after each test."""
        self.session_dir_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_agent_exists_function(self):
        """Test the agent_exists utility function."""
        agent_id = "existence-test-agent"

        # Initially doesn't exist
        assert not agent_exists(self.session_id, agent_id)

        # Register agent
        _register_agent_impl(
            session_id=self.session_id,
            agent_id=agent_id,
            agent_type="existence-test",
        )

        # Now should exist
        assert agent_exists(self.session_id, agent_id)

    def test_get_agent_directory_function(self):
        """Test the get_agent_directory utility function."""
        agent_id = "directory-test-agent"

        agent_dir = get_agent_directory(self.session_id, agent_id)
        expected_path = (
            self.test_dir
            / ".claude"
            / "session-notes"
            / self.session_id
            / "agents"
            / agent_id
        )

        assert agent_dir == expected_path

    def test_session_exists_function(self):
        """Test the session_exists utility function."""
        # Current session should exist
        assert session_exists(self.session_id)

        # Stop the patcher to test real behavior for non-existent session
        self.session_dir_patcher.stop()

        try:
            # Non-existent session should not exist
            assert not session_exists("non-existent-session")
        finally:
            # Restart the patcher for cleanup
            self.session_dir_patcher.start()


if __name__ == "__main__":
    pytest.main([__file__])
