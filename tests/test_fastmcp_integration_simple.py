"""
Simple FastMCP 2.0 integration tests that focus on working API calls.

Tests basic FastMCP functionality without complex async patterns.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from session_notes.server import app


class TestFastMCPAppConfiguration:
    """Test basic FastMCP application configuration."""

    def test_app_metadata(self):
        """Test that FastMCP app has correct metadata."""
        assert app.name == "session-notes"
        assert hasattr(app, "name")

    def test_app_initialization(self):
        """Test that app initializes correctly."""
        # App should be properly initialized
        assert app is not None
        assert hasattr(app, "name")


class TestBasicMCPCompliance:
    """Test basic MCP protocol compliance."""

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

    def test_direct_tool_calls(self):
        """Test calling tools directly (not through MCP protocol)."""
        from session_notes.server import end_session, start_session

        # Test start_session
        result = start_session.fn("test-session")
        assert isinstance(result, str)
        assert "started successfully" in result

        # Test end_session (will not find session but should return string)
        result = end_session.fn("test-session")
        assert isinstance(result, str)

    def test_direct_resource_calls(self):
        """Test calling resources directly."""
        from session_notes.server import get_session, list_sessions

        # Test get_session (non-existent session)
        result = get_session.fn("nonexistent")
        assert isinstance(result, dict)
        assert "error" in result

        # Test list_sessions (empty list)
        result = list_sessions.fn()
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
