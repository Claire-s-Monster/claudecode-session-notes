#!/usr/bin/env python3
"""
Tests for the file-based storage layer implementation.

This test suite validates the core storage utilities, directory creation,
and JSON file operations for the session-notes MCP server.
"""

import json
import tempfile
import uuid
from pathlib import Path
from unittest import TestCase

import pytest

# Import the storage utilities from the server module
from session_notes.server import (
    ensure_directory,
    get_agent_directory,
    get_session_directory,
    load_json_data,
    save_json_data,
)


class TestStorageUtilities(TestCase):
    """Test suite for core storage utility functions."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        # Change to temp directory for testing
        import os

        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        import os
        import shutil

        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ensure_directory_creates_new_directory(self):
        """Test that ensure_directory creates a new directory."""
        test_path = Path(self.temp_dir) / "test_dir" / "nested" / "deep"

        # Verify directory doesn't exist
        self.assertFalse(test_path.exists())

        # Create directory
        ensure_directory(test_path)

        # Verify directory was created
        self.assertTrue(test_path.exists())
        self.assertTrue(test_path.is_dir())

    def test_ensure_directory_handles_existing_directory(self):
        """Test that ensure_directory handles existing directories without error."""
        test_path = Path(self.temp_dir) / "existing_dir"
        test_path.mkdir(parents=True, exist_ok=True)

        # Verify directory exists
        self.assertTrue(test_path.exists())

        # Should not raise error
        ensure_directory(test_path)

        # Directory should still exist
        self.assertTrue(test_path.exists())
        self.assertTrue(test_path.is_dir())

    def test_get_session_directory_returns_correct_path(self):
        """Test that get_session_directory returns the correct path structure."""
        session_id = "test-session-123"
        expected_path = Path(".claude/session-notes") / session_id

        result_path = get_session_directory(session_id)

        self.assertEqual(result_path, expected_path)
        self.assertIsInstance(result_path, Path)

    def test_get_agent_directory_returns_correct_path(self):
        """Test that get_agent_directory returns the correct nested path structure."""
        session_id = "test-session-123"
        agent_id = "test-agent-456"
        expected_path = Path(".claude/session-notes") / session_id / "agents" / agent_id

        result_path = get_agent_directory(session_id, agent_id)

        self.assertEqual(result_path, expected_path)
        self.assertIsInstance(result_path, Path)

    def test_save_json_data_creates_file_and_directories(self):
        """Test that save_json_data creates necessary directories and saves data."""
        test_data = {"test_key": "test_value", "number": 42, "nested": {"data": True}}
        file_path = Path(self.temp_dir) / "nested" / "dirs" / "test.json"

        # Verify file doesn't exist
        self.assertFalse(file_path.exists())

        # Save data
        save_json_data(file_path, test_data)

        # Verify file was created
        self.assertTrue(file_path.exists())
        self.assertTrue(file_path.is_file())

        # Verify data is correct
        with open(file_path, encoding="utf-8") as f:
            loaded_data = json.load(f)

        self.assertEqual(loaded_data, test_data)

    def test_save_json_data_formats_properly(self):
        """Test that save_json_data formats JSON with proper indentation."""
        test_data = {"formatted": True, "indented": {"nested": "data"}}
        file_path = Path(self.temp_dir) / "formatted.json"

        save_json_data(file_path, test_data)

        # Read raw content to verify formatting
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Should be formatted with indentation
        self.assertIn("  ", content)  # Should have indentation
        self.assertIn("\n", content)  # Should have newlines

    def test_load_json_data_loads_existing_file(self):
        """Test that load_json_data correctly loads existing JSON files."""
        test_data = {"loaded": True, "value": 123}
        file_path = Path(self.temp_dir) / "load_test.json"

        # Create test file
        save_json_data(file_path, test_data)

        # Load data
        loaded_data = load_json_data(file_path)

        self.assertEqual(loaded_data, test_data)

    def test_load_json_data_returns_default_for_missing_file(self):
        """Test that load_json_data returns default value for missing files."""
        file_path = Path(self.temp_dir) / "nonexistent.json"
        default_value = {"default": True}

        # Verify file doesn't exist
        self.assertFalse(file_path.exists())

        # Load with default
        result = load_json_data(file_path, default_value)

        self.assertEqual(result, default_value)

    def test_load_json_data_handles_invalid_json(self):
        """Test that load_json_data handles invalid JSON gracefully."""
        file_path = Path(self.temp_dir) / "invalid.json"
        default_value = {"fallback": True}

        # Create invalid JSON file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json content")

        # Should return default value
        result = load_json_data(file_path, default_value)

        self.assertEqual(result, default_value)

    def test_base_storage_directory_creation(self):
        """Test that the base .claude/session-notes directory is created correctly."""
        session_id = str(uuid.uuid4())
        session_dir = get_session_directory(session_id)

        # Verify base directory doesn't exist yet
        base_dir = Path(".claude/session-notes")
        self.assertFalse(base_dir.exists())

        # Create session directory
        ensure_directory(session_dir)

        # Verify base directory was created
        self.assertTrue(base_dir.exists())
        self.assertTrue(base_dir.is_dir())

        # Verify session directory was created
        self.assertTrue(session_dir.exists())
        self.assertTrue(session_dir.is_dir())


class TestIntegratedStorageWorkflow(TestCase):
    """Integration tests for complete storage workflows."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        import os
        import shutil

        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_session_agent_workflow(self):
        """Test the complete workflow of creating session and agent directories."""
        session_id = "workflow-session-123"
        agent_id = "workflow-agent-456"

        # 1. Create session directory
        session_dir = get_session_directory(session_id)
        ensure_directory(session_dir)

        # 2. Create session.json
        session_data = {
            "session_id": session_id,
            "timestamp": "2025-07-31T02:00:00.000Z",
            "status": "active",
        }
        session_file = session_dir / "session.json"
        save_json_data(session_file, session_data)

        # 3. Create agent directory
        agent_dir = get_agent_directory(session_id, agent_id)
        ensure_directory(agent_dir)

        # 4. Create execution.json for agent
        execution_data = {"agent_id": agent_id, "executions": []}
        execution_file = agent_dir / "execution.json"
        save_json_data(execution_file, execution_data)

        # Verify complete structure
        self.assertTrue(session_dir.exists())
        self.assertTrue(session_file.exists())
        self.assertTrue(agent_dir.exists())
        self.assertTrue(execution_file.exists())

        # Verify data integrity
        loaded_session = load_json_data(session_file)
        loaded_execution = load_json_data(execution_file)

        self.assertEqual(loaded_session, session_data)
        self.assertEqual(loaded_execution, execution_data)

    def test_multiple_agents_in_session(self):
        """Test creating multiple agents within the same session."""
        session_id = "multi-agent-session"
        agent_ids = ["agent-1", "agent-2", "agent-3"]

        # Create session directory
        session_dir = get_session_directory(session_id)
        ensure_directory(session_dir)

        # Create multiple agent directories
        for agent_id in agent_ids:
            agent_dir = get_agent_directory(session_id, agent_id)
            ensure_directory(agent_dir)

            # Create execution.json for each agent
            execution_file = agent_dir / "execution.json"
            save_json_data(execution_file, {"agent_id": agent_id, "executions": []})

        # Verify all agents were created
        agents_dir = session_dir / "agents"
        self.assertTrue(agents_dir.exists())

        created_agents = [d.name for d in agents_dir.iterdir() if d.is_dir()]
        self.assertEqual(set(created_agents), set(agent_ids))

        # Verify each agent has execution.json
        for agent_id in agent_ids:
            agent_dir = get_agent_directory(session_id, agent_id)
            execution_file = agent_dir / "execution.json"
            self.assertTrue(execution_file.exists())

            data = load_json_data(execution_file)
            self.assertEqual(data["agent_id"], agent_id)


if __name__ == "__main__":
    pytest.main([__file__])
