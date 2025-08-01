#!/usr/bin/env python3
"""
Test Tool Request Execution Time Tracking

This module tests the enhanced ToolRequest model and log_tool_request endpoint
to ensure accurate millisecond-precision timing data storage and retrieval.
"""

import tempfile
import uuid
from pathlib import Path

import pytest

from session_notes.server import (
    ToolRequest,
    get_agent_directory,
    get_session,
    load_json_data,
    log_tool_request,
    start_session,
)


@pytest.fixture
def temp_session_notes_dir(monkeypatch):
    """Create temporary session notes directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_session_notes_path = Path(temp_dir) / "session-notes"
        temp_session_notes_path.mkdir(exist_ok=True)
        monkeypatch.setattr(
            "session_notes.server.CLAUDE_SESSION_NOTES_DIR",
            str(temp_session_notes_path),
        )
        yield temp_session_notes_path


class TestToolRequestExecutionTime:
    """Test suite for tool request execution time tracking"""

    def test_tool_request_model_has_execution_time_field(self):
        """Test that ToolRequest model includes execution_time field"""
        # Create a ToolRequest with execution time
        tool_request = ToolRequest(
            tool_name="test_tool",
            available=True,
            parameters={"param1": "value1"},
            success=True,
            timestamp="2025-08-01T15:30:00Z",
            execution_time=125.5,
        )

        # Verify execution_time field is present and correct
        assert tool_request.execution_time == 125.5
        assert hasattr(tool_request, "execution_time")

    def test_tool_request_model_execution_time_optional(self):
        """Test that execution_time field is optional in ToolRequest model"""
        # Create a ToolRequest without execution time
        tool_request = ToolRequest(
            tool_name="test_tool",
            available=True,
            parameters={"param1": "value1"},
            success=True,
            timestamp="2025-08-01T15:30:00Z",
        )

        # Verify execution_time defaults to None
        assert tool_request.execution_time is None

    def test_tool_request_model_serialization_with_execution_time(self):
        """Test that ToolRequest model correctly serializes with execution_time"""
        tool_request = ToolRequest(
            tool_name="test_tool",
            available=True,
            parameters={"param1": "value1"},
            success=True,
            timestamp="2025-08-01T15:30:00Z",
            execution_time=250.75,
        )

        # Serialize to dict
        data = tool_request.model_dump()

        # Verify all fields are present
        assert data["tool_name"] == "test_tool"
        assert data["available"] is True
        assert data["parameters"] == {"param1": "value1"}
        assert data["success"] is True
        assert data["timestamp"] == "2025-08-01T15:30:00Z"
        assert data["execution_time"] == 250.75

    def test_log_tool_request_with_execution_time(self, temp_session_notes_dir):
        """Test logging tool request with execution time data"""
        # Start a session
        session_id = str(uuid.uuid4())
        start_session(session_id)

        agent_id = "test_agent"
        tool_name = "test_tool"
        execution_time = 175.25

        # Log tool request with execution time
        result = log_tool_request(
            session_id=session_id,
            agent_id=agent_id,
            tool_name=tool_name,
            available=True,
            parameters={"param1": "value1", "param2": 42},
            success=True,
            execution_time=execution_time,
        )

        # Verify successful logging
        assert "Logged tool request" in result
        assert agent_id in result
        assert tool_name in result

        # Verify data is stored correctly
        agent_dir = get_agent_directory(session_id, agent_id)
        tools_file = agent_dir / "tools.json"
        assert tools_file.exists()

        tools_data = load_json_data(tools_file, [])
        assert len(tools_data) == 1

        tool_request = tools_data[0]
        assert tool_request["tool_name"] == tool_name
        assert tool_request["available"] is True
        assert tool_request["success"] is True
        assert tool_request["execution_time"] == execution_time
        assert tool_request["parameters"] == {"param1": "value1", "param2": 42}
        assert "timestamp" in tool_request

    def test_log_tool_request_without_execution_time(self, temp_session_notes_dir):
        """Test logging tool request without execution time (backward compatibility)"""
        # Start a session
        session_id = str(uuid.uuid4())
        start_session(session_id)

        agent_id = "test_agent"
        tool_name = "test_tool"

        # Log tool request without execution time
        result = log_tool_request(
            session_id=session_id,
            agent_id=agent_id,
            tool_name=tool_name,
            available=True,
            parameters={"param1": "value1"},
            success=True,
        )

        # Verify successful logging
        assert "Logged tool request" in result

        # Verify data is stored correctly with None execution_time
        agent_dir = get_agent_directory(session_id, agent_id)
        tools_file = agent_dir / "tools.json"
        assert tools_file.exists()

        tools_data = load_json_data(tools_file, [])
        assert len(tools_data) == 1

        tool_request = tools_data[0]
        assert tool_request["tool_name"] == tool_name
        assert tool_request["available"] is True
        assert tool_request["success"] is True
        assert tool_request["execution_time"] is None
        assert tool_request["parameters"] == {"param1": "value1"}

    def test_log_multiple_tool_requests_with_timing(self, temp_session_notes_dir):
        """Test logging multiple tool requests with different execution times"""
        # Start a session
        session_id = str(uuid.uuid4())
        start_session(session_id)

        agent_id = "test_agent"

        # Log multiple tool requests with different execution times
        tool_requests = [
            ("tool_a", 50.25, True),
            ("tool_b", 125.75, False),
            ("tool_c", 300.0, True),
            ("tool_d", None, True),  # No execution time
        ]

        for tool_name, exec_time, available in tool_requests:
            log_tool_request(
                session_id=session_id,
                agent_id=agent_id,
                tool_name=tool_name,
                available=available,
                success=available,
                execution_time=exec_time,
            )

        # Verify all requests are stored correctly
        agent_dir = get_agent_directory(session_id, agent_id)
        tools_file = agent_dir / "tools.json"
        tools_data = load_json_data(tools_file, [])

        assert len(tools_data) == 4

        # Verify each tool request has correct execution time
        for i, (expected_tool, expected_time, expected_available) in enumerate(
            tool_requests
        ):
            tool_request = tools_data[i]
            assert tool_request["tool_name"] == expected_tool
            assert tool_request["available"] == expected_available
            assert tool_request["execution_time"] == expected_time

    def test_millisecond_precision_execution_time(self, temp_session_notes_dir):
        """Test that execution time supports millisecond precision"""
        # Start a session
        session_id = str(uuid.uuid4())
        start_session(session_id)

        agent_id = "test_agent"
        tool_name = "precision_tool"

        # Test various millisecond precision values
        precision_values = [
            0.001,  # 1 microsecond = 0.001 ms
            1.5,  # 1.5 milliseconds
            10.123,  # 10.123 milliseconds
            1000.999,  # Nearly 1001 milliseconds
            5432.1234,  # High precision value
        ]

        for exec_time in precision_values:
            log_tool_request(
                session_id=session_id,
                agent_id=agent_id,
                tool_name=f"{tool_name}_{exec_time}",
                available=True,
                success=True,
                execution_time=exec_time,
            )

        # Verify precision is maintained
        agent_dir = get_agent_directory(session_id, agent_id)
        tools_file = agent_dir / "tools.json"
        tools_data = load_json_data(tools_file, [])

        assert len(tools_data) == len(precision_values)

        for i, expected_time in enumerate(precision_values):
            tool_request = tools_data[i]
            assert tool_request["execution_time"] == expected_time

    def test_tool_request_timing_with_failed_requests(self, temp_session_notes_dir):
        """Test execution time tracking for failed tool requests"""
        # Start a session
        session_id = str(uuid.uuid4())
        start_session(session_id)

        agent_id = "test_agent"

        # Log failed tool requests with execution times
        failed_requests = [
            ("missing_tool_1", 25.5, False, False),  # Tool not available, failed
            ("broken_tool_2", 150.25, True, False),  # Tool available, but failed
            ("timeout_tool_3", 5000.0, True, False),  # Tool available, but timed out
        ]

        for tool_name, exec_time, available, success in failed_requests:
            log_tool_request(
                session_id=session_id,
                agent_id=agent_id,
                tool_name=tool_name,
                available=available,
                success=success,
                execution_time=exec_time,
            )

        # Verify failed requests are logged with timing data
        agent_dir = get_agent_directory(session_id, agent_id)
        tools_file = agent_dir / "tools.json"
        tools_data = load_json_data(tools_file, [])

        assert len(tools_data) == 3

        for i, (
            expected_tool,
            expected_time,
            expected_available,
            expected_success,
        ) in enumerate(failed_requests):
            tool_request = tools_data[i]
            assert tool_request["tool_name"] == expected_tool
            assert tool_request["available"] == expected_available
            assert tool_request["success"] == expected_success
            assert tool_request["execution_time"] == expected_time

    def test_session_data_includes_tool_timing(self, temp_session_notes_dir):
        """Test that session data retrieval includes tool request timing"""
        # Start a session
        session_id = str(uuid.uuid4())
        start_session(session_id)

        agent_id = "timing_agent"

        # Log tool requests with various timing data
        log_tool_request(
            session_id=session_id,
            agent_id=agent_id,
            tool_name="fast_tool",
            available=True,
            success=True,
            execution_time=10.5,
        )

        log_tool_request(
            session_id=session_id,
            agent_id=agent_id,
            tool_name="slow_tool",
            available=True,
            success=True,
            execution_time=2500.75,
        )

        # Retrieve session data
        session_data = get_session(session_id)

        # Verify session includes agent tool data with timing
        assert "agents" in session_data
        assert agent_id in session_data["agents"]

        agent_data = session_data["agents"][agent_id]
        assert "tool_requests" in agent_data

        tool_requests = agent_data["tool_requests"]
        assert len(tool_requests) == 2

        # Verify timing data is present
        fast_tool = next(
            req for req in tool_requests if req["tool_name"] == "fast_tool"
        )
        slow_tool = next(
            req for req in tool_requests if req["tool_name"] == "slow_tool"
        )

        assert fast_tool["execution_time"] == 10.5
        assert slow_tool["execution_time"] == 2500.75

    def test_zero_execution_time_handling(self, temp_session_notes_dir):
        """Test handling of zero execution time values"""
        # Start a session
        session_id = str(uuid.uuid4())
        start_session(session_id)

        agent_id = "test_agent"

        # Log tool request with zero execution time
        log_tool_request(
            session_id=session_id,
            agent_id=agent_id,
            tool_name="instant_tool",
            available=True,
            success=True,
            execution_time=0.0,
        )

        # Verify zero execution time is stored correctly
        agent_dir = get_agent_directory(session_id, agent_id)
        tools_file = agent_dir / "tools.json"
        tools_data = load_json_data(tools_file, [])

        assert len(tools_data) == 1
        tool_request = tools_data[0]
        assert tool_request["execution_time"] == 0.0
        assert tool_request["tool_name"] == "instant_tool"

    def test_negative_execution_time_handling(self, temp_session_notes_dir):
        """Test handling of negative execution time values (edge case)"""
        # Start a session
        session_id = str(uuid.uuid4())
        start_session(session_id)

        agent_id = "test_agent"

        # Log tool request with negative execution time (should be allowed for edge cases)
        log_tool_request(
            session_id=session_id,
            agent_id=agent_id,
            tool_name="negative_time_tool",
            available=True,
            success=True,
            execution_time=-1.0,
        )

        # Verify negative execution time is stored (no validation constraint)
        agent_dir = get_agent_directory(session_id, agent_id)
        tools_file = agent_dir / "tools.json"
        tools_data = load_json_data(tools_file, [])

        assert len(tools_data) == 1
        tool_request = tools_data[0]
        assert tool_request["execution_time"] == -1.0
        assert tool_request["tool_name"] == "negative_time_tool"

    def test_large_execution_time_values(self, temp_session_notes_dir):
        """Test handling of large execution time values"""
        # Start a session
        session_id = str(uuid.uuid4())
        start_session(session_id)

        agent_id = "test_agent"

        # Log tool request with very large execution time
        large_time = 999999.999
        log_tool_request(
            session_id=session_id,
            agent_id=agent_id,
            tool_name="long_running_tool",
            available=True,
            success=True,
            execution_time=large_time,
        )

        # Verify large execution time is stored correctly
        agent_dir = get_agent_directory(session_id, agent_id)
        tools_file = agent_dir / "tools.json"
        tools_data = load_json_data(tools_file, [])

        assert len(tools_data) == 1
        tool_request = tools_data[0]
        assert tool_request["execution_time"] == large_time
        assert tool_request["tool_name"] == "long_running_tool"
