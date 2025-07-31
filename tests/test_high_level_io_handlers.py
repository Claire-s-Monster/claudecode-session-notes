#!/usr/bin/env python3
"""
Tests for high-level JSON data I/O handlers.

This test suite validates the high-level I/O functions that provide
convenient abstractions for reading and writing session and agent data.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

import pytest

# Add src to path
sys.path.insert(0, "src")


class TestHighLevelIOHandlers(TestCase):
    """Test suite for high-level JSON I/O handler functions."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        # Change to temp directory for testing
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_session_json_write_and_read(self):
        """Test writing and reading session JSON data."""
        # Import here to avoid fastmcp import issues
        from session_notes.server import read_session_json, write_session_json

        session_id = "test-session-io"
        filename = "session.json"
        test_data = {
            "session_id": session_id,
            "timestamp": "2025-07-31T02:00:00.000Z",
            "status": "active",
            "environment": {"platform": "linux", "version": "test"},
        }

        # Write session data
        write_session_json(session_id, filename, test_data)

        # Read session data back
        loaded_data = read_session_json(session_id, filename)

        # Verify data integrity
        self.assertEqual(loaded_data, test_data)

        # Verify file was created in correct location
        session_dir = Path(".claude/session-notes") / session_id
        session_file = session_dir / filename
        self.assertTrue(session_file.exists())

    def test_session_json_read_nonexistent_with_default(self):
        """Test reading non-existent session JSON returns default value."""
        from session_notes.server import read_session_json

        session_id = "nonexistent-session"
        filename = "session.json"
        default_value = {"default": True}

        # Read non-existent file
        result = read_session_json(session_id, filename, default_value)

        # Should return default value
        self.assertEqual(result, default_value)

    def test_agent_json_write_and_read(self):
        """Test writing and reading agent JSON data."""
        from session_notes.server import read_agent_json, write_agent_json

        session_id = "test-session-agent-io"
        agent_id = "test-agent-123"
        filename = "execution.json"
        test_data = [
            {
                "agent_id": agent_id,
                "timestamp": "2025-07-31T02:00:00.000Z",
                "action": "test_action",
                "parameters": {"test": "value"},
            }
        ]

        # Write agent data
        write_agent_json(session_id, agent_id, filename, test_data)

        # Read agent data back
        loaded_data = read_agent_json(session_id, agent_id, filename)

        # Verify data integrity
        self.assertEqual(loaded_data, test_data)

        # Verify file was created in correct location
        agent_dir = Path(".claude/session-notes") / session_id / "agents" / agent_id
        agent_file = agent_dir / filename
        self.assertTrue(agent_file.exists())

    def test_agent_json_read_nonexistent_with_default(self):
        """Test reading non-existent agent JSON returns default value."""
        from session_notes.server import read_agent_json

        session_id = "nonexistent-session"
        agent_id = "nonexistent-agent"
        filename = "execution.json"
        default_value = []

        # Read non-existent file
        result = read_agent_json(session_id, agent_id, filename, default_value)

        # Should return default value
        self.assertEqual(result, default_value)

    def test_multiple_agent_files(self):
        """Test handling multiple JSON files for the same agent."""
        from session_notes.server import read_agent_json, write_agent_json

        session_id = "test-session-multi-files"
        agent_id = "test-agent-multi"

        # Write execution.json
        execution_data = [
            {"action": "execute", "timestamp": "2025-07-31T02:00:00.000Z"}
        ]
        write_agent_json(session_id, agent_id, "execution.json", execution_data)

        # Write tools.json
        tools_data = [
            {
                "tool": "editor",
                "available": True,
                "timestamp": "2025-07-31T02:01:00.000Z",
            }
        ]
        write_agent_json(session_id, agent_id, "tools.json", tools_data)

        # Read both files back
        loaded_execution = read_agent_json(session_id, agent_id, "execution.json")
        loaded_tools = read_agent_json(session_id, agent_id, "tools.json")

        # Verify both files contain correct data
        self.assertEqual(loaded_execution, execution_data)
        self.assertEqual(loaded_tools, tools_data)

        # Verify both files exist
        agent_dir = Path(".claude/session-notes") / session_id / "agents" / agent_id
        self.assertTrue((agent_dir / "execution.json").exists())
        self.assertTrue((agent_dir / "tools.json").exists())

    def test_session_exists_function(self):
        """Test session_exists utility function."""
        from session_notes.server import session_exists, write_session_json

        session_id = "test-session-exists"

        # Initially should not exist
        self.assertFalse(session_exists(session_id))

        # Create session by writing data
        write_session_json(session_id, "session.json", {"test": "data"})

        # Now should exist
        self.assertTrue(session_exists(session_id))

    def test_agent_exists_function(self):
        """Test agent_exists utility function."""
        from session_notes.server import agent_exists, write_agent_json

        session_id = "test-session-agent-exists"
        agent_id = "test-agent-exists"

        # Initially should not exist
        self.assertFalse(agent_exists(session_id, agent_id))

        # Create agent by writing data
        write_agent_json(session_id, agent_id, "execution.json", [])

        # Now should exist
        self.assertTrue(agent_exists(session_id, agent_id))

    def test_list_session_agents(self):
        """Test listing all agents within a session."""
        from session_notes.server import list_session_agents, write_agent_json

        session_id = "test-session-list-agents"
        agent_ids = ["agent-1", "agent-2", "agent-3"]

        # Initially should be empty
        agents = list_session_agents(session_id)
        self.assertEqual(agents, [])

        # Create multiple agents
        for agent_id in agent_ids:
            write_agent_json(session_id, agent_id, "execution.json", [])

        # List agents
        agents = list_session_agents(session_id)

        # Should contain all created agents
        self.assertEqual(set(agents), set(agent_ids))

    def test_list_session_agents_nonexistent_session(self):
        """Test listing agents for non-existent session returns empty list."""
        from session_notes.server import list_session_agents

        session_id = "nonexistent-session"

        # Should return empty list
        agents = list_session_agents(session_id)
        self.assertEqual(agents, [])

    def test_json_formatting_consistency(self):
        """Test that high-level handlers maintain consistent JSON formatting."""
        from session_notes.server import write_agent_json, write_session_json

        session_id = "test-formatting-consistency"
        agent_id = "test-agent-formatting"

        # Test data with nested structure
        test_data = {"nested": {"data": True, "array": [1, 2, 3], "string": "test"}}

        # Write via session handler
        write_session_json(session_id, "test.json", test_data)

        # Write via agent handler
        write_agent_json(session_id, agent_id, "test.json", test_data)

        # Read raw content from both files
        session_file = Path(".claude/session-notes") / session_id / "test.json"
        agent_file = (
            Path(".claude/session-notes")
            / session_id
            / "agents"
            / agent_id
            / "test.json"
        )

        with open(session_file, encoding="utf-8") as f:
            session_content = f.read()

        with open(agent_file, encoding="utf-8") as f:
            agent_content = f.read()

        # Both should be properly formatted with indentation
        self.assertIn("  ", session_content)  # Should have indentation
        self.assertIn("  ", agent_content)  # Should have indentation

        # Both should parse to the same data
        session_parsed = json.loads(session_content)
        agent_parsed = json.loads(agent_content)

        self.assertEqual(session_parsed, test_data)
        self.assertEqual(agent_parsed, test_data)

    def test_error_handling_invalid_json(self):
        """Test error handling when reading invalid JSON files."""
        from session_notes.server import read_agent_json, read_session_json

        session_id = "test-error-handling"
        agent_id = "test-agent-error"

        # Create directories manually
        session_dir = Path(".claude/session-notes") / session_id
        agent_dir = session_dir / "agents" / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Create invalid JSON files
        session_file = session_dir / "invalid.json"
        agent_file = agent_dir / "invalid.json"

        with open(session_file, "w") as f:
            f.write("{ invalid json content")

        with open(agent_file, "w") as f:
            f.write("{ also invalid json")

        # Reading should return default values, not raise exceptions
        default_value = {"fallback": True}

        session_result = read_session_json(session_id, "invalid.json", default_value)
        agent_result = read_agent_json(
            session_id, agent_id, "invalid.json", default_value
        )

        self.assertEqual(session_result, default_value)
        self.assertEqual(agent_result, default_value)

    def test_complete_workflow_integration(self):
        """Test complete workflow using high-level I/O handlers."""
        from session_notes.server import (
            agent_exists,
            list_session_agents,
            read_agent_json,
            read_session_json,
            session_exists,
            write_agent_json,
            write_session_json,
        )

        session_id = "test-complete-workflow"

        # 1. Create session
        session_data = {
            "session_id": session_id,
            "timestamp": "2025-07-31T02:00:00.000Z",
            "status": "active",
        }
        write_session_json(session_id, "session.json", session_data)

        # Verify session exists
        self.assertTrue(session_exists(session_id))

        # 2. Create multiple agents
        agents_data = {
            "agent-1": [{"action": "review", "timestamp": "2025-07-31T02:01:00.000Z"}],
            "agent-2": [{"action": "execute", "timestamp": "2025-07-31T02:02:00.000Z"}],
            "agent-3": [{"action": "analyze", "timestamp": "2025-07-31T02:03:00.000Z"}],
        }

        for agent_id, executions in agents_data.items():
            write_agent_json(session_id, agent_id, "execution.json", executions)
            self.assertTrue(agent_exists(session_id, agent_id))

        # 3. Verify all agents are listed
        agents = list_session_agents(session_id)
        self.assertEqual(set(agents), set(agents_data.keys()))

        # 4. Read and verify all data
        loaded_session = read_session_json(session_id, "session.json")
        self.assertEqual(loaded_session, session_data)

        for agent_id, expected_executions in agents_data.items():
            loaded_executions = read_agent_json(session_id, agent_id, "execution.json")
            self.assertEqual(loaded_executions, expected_executions)

        # 5. Update session status
        session_data["status"] = "completed"
        session_data["duration"] = 180.5
        write_session_json(session_id, "session.json", session_data)

        # Verify update
        updated_session = read_session_json(session_id, "session.json")
        self.assertEqual(updated_session["status"], "completed")
        self.assertEqual(updated_session["duration"], 180.5)

        print("✅ Complete workflow integration test passed!")


if __name__ == "__main__":
    pytest.main([__file__])
