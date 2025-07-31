"""
Comprehensive validation tests for Pydantic models.

Tests edge cases, validation errors, and model serialization/deserialization.
"""

import json

import pytest
from pydantic import ValidationError

from session_notes.server import AgentExecution, SessionInfo, ToolRequest


class TestSessionInfoValidation:
    """Test SessionInfo model validation edge cases."""

    def test_session_info_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            SessionInfo()

        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        assert "session_id" in required_fields
        assert "timestamp" in required_fields

    def test_session_info_field_types(self):
        """Test field type validation."""
        base_data = {
            "session_id": "test-session",
            "timestamp": "2024-01-15T10:30:00Z",
        }

        # Test valid duration types
        valid_durations = [300.5, 0, 0.0, None]
        for duration in valid_durations:
            session = SessionInfo(**base_data, duration=duration)
            assert session.duration == duration

        # Test invalid duration type
        with pytest.raises(ValidationError):
            SessionInfo(**base_data, duration="invalid")

        # Test environment field
        valid_envs = [{}, {"key": "value"}, {"nested": {"key": "value"}}]
        for env in valid_envs:
            session = SessionInfo(**base_data, environment=env)
            assert session.environment == env

    def test_session_info_serialization(self):
        """Test model serialization and deserialization."""
        original_data = {
            "session_id": "serialize-test",
            "timestamp": "2024-01-15T10:30:00Z",
            "duration": 1800.5,
            "environment": {"python": "3.12", "nested": {"key": "value"}},
            "status": "completed",
        }

        # Create model from data
        session = SessionInfo(**original_data)

        # Serialize to dict
        serialized = session.model_dump()
        assert serialized == original_data

        # Test JSON serialization
        json_str = session.model_dump_json()
        loaded_data = json.loads(json_str)
        assert loaded_data == original_data

        # Create new model from serialized data
        new_session = SessionInfo(**serialized)
        assert new_session == session

    def test_session_info_field_constraints(self):
        """Test field constraint validation."""
        base_data = {
            "session_id": "constraint-test",
            "timestamp": "2024-01-15T10:30:00Z",
        }

        # Test that empty session_id is actually allowed (Pydantic allows empty strings)
        session = SessionInfo(**{**base_data, "session_id": ""})
        assert session.session_id == ""

        # Test that empty timestamp is actually allowed (Pydantic allows empty strings)
        session = SessionInfo(**{**base_data, "timestamp": ""})
        assert session.timestamp == ""

        # Test negative duration should be allowed
        session = SessionInfo(**base_data, duration=-100.0)
        assert session.duration == -100.0


class TestAgentExecutionValidation:
    """Test AgentExecution model validation edge cases."""

    def test_agent_execution_required_fields(self):
        """Test required field validation."""
        with pytest.raises(ValidationError) as exc_info:
            AgentExecution()

        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        expected_required = {"agent_id", "agent_type", "timestamp", "action"}
        assert required_fields == expected_required

    def test_agent_execution_optional_fields(self):
        """Test optional field defaults."""
        minimal_data = {
            "agent_id": "test-agent",
            "agent_type": "test-type",
            "timestamp": "2024-01-15T10:30:00Z",
            "action": "test-action",
        }

        execution = AgentExecution(**minimal_data)
        assert execution.parameters == {}
        assert execution.result is None
        assert execution.execution_time is None

    def test_agent_execution_complex_data(self):
        """Test with complex parameter and result data."""
        complex_data = {
            "agent_id": "complex-agent",
            "agent_type": "complex-type",
            "timestamp": "2024-01-15T10:30:00Z",
            "action": "complex-action",
            "parameters": {
                "nested": {
                    "deep": {"values": [1, 2, 3]},
                    "list": ["a", "b", {"inner": "value"}],
                },
                "numbers": 42,
                "boolean": True,
            },
            "result": {
                "status": "success",
                "data": {"processed": 100, "errors": []},
                "metadata": {"execution_id": "exec-123"},
            },
            "execution_time": 2500.75,
        }

        execution = AgentExecution(**complex_data)
        assert execution.parameters == complex_data["parameters"]
        assert execution.result == complex_data["result"]
        assert execution.execution_time == 2500.75

    def test_agent_execution_serialization(self):
        """Test serialization with complex nested data."""
        data = {
            "agent_id": "serialize-agent",
            "agent_type": "serializer",
            "timestamp": "2024-01-15T10:30:00Z",
            "action": "serialize",
            "parameters": {"list": [1, "two", {"three": 3}]},
            "result": {"nested": {"data": True}},
            "execution_time": 1000.5,
        }

        execution = AgentExecution(**data)
        serialized = execution.model_dump()
        assert serialized == data

        # Test round-trip
        new_execution = AgentExecution(**serialized)
        assert new_execution == execution

    def test_agent_execution_type_validation(self):
        """Test field type validation."""
        base_data = {
            "agent_id": "type-test",
            "agent_type": "tester",
            "timestamp": "2024-01-15T10:30:00Z",
            "action": "test",
        }

        # Test execution_time type validation
        valid_times = [0, 0.0, 1000.5, None]
        for time_val in valid_times:
            execution = AgentExecution(**base_data, execution_time=time_val)
            assert execution.execution_time == time_val

        # Test invalid execution_time
        with pytest.raises(ValidationError):
            AgentExecution(**base_data, execution_time="invalid")


class TestToolRequestValidation:
    """Test ToolRequest model validation edge cases."""

    def test_tool_request_required_fields(self):
        """Test required field validation."""
        with pytest.raises(ValidationError) as exc_info:
            ToolRequest()

        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        expected_required = {"tool_name", "available", "success", "timestamp"}
        assert required_fields == expected_required

    def test_tool_request_boolean_fields(self):
        """Test boolean field validation."""
        base_data = {
            "tool_name": "test-tool",
            "timestamp": "2024-01-15T10:30:00Z",
        }

        # Test valid boolean combinations
        boolean_combinations = [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ]

        for available, success in boolean_combinations:
            request = ToolRequest(**base_data, available=available, success=success)
            assert request.available is available
            assert request.success is success

        # Note: Pydantic might coerce string "true"/"false" to boolean,
        # so let's test with clearly invalid values
        with pytest.raises(ValidationError):
            ToolRequest(**base_data, available=None, success=True)

        with pytest.raises(ValidationError):
            ToolRequest(**base_data, available=True, success=None)

    def test_tool_request_parameters_validation(self):
        """Test parameters field validation."""
        base_data = {
            "tool_name": "param-tool",
            "available": True,
            "success": True,
            "timestamp": "2024-01-15T10:30:00Z",
        }

        # Test various parameter types
        parameter_tests = [
            {},
            {"simple": "value"},
            {"number": 42, "boolean": True, "null": None},
            {"nested": {"deep": {"value": "test"}}},
            {"list": [1, "two", {"three": 3}]},
            {"complex": {"mixed": [1, {"nested": True}, "string"]}},
        ]

        for params in parameter_tests:
            request = ToolRequest(**base_data, parameters=params)
            assert request.parameters == params

    def test_tool_request_serialization(self):
        """Test serialization with various data types."""
        data = {
            "tool_name": "serialization-tool",
            "available": True,
            "success": False,
            "timestamp": "2024-01-15T10:30:00Z",
            "parameters": {
                "config": {"timeout": 30, "retries": 3},
                "files": ["file1.py", "file2.py"],
                "options": {"verbose": True, "dry_run": False},
            },
        }

        request = ToolRequest(**data)
        serialized = request.model_dump()
        assert serialized == data

        # Test JSON serialization
        json_str = request.model_dump_json()
        loaded_data = json.loads(json_str)
        assert loaded_data == data

        # Test round-trip
        new_request = ToolRequest(**serialized)
        assert new_request == request

    def test_tool_request_edge_cases(self):
        """Test edge cases and boundary conditions."""
        base_data = {
            "tool_name": "edge-tool",
            "available": True,
            "success": True,
            "timestamp": "2024-01-15T10:30:00Z",
        }

        # Test empty tool name (Pydantic allows empty strings)
        request = ToolRequest(**{**base_data, "tool_name": ""})
        assert request.tool_name == ""

        # Test empty timestamp (Pydantic allows empty strings)
        request = ToolRequest(**{**base_data, "timestamp": ""})
        assert request.timestamp == ""

        # Test very long tool name (should work)
        long_name = "a" * 1000
        request = ToolRequest(**{**base_data, "tool_name": long_name})
        assert request.tool_name == long_name

        # Test special characters in tool name
        special_name = "tool-name_with.special@chars#123"
        request = ToolRequest(**{**base_data, "tool_name": special_name})
        assert request.tool_name == special_name


class TestModelComparison:
    """Test model equality and comparison operations."""

    def test_session_info_equality(self):
        """Test SessionInfo equality comparison."""
        data = {
            "session_id": "test-session",
            "timestamp": "2024-01-15T10:30:00Z",
            "duration": 300.0,
            "environment": {"key": "value"},
            "status": "active",
        }

        session1 = SessionInfo(**data)
        session2 = SessionInfo(**data)
        session3 = SessionInfo(**{**data, "duration": 400.0})

        assert session1 == session2
        assert session1 != session3
        assert session2 != session3

    def test_agent_execution_equality(self):
        """Test AgentExecution equality comparison."""
        data = {
            "agent_id": "test-agent",
            "agent_type": "test-type",
            "timestamp": "2024-01-15T10:30:00Z",
            "action": "test-action",
            "parameters": {"key": "value"},
            "result": {"status": "success"},
            "execution_time": 1000.0,
        }

        exec1 = AgentExecution(**data)
        exec2 = AgentExecution(**data)
        exec3 = AgentExecution(**{**data, "action": "different-action"})

        assert exec1 == exec2
        assert exec1 != exec3
        assert exec2 != exec3

    def test_tool_request_equality(self):
        """Test ToolRequest equality comparison."""
        data = {
            "tool_name": "test-tool",
            "available": True,
            "success": True,
            "timestamp": "2024-01-15T10:30:00Z",
            "parameters": {"config": "default"},
        }

        req1 = ToolRequest(**data)
        req2 = ToolRequest(**data)
        req3 = ToolRequest(**{**data, "available": False})

        assert req1 == req2
        assert req1 != req3
        assert req2 != req3

    def test_cross_model_inequality(self):
        """Test that different model types are not equal."""
        session = SessionInfo(session_id="test", timestamp="2024-01-15T10:30:00Z")

        execution = AgentExecution(
            agent_id="test",
            agent_type="test",
            timestamp="2024-01-15T10:30:00Z",
            action="test",
        )

        tool_request = ToolRequest(
            tool_name="test",
            available=True,
            success=True,
            timestamp="2024-01-15T10:30:00Z",
        )

        # Different model types should not be equal
        assert session != execution
        assert session != tool_request
        assert execution != tool_request

        # Test against non-model objects
        assert session != "string"
        assert execution != 42
        assert tool_request is not None


class TestModelInvalidData:
    """Test models with various invalid data scenarios."""

    def test_invalid_timestamp_formats(self):
        """Test handling of invalid timestamp formats."""
        base_session_data = {"session_id": "test"}
        base_execution_data = {
            "agent_id": "test",
            "agent_type": "test",
            "action": "test",
        }
        base_tool_data = {"tool_name": "test", "available": True, "success": True}

        # Note: Pydantic with basic string fields doesn't validate timestamp format
        # We're using str fields, not datetime fields, so most strings are valid
        # Only None values should fail for required fields

        # Test None values (should fail for required fields)
        with pytest.raises(ValidationError):
            SessionInfo(**base_session_data, timestamp=None)

        with pytest.raises(ValidationError):
            AgentExecution(**base_execution_data, timestamp=None)

        with pytest.raises(ValidationError):
            ToolRequest(**base_tool_data, timestamp=None)

        # Test that string timestamps are accepted (even if malformed)
        # This is expected behavior since we use str fields
        valid_session = SessionInfo(**base_session_data, timestamp="invalid-format")
        assert valid_session.timestamp == "invalid-format"

    def test_none_values_in_required_fields(self):
        """Test that None values in required fields raise validation errors."""
        # SessionInfo with None values
        with pytest.raises(ValidationError):
            SessionInfo(session_id=None, timestamp="2024-01-15T10:30:00Z")

        with pytest.raises(ValidationError):
            SessionInfo(session_id="test", timestamp=None)

        # AgentExecution with None values
        with pytest.raises(ValidationError):
            AgentExecution(
                agent_id=None,
                agent_type="test",
                timestamp="2024-01-15T10:30:00Z",
                action="test",
            )

        # ToolRequest with None values
        with pytest.raises(ValidationError):
            ToolRequest(
                tool_name=None,
                available=True,
                success=True,
                timestamp="2024-01-15T10:30:00Z",
            )

    def test_extreme_values(self):
        """Test models with extreme values."""
        # Very large duration
        session = SessionInfo(
            session_id="extreme",
            timestamp="2024-01-15T10:30:00Z",
            duration=float("inf"),
        )
        assert session.duration == float("inf")

        # Very large execution time
        execution = AgentExecution(
            agent_id="extreme",
            agent_type="extreme",
            timestamp="2024-01-15T10:30:00Z",
            action="extreme",
            execution_time=1e10,
        )
        assert execution.execution_time == 1e10

        # Extremely long strings
        long_string = "x" * 100000
        session = SessionInfo(session_id=long_string, timestamp="2024-01-15T10:30:00Z")
        assert len(session.session_id) == 100000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
