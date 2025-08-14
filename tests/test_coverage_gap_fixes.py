"""
Test cases specifically designed to close coverage gaps and reach 88%+ coverage.

This module contains targeted tests for uncovered lines identified in coverage analysis,
focusing on meaningful test scenarios that improve both coverage and code quality.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from session_notes.server import (
    _update_session_metadata_impl,
    _start_session_impl,
    start_session,
    load_json_data,
)


class TestCoverageGapFixes:
    """Test cases targeting specific coverage gaps."""

    def test_update_session_metadata_nonexistent_session(self):
        """Test updating metadata for a non-existent session (covers line 611)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "session_notes.server.CLAUDE_SESSION_NOTES_DIR",
                f"{temp_dir}/.claude/session-notes",
            ):
                # Try to update metadata for a session that doesn't exist
                result = _update_session_metadata_impl(
                    session_id="nonexistent-session",
                    metadata_updates={"test": "data"},
                    merge_environment=True,
                )

                # Should return error message for non-existent session
                assert result == "Session nonexistent-session not found"

    def test_update_session_metadata_no_merge_environment(self):
        """Test metadata update without merging environment metadata (covers line 623)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "session_notes.server.CLAUDE_SESSION_NOTES_DIR",
                f"{temp_dir}/.claude/session-notes",
            ):
                # Start a session first
                session_id = "test-session-no-merge"
                start_result = _start_session_impl(
                    session_id=session_id,
                    environment_info={"initial": "data"},
                    auto_collect_environment=False,
                )
                assert session_id in start_result

                # Update metadata without merging environment data
                result = _update_session_metadata_impl(
                    session_id=session_id,
                    metadata_updates={
                        "custom_key": "custom_value",
                        "environment": {"should": "replace"},
                    },
                    merge_environment=False,
                )

                # Should succeed and return success message
                assert "updated successfully" in result

                # Verify the metadata was set directly without merging
                session_file = (
                    Path(temp_dir)
                    / ".claude"
                    / "session-notes"
                    / session_id
                    / "session.json"
                )
                session_data = load_json_data(session_file)

                # Environment should be replaced, not merged
                assert session_data["environment"]["should"] == "replace"
                assert session_data["custom_key"] == "custom_value"

    def test_fastmcp_tool_wrapper_coverage(self):
        """Test FastMCP tool wrapper functions to increase coverage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "session_notes.server.CLAUDE_SESSION_NOTES_DIR",
                f"{temp_dir}/.claude/session-notes",
            ):
                # Test various FastMCP tool wrapper calls
                session_id = "fastmcp-coverage-session"

                # Test start_session wrapper (covers line 1237 and similar)
                result = start_session(
                    session_id=session_id,
                    environment_info={"tool": "coverage_test"},
                    auto_collect_environment=False,
                )
                assert session_id in result

    def test_metadata_merge_branch_coverage(self):
        """Test specific branch conditions in metadata merging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "session_notes.server.CLAUDE_SESSION_NOTES_DIR",
                f"{temp_dir}/.claude/session-notes",
            ):
                session_id = "branch-coverage-session"

                # Start session with minimal environment
                _start_session_impl(
                    session_id=session_id,
                    environment_info={"minimal": "env"},
                    auto_collect_environment=False,
                )

                # Test the else branch in environment merging (line 623)
                result = _update_session_metadata_impl(
                    session_id=session_id,
                    metadata_updates={
                        "test_key": "test_value",
                        "environment": {"replaced": True},
                    },
                    merge_environment=False,  # This should trigger the else branch
                )

                assert "updated successfully" in result

                # Verify the environment was replaced rather than merged
                session_file = (
                    Path(temp_dir)
                    / ".claude"
                    / "session-notes"
                    / session_id
                    / "session.json"
                )
                session_data = load_json_data(session_file)
                assert session_data["environment"]["replaced"] is True
                assert "minimal" not in session_data["environment"]
