"""
Fixed comprehensive tests for Session Notes FastMCP 2.0 Server.

Tests all FastMCP tools, resources, and data models with correct API usage.
"""

import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from session_notes.server import (
    AgentExecution,
    SessionInfo,
    ToolRequest,
    app,
    end_session,
    ensure_directory,
    get_agent_directory,
    get_session,
    get_session_directory,
    list_sessions,
    load_json_data,
    log_agent_execution,
    log_tool_request,
    save_json_data,
    # Import the actual tool and resource functions
    start_session,
)


class TestDataModels:
    """Test Pydantic data models."""

    def test_session_info_creation(self):
        """Test SessionInfo model creation and validation."""
        session = SessionInfo(
            session_id="test-session-123",
            timestamp="2024-01-15T10:30:00Z",
            duration=300.5,
            environment={"python_version": "3.12", "os": "linux"},
            status="active",
        )

        assert session.session_id == "test-session-123"
        assert session.timestamp == "2024-01-15T10:30:00Z"
        assert session.duration == 300.5
        assert session.environment == {"python_version": "3.12", "os": "linux"}
        assert session.status == "active"

    def test_session_info_defaults(self):
        """Test SessionInfo with minimal required fields."""
        session = SessionInfo(
            session_id="minimal-session", timestamp="2024-01-15T10:30:00Z"
        )

        assert session.session_id == "minimal-session"
        assert session.timestamp == "2024-01-15T10:30:00Z"
        assert session.duration is None
        assert session.environment == {}
        assert session.status == "active"

    def test_agent_execution_creation(self):
        """Test AgentExecution model creation and validation."""
        execution = AgentExecution(
            agent_id="agent-001",
            agent_type="code-reviewer",
            timestamp="2024-01-15T10:35:00Z",
            action="review_code",
            parameters={"file_path": "test.py", "severity": "high"},
            result={"issues_found": 3, "status": "completed"},
            execution_time=1500.0,
        )

        assert execution.agent_id == "agent-001"
        assert execution.agent_type == "code-reviewer"
        assert execution.timestamp == "2024-01-15T10:35:00Z"
        assert execution.action == "review_code"
        assert execution.parameters == {"file_path": "test.py", "severity": "high"}
        assert execution.result == {"issues_found": 3, "status": "completed"}
        assert execution.execution_time == 1500.0

    def test_tool_request_creation(self):
        """Test ToolRequest model creation and validation."""
        tool_request = ToolRequest(
            tool_name="file_reader",
            available=True,
            parameters={"file_path": "/path/to/file.txt", "encoding": "utf-8"},
            success=True,
            timestamp="2024-01-15T10:40:00Z",
        )

        assert tool_request.tool_name == "file_reader"
        assert tool_request.available is True
        assert tool_request.parameters == {
            "file_path": "/path/to/file.txt",
            "encoding": "utf-8",
        }
        assert tool_request.success is True
        assert tool_request.timestamp == "2024-01-15T10:40:00Z"

    def test_pydantic_validation_errors(self):
        """Test that Pydantic validation works correctly."""
        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            SessionInfo()  # Missing required session_id and timestamp

        with pytest.raises(ValidationError):
            AgentExecution(agent_id="test")  # Missing required fields

        with pytest.raises(ValidationError):
            ToolRequest(tool_name="test")  # Missing required fields


class TestStorageUtilities:
    """Test storage utility functions."""

    def setup_method(self):
        """Set up test directories."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        # Change to temp directory to isolate .claude directory
        import os

        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up test directories."""
        import os

        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_session_directory(self):
        """Test session directory path generation."""
        session_id = "test-session-123"
        expected_path = Path(".claude/session-notes/test-session-123")
        actual_path = get_session_directory(session_id)

        assert actual_path == expected_path

    def test_get_agent_directory(self):
        """Test agent directory path generation."""
        session_id = "test-session-123"
        agent_id = "agent-456"
        expected_path = Path(".claude/session-notes/test-session-123/agents/agent-456")
        actual_path = get_agent_directory(session_id, agent_id)

        assert actual_path == expected_path

    def test_ensure_directory(self):
        """Test directory creation."""
        test_path = self.temp_dir / "test" / "nested" / "directory"
        assert not test_path.exists()

        ensure_directory(test_path)
        assert test_path.exists()
        assert test_path.is_dir()

        # Test idempotency
        ensure_directory(test_path)
        assert test_path.exists()

    def test_save_json_data(self):
        """Test JSON data saving."""
        test_file = self.temp_dir / "nested" / "test.json"
        test_data = {"key": "value", "number": 42, "nested": {"inner": "data"}}

        save_json_data(test_file, test_data)

        assert test_file.exists()
        with open(test_file, encoding="utf-8") as f:
            loaded_data = json.load(f)

        assert loaded_data == test_data

    def test_load_json_data_existing_file(self):
        """Test JSON data loading from existing file."""
        test_file = self.temp_dir / "test_load.json"
        test_data = {"existing": "data", "count": 10}

        # Create test file
        test_file.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        loaded_data = load_json_data(test_file)
        assert loaded_data == test_data

    def test_load_json_data_nonexistent_file(self):
        """Test JSON data loading with default when file doesn't exist."""
        nonexistent_file = self.temp_dir / "nonexistent.json"
        default_data = {"default": "value"}

        loaded_data = load_json_data(nonexistent_file, default_data)
        assert loaded_data == default_data

        # Test with no default
        loaded_data = load_json_data(nonexistent_file)
        assert loaded_data is None


class TestFastMCPTools:
    """Test FastMCP 2.0 tool functions."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import os

        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("session_notes.server.datetime")
    def test_start_session_with_provided_id(self, mock_datetime):
        """Test starting a session with provided session ID."""
        # Mock datetime
        mock_now = Mock()
        mock_now.isoformat.return_value = "2024-01-15T10:30:00Z"
        mock_datetime.now.return_value = mock_now

        session_id = "custom-session-123"
        environment_info = {"python_version": "3.12", "platform": "linux"}

        result = start_session.fn(session_id, environment_info)

        # Check result message
        assert result == f"Session {session_id} started successfully"

        # Verify session file was created
        session_dir = get_session_directory(session_id)
        session_file = session_dir / "session.json"
        assert session_file.exists()

        # Check session data
        with open(session_file, encoding="utf-8") as f:
            session_data = json.load(f)

        assert session_data["session_id"] == session_id
        assert session_data["timestamp"] == "2024-01-15T10:30:00Z"
        assert session_data["environment"] == environment_info
        assert session_data["status"] == "active"
        assert session_data["duration"] is None

    @patch("session_notes.server.datetime")
    @patch("session_notes.server.uuid")
    def test_start_session_auto_generated_id(self, mock_uuid, mock_datetime):
        """Test starting a session with auto-generated ID."""
        # Mock UUID generation
        mock_uuid.uuid4.return_value = Mock()
        mock_uuid.uuid4.return_value.__str__ = Mock(return_value="auto-generated-uuid")

        # Mock datetime
        mock_now = Mock()
        mock_now.isoformat.return_value = "2024-01-15T10:30:00Z"
        mock_datetime.now.return_value = mock_now

        result = start_session.fn()

        assert result == "Session auto-generated-uuid started successfully"

        # Verify session was created
        session_dir = get_session_directory("auto-generated-uuid")
        assert session_dir.exists()

    @patch("session_notes.server.datetime")
    def test_end_session_success(self, mock_datetime):
        """Test successfully ending a session."""
        # Create initial session
        session_id = "test-end-session"
        start_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)

        # Set up session file
        session_dir = get_session_directory(session_id)
        session_file = session_dir / "session.json"
        session_data = {
            "session_id": session_id,
            "timestamp": start_time.isoformat(),
            "status": "active",
        }
        save_json_data(session_file, session_data)

        # Mock datetime for end time
        mock_datetime.now.return_value = end_time
        mock_datetime.fromisoformat.return_value = start_time

        result = end_session.fn(session_id)

        assert result == f"Session {session_id} ended successfully"

        # Check updated session data
        with open(session_file, encoding="utf-8") as f:
            updated_data = json.load(f)

        assert updated_data["status"] == "completed"
        assert updated_data["duration"] == 1800.0  # 30 minutes in seconds
        assert "end_timestamp" in updated_data

    def test_end_session_not_found(self):
        """Test ending a session that doesn't exist."""
        session_id = "nonexistent-session"

        result = end_session.fn(session_id)

        assert result == f"Session {session_id} not found"

    @patch("session_notes.server.datetime")
    def test_log_agent_execution_full(self, mock_datetime):
        """Test logging agent execution with all parameters."""
        # Mock datetime
        mock_now = Mock()
        mock_now.isoformat.return_value = "2024-01-15T10:35:00Z"
        mock_datetime.now.return_value = mock_now

        session_id = "test-session"
        agent_id = "test-agent"
        agent_type = "code-reviewer"
        action = "review_code"
        parameters = {"file_path": "test.py", "severity": "high"}
        result_data = {"issues_found": 3, "status": "completed"}
        execution_time = 1500.0

        result = log_agent_execution.fn(
            session_id,
            agent_id,
            agent_type,
            action,
            parameters,
            result_data,
            execution_time,
        )

        assert result == f"Logged execution for agent {agent_id}: {action}"

        # Verify execution was logged
        agent_dir = get_agent_directory(session_id, agent_id)
        execution_file = agent_dir / "execution.json"
        assert execution_file.exists()

        with open(execution_file, encoding="utf-8") as f:
            executions = json.load(f)

        assert len(executions) == 1
        execution = executions[0]
        assert execution["agent_id"] == agent_id
        assert execution["agent_type"] == agent_type
        assert execution["action"] == action
        assert execution["parameters"] == parameters
        assert execution["result"] == result_data
        assert execution["execution_time"] == execution_time

    @patch("session_notes.server.datetime")
    def test_log_tool_request_full(self, mock_datetime):
        """Test logging tool request with all parameters."""
        mock_now = Mock()
        mock_now.isoformat.return_value = "2024-01-15T10:40:00Z"
        mock_datetime.now.return_value = mock_now

        session_id = "test-session"
        agent_id = "test-agent"
        tool_name = "file_reader"
        available = True
        success = True
        parameters = {"file_path": "/path/to/file.txt", "encoding": "utf-8"}

        result = log_tool_request.fn(
            session_id,
            agent_id,
            tool_name,
            available,
            success,
            parameters,
        )

        expected_message = f"Logged tool request: {tool_name} (available: {available}, success: {success})"
        assert result == expected_message

        # Verify tool request was logged
        agent_dir = get_agent_directory(session_id, agent_id)
        tools_file = agent_dir / "tools.json"
        assert tools_file.exists()

        with open(tools_file, encoding="utf-8") as f:
            tool_requests = json.load(f)

        assert len(tool_requests) == 1
        request = tool_requests[0]
        assert request["tool_name"] == tool_name
        assert request["available"] == available
        assert request["success"] == success
        assert request["parameters"] == parameters


class TestFastMCPResources:
    """Test FastMCP 2.0 resource functions."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import os

        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_session_full_data(self):
        """Test retrieving complete session data."""
        session_id = "test-get-session"

        # Create session data
        session_dir = get_session_directory(session_id)
        session_data = {
            "session_id": session_id,
            "timestamp": "2024-01-15T10:30:00Z",
            "status": "active",
            "environment": {"python": "3.12"},
        }
        save_json_data(session_dir / "session.json", session_data)

        # Create agent executions
        agent_id = "test-agent"
        agent_dir = get_agent_directory(session_id, agent_id)

        executions = [
            {
                "agent_id": agent_id,
                "agent_type": "code-reviewer",
                "action": "review",
                "timestamp": "2024-01-15T10:35:00Z",
                "parameters": {},
                "result": None,
                "execution_time": None,
            }
        ]
        save_json_data(agent_dir / "execution.json", executions)

        tool_requests = [
            {
                "tool_name": "file_reader",
                "available": True,
                "success": True,
                "parameters": {"file": "test.py"},
                "timestamp": "2024-01-15T10:40:00Z",
            }
        ]
        save_json_data(agent_dir / "tools.json", tool_requests)

        # Get session data using resource
        result = get_session.fn(session_id)

        assert result["session_id"] == session_id
        assert result["timestamp"] == "2024-01-15T10:30:00Z"
        assert result["status"] == "active"
        assert result["environment"] == {"python": "3.12"}
        assert "agents" in result
        assert agent_id in result["agents"]
        assert result["agents"][agent_id]["executions"] == executions
        assert result["agents"][agent_id]["tool_requests"] == tool_requests

    def test_get_session_not_found(self):
        """Test retrieving non-existent session."""
        session_id = "nonexistent-session"

        result = get_session.fn(session_id)

        assert result == {"error": f"Session {session_id} not found"}

    def test_list_sessions_empty(self):
        """Test listing sessions when none exist."""
        result = list_sessions.fn()

        assert result == []

    def test_list_sessions_single(self):
        """Test listing single session."""
        session_id = "list-test-session"

        # Create session
        session_dir = get_session_directory(session_id)
        session_data = {
            "session_id": session_id,
            "timestamp": "2024-01-15T10:30:00Z",
            "status": "completed",
            "duration": 1800.0,
        }
        save_json_data(session_dir / "session.json", session_data)

        # Create some agent data to test agent count
        agent_dir = get_agent_directory(session_id, "agent1")
        ensure_directory(agent_dir)
        agent_dir2 = get_agent_directory(session_id, "agent2")
        ensure_directory(agent_dir2)

        result = list_sessions.fn()

        assert len(result) == 1
        session_summary = result[0]
        assert session_summary["session_id"] == session_id
        assert session_summary["timestamp"] == "2024-01-15T10:30:00Z"
        assert session_summary["status"] == "completed"
        assert session_summary["duration"] == 1800.0
        assert session_summary["agent_count"] == 2


class TestIntegrationWorkflows:
    """End-to-end integration tests for complete workflows."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import os

        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("session_notes.server.datetime")
    def test_complete_session_lifecycle(self, mock_datetime):
        """Test complete session lifecycle from start to end."""
        # Mock datetime for consistent timestamps
        start_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)

        mock_datetime.now.side_effect = [
            start_time,
            start_time,
            start_time,
            end_time,
            end_time,
        ]
        mock_datetime.fromisoformat.return_value = start_time

        session_id = "lifecycle-test"
        environment = {"python_version": "3.12", "platform": "linux"}

        # 1. Start session
        start_result = start_session.fn(session_id, environment)
        assert "started successfully" in start_result

        # 2. Log agent execution
        agent_id = "test-agent"
        execution_result = log_agent_execution.fn(
            session_id,
            agent_id,
            "code-reviewer",
            "review_code",
            {"file": "test.py"},
            {"issues": 2},
            1200.0,
        )
        assert "Logged execution" in execution_result

        # 3. Log tool request
        tool_result = log_tool_request.fn(
            session_id,
            agent_id,
            "file_reader",
            True,
            True,
            {"path": "test.py"},
        )
        assert "Logged tool request" in tool_result

        # 4. Get session data
        session_data = get_session.fn(session_id)
        assert session_data["session_id"] == session_id
        assert session_data["status"] == "active"
        assert agent_id in session_data["agents"]

        # 5. End session
        end_result = end_session.fn(session_id)
        assert "ended successfully" in end_result

        # 6. Verify final session state
        final_data = get_session.fn(session_id)
        assert final_data["status"] == "completed"
        assert final_data["duration"] == 1800.0  # 30 minutes

        # 7. Verify session appears in list
        sessions_list = list_sessions.fn()
        assert len(sessions_list) == 1
        assert sessions_list[0]["session_id"] == session_id


class TestFastMCPAppIntegration:
    """Integration tests for FastMCP app configuration."""

    def test_fastmcp_app_configuration(self):
        """Test FastMCP application configuration."""
        assert app.name == "session-notes"
        # Note: FastMCP 2.0 doesn't have a version attribute in the app object
        assert hasattr(app, "name")

    async def test_tool_registration(self):
        """Test that all tools are properly registered with FastMCP."""
        expected_tools = [
            "start_session",
            "end_session",
            "log_agent_execution",
            "log_tool_request",
        ]

        tools = await app.get_tools()

        for tool_name in expected_tools:
            assert tool_name in tools

    async def test_resource_registration(self):
        """Test that all resources are properly registered with FastMCP."""
        resources = await app.get_resources()

        # Check that sessions list resource exists
        assert "sessions://list" in resources


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
