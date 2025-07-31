#!/usr/bin/env python3
"""
Tests for session directory and session.json creation functionality.

This test suite validates that the start_session function correctly creates
the session directory structure and initializes session.json files.
"""

import json
import tempfile
import uuid
from pathlib import Path
from unittest import TestCase

import pytest


class TestSessionCreation(TestCase):
    """Test suite for session directory and session.json creation."""

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

    def test_start_session_creates_directory_structure(self):
        """Test that start_session creates the correct directory structure."""
        # Import here to avoid the fastmcp import issue in test collection
        from session_notes.server import start_session, get_session_directory

        session_id = "test-session-123"

        # Verify directory doesn't exist initially
        session_dir = get_session_directory(session_id)
        self.assertFalse(session_dir.exists())

        # Start session
        result = start_session(session_id)

        # Verify directory was created
        self.assertTrue(session_dir.exists())
        self.assertTrue(session_dir.is_dir())

        # Verify return message
        self.assertIn(session_id, result)
        self.assertIn("started successfully", result.lower())

    def test_start_session_creates_session_json(self):
        """Test that start_session creates a properly formatted session.json file."""
        from session_notes.server import start_session, get_session_directory

        session_id = "test-session-456"
        environment_info = {"platform": "linux", "version": "1.0"}

        # Start session with environment info
        start_session(session_id, environment_info)

        # Verify session.json was created
        session_dir = get_session_directory(session_id)
        session_file = session_dir / "session.json"

        self.assertTrue(session_file.exists())
        self.assertTrue(session_file.is_file())

        # Load and verify session data
        with open(session_file, encoding="utf-8") as f:
            session_data = json.load(f)

        # Verify required fields
        self.assertEqual(session_data["session_id"], session_id)
        self.assertEqual(session_data["status"], "active")
        self.assertEqual(session_data["environment"], environment_info)
        self.assertIsNone(session_data["duration"])

        # Verify timestamp is present and valid ISO format
        self.assertIn("timestamp", session_data)
        # This should not raise an exception if timestamp is valid ISO format
        from datetime import datetime

        datetime.fromisoformat(session_data["timestamp"].replace("Z", "+00:00"))

    def test_start_session_with_auto_generated_id(self):
        """Test that start_session generates a session ID when none provided."""
        from session_notes.server import start_session

        # Start session without providing session_id
        result = start_session()

        # Extract session ID from result message
        # Format: "Session {session_id} started successfully"
        session_id = result.split("Session ")[1].split(" started")[0]

        # Verify it's a valid UUID format
        uuid.UUID(session_id)  # This will raise ValueError if not valid UUID

        # Verify directory was created with the generated ID
        from session_notes.server import get_session_directory

        session_dir = get_session_directory(session_id)
        self.assertTrue(session_dir.exists())

        # Verify session.json exists
        session_file = session_dir / "session.json"
        self.assertTrue(session_file.exists())

    def test_start_session_with_empty_environment(self):
        """Test that start_session handles empty or None environment info."""
        from session_notes.server import start_session, get_session_directory

        session_id = "test-session-empty-env"

        # Start session with None environment
        start_session(session_id, None)

        # Verify session.json was created with empty environment
        session_dir = get_session_directory(session_id)
        session_file = session_dir / "session.json"

        with open(session_file, encoding="utf-8") as f:
            session_data = json.load(f)

        self.assertEqual(session_data["environment"], {})

    def test_multiple_sessions_creation(self):
        """Test creating multiple sessions with different IDs."""
        from session_notes.server import start_session, get_session_directory

        session_ids = ["session-1", "session-2", "session-3"]

        # Create multiple sessions
        for session_id in session_ids:
            start_session(session_id, {"session": session_id})

        # Verify all sessions were created
        for session_id in session_ids:
            session_dir = get_session_directory(session_id)
            session_file = session_dir / "session.json"

            self.assertTrue(session_dir.exists())
            self.assertTrue(session_file.exists())

            # Verify session data is correct
            with open(session_file, encoding="utf-8") as f:
                session_data = json.load(f)

            self.assertEqual(session_data["session_id"], session_id)
            self.assertEqual(session_data["environment"]["session"], session_id)

    def test_base_directory_creation(self):
        """Test that the base .claude/session-notes directory is created."""
        from session_notes.server import start_session

        # Verify base directory doesn't exist initially
        base_dir = Path(".claude/session-notes")
        self.assertFalse(base_dir.exists())

        # Start a session
        start_session("test-base-dir")

        # Verify base directory was created
        self.assertTrue(base_dir.exists())
        self.assertTrue(base_dir.is_dir())

    def test_session_json_formatting(self):
        """Test that session.json is properly formatted with indentation."""
        from session_notes.server import start_session, get_session_directory

        session_id = "test-formatting"
        start_session(session_id, {"nested": {"data": True}})

        # Read raw file content
        session_dir = get_session_directory(session_id)
        session_file = session_dir / "session.json"

        with open(session_file, encoding="utf-8") as f:
            content = f.read()

        # Verify proper JSON formatting
        self.assertIn("  ", content)  # Should have indentation
        self.assertIn("\n", content)  # Should have newlines

        # Verify it's valid JSON
        json.loads(content)  # Should not raise exception


if __name__ == "__main__":
    pytest.main([__file__])
