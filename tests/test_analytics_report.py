# \!/usr/bin/env python3
"""
Tests for the analytics report endpoint implementation.

This test suite validates the analytics report functionality including tool usage
analysis, missing tools detection, and comprehensive session analytics.
"""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import TestCase

import pytest

# Import the analytics functions and supporting utilities
from session_notes.server import (
    TESTING_MODE,
    _end_session_impl,
    _generate_analytics_report_impl,
    _log_tool_request_impl,
    _register_agent_impl,
    _start_session_impl,
    get_session_directory,
    load_json_data,
    save_json_data,
)


class TestAnalyticsReportGeneration(TestCase):
    """Test suite for analytics report generation functionality."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.temp_dir)

        # Verify we're in testing mode
        self.assertTrue(TESTING_MODE, "Tests should run in TESTING_MODE")

    def tearDown(self):
        """Clean up test environment."""
        import os
        import shutil

        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_sessions_analytics_report(self):
        """Test analytics report generation with no sessions."""
        report = _generate_analytics_report_impl()

        # Verify basic structure
        self.assertIsInstance(report, dict)
        self.assertIn("report_timestamp", report)
        self.assertIn("total_sessions", report)
        self.assertEqual(report["total_sessions"], 0)

        # Verify empty data structures
        self.assertEqual(report["total_tool_requests"], 0)
        self.assertEqual(report["successful_tool_requests"], 0)
        self.assertEqual(report["overall_tool_success_rate"], 0.0)
        self.assertEqual(len(report["frequently_used_tools"]), 0)
        self.assertEqual(report["total_missing_tools"], 0)
        self.assertEqual(report["total_failed_requests"], 0)
        self.assertEqual(len(report["missing_tools"]), 0)
        self.assertEqual(len(report["session_summaries"]), 0)

        # Verify date range
        self.assertIsNone(report["date_range"]["start"])
        self.assertIsNone(report["date_range"]["end"])

    def test_single_session_basic_analytics(self):
        """Test analytics report with a single session containing basic tool usage."""
        # Create a session
        session_id = "test-session-001"

        _start_session_impl(session_id)

        # Register an agent
        agent_id = "test-agent-001"
        _register_agent_impl(session_id, agent_id, "test-agent")

        # Log some tool requests
        _log_tool_request_impl(
            session_id, agent_id, "git_status", True, {"repo": "."}, True
        )
        _log_tool_request_impl(
            session_id, agent_id, "edit_file", True, {"file": "test.py"}, True
        )
        _log_tool_request_impl(
            session_id, agent_id, "git_status", True, {"repo": "."}, True
        )
        _log_tool_request_impl(
            session_id, agent_id, "missing_tool", False, {"param": "value"}, False
        )

        # End the session
        _end_session_impl(session_id)

        # Generate analytics report
        report = _generate_analytics_report_impl()

        # Verify session count
        self.assertEqual(report["total_sessions"], 1)

        # Verify tool usage
        self.assertEqual(report["total_tool_requests"], 4)
        self.assertEqual(report["successful_tool_requests"], 3)
        self.assertEqual(report["overall_tool_success_rate"], 75.0)

        # Verify frequently used tools
        tools = report["frequently_used_tools"]
        self.assertEqual(len(tools), 2)  # git_status and edit_file

        # Check git_status (should be most frequent)
        git_tool = next((t for t in tools if t["tool_name"] == "git_status"), None)
        self.assertIsNotNone(git_tool)
        self.assertEqual(git_tool["usage_count"], 2)
        self.assertEqual(git_tool["success_count"], 2)
        self.assertEqual(git_tool["success_rate"], 100.0)

        # Check edit_file
        edit_tool = next((t for t in tools if t["tool_name"] == "edit_file"), None)
        self.assertIsNotNone(edit_tool)
        self.assertEqual(edit_tool["usage_count"], 1)
        self.assertEqual(edit_tool["success_count"], 1)
        self.assertEqual(edit_tool["success_rate"], 100.0)

        # Verify missing tools
        self.assertEqual(report["total_missing_tools"], 1)
        self.assertEqual(report["total_failed_requests"], 1)

        missing_tools = report["missing_tools"]
        self.assertEqual(len(missing_tools), 1)
        missing_tool = missing_tools[0]
        self.assertEqual(missing_tool["tool_name"], "missing_tool")
        self.assertEqual(missing_tool["request_count"], 1)

    def test_multiple_sessions_comprehensive_analytics(self):
        """Test analytics report with multiple sessions and complex tool usage patterns."""
        # Create multiple sessions with different patterns
        sessions_data = [
            {
                "session_id": "session-001",
                "agent_id": "agent-001",
                "tools": [
                    ("git_status", True, True),
                    ("edit_file", True, True),
                    ("run_tests", True, False),  # Available but failed
                    ("missing_tool_a", False, False),
                ],
            },
            {
                "session_id": "session-002",
                "agent_id": "agent-002",
                "tools": [
                    ("git_status", True, True),
                    ("git_commit", True, True),
                    ("edit_file", True, True),
                    ("missing_tool_a", False, False),
                    ("missing_tool_b", False, False),
                ],
            },
            {
                "session_id": "session-003",
                "agent_id": "agent-003",
                "tools": [
                    ("git_status", True, True),
                    ("lint_code", True, True),
                    ("run_tests", True, True),
                    ("missing_tool_b", False, False),
                ],
            },
        ]

        # Create the sessions
        for session_data in sessions_data:
            session_id = session_data["session_id"]
            agent_id = session_data["agent_id"]

            _start_session_impl(session_id)
            _register_agent_impl(session_id, agent_id, "test-agent")

            for tool_name, available, success in session_data["tools"]:
                _log_tool_request_impl(
                    session_id, agent_id, tool_name, available, {}, success
                )

            _end_session_impl(session_id)

        # Generate comprehensive analytics report
        report = _generate_analytics_report_impl(include_session_details=True)

        # Verify session count
        self.assertEqual(report["total_sessions"], 3)

        # Verify tool usage totals
        self.assertEqual(report["total_tool_requests"], 13)  # 4 + 5 + 4
        self.assertEqual(
            report["successful_tool_requests"], 8
        )  # Successful requests only
        expected_success_rate = round((8 / 13) * 100, 2)
        self.assertEqual(report["overall_tool_success_rate"], expected_success_rate)

        # Verify frequently used tools (should be sorted by usage count)
        tools = report["frequently_used_tools"]
        self.assertGreater(len(tools), 0)

        # git_status should be most frequent (3 uses across all sessions)
        git_tool = tools[0]  # Should be first due to sorting
        self.assertEqual(git_tool["tool_name"], "git_status")
        self.assertEqual(git_tool["usage_count"], 3)
        self.assertEqual(git_tool["success_count"], 3)
        self.assertEqual(git_tool["success_rate"], 100.0)
        self.assertEqual(len(git_tool["sessions_used"]), 3)

        # Verify missing tools analysis
        self.assertEqual(
            report["total_missing_tools"], 2
        )  # missing_tool_a and missing_tool_b
        self.assertEqual(report["total_failed_requests"], 4)  # 1 + 2 + 1

        missing_tools = report["missing_tools"]
        self.assertEqual(len(missing_tools), 2)

        # Check missing_tool_a (should have 2 requests from 2 sessions)
        missing_a = next(
            (t for t in missing_tools if t["tool_name"] == "missing_tool_a"), None
        )
        self.assertIsNotNone(missing_a)
        self.assertEqual(missing_a["request_count"], 2)
        self.assertEqual(len(missing_a["requesting_sessions"]), 2)

        # Check missing_tool_b (should have 2 requests from 2 sessions)
        missing_b = next(
            (t for t in missing_tools if t["tool_name"] == "missing_tool_b"), None
        )
        self.assertIsNotNone(missing_b)
        self.assertEqual(missing_b["request_count"], 2)
        self.assertEqual(len(missing_b["requesting_sessions"]), 2)

        # Verify session summaries are included
        self.assertEqual(len(report["session_summaries"]), 3)
        for summary in report["session_summaries"]:
            self.assertIn("session_id", summary)
            self.assertIn("timestamp", summary)
            self.assertIn("status", summary)

    def test_analytics_report_with_session_filter(self):
        """Test analytics report with session status filtering."""
        # Create sessions with different statuses
        _start_session_impl("active-session")
        # Don't end this session, so it remains "active"

        _start_session_impl("completed-session")
        _end_session_impl("completed-session")  # This will be "completed"

        # Test filtering for active sessions only
        active_report = _generate_analytics_report_impl(session_filter="active")
        self.assertEqual(active_report["total_sessions"], 1)

        # Test filtering for completed sessions only
        completed_report = _generate_analytics_report_impl(session_filter="completed")
        self.assertEqual(completed_report["total_sessions"], 1)

        # Test no filter (should include all)
        all_report = _generate_analytics_report_impl()
        self.assertEqual(all_report["total_sessions"], 2)

    def test_analytics_report_with_session_limit(self):
        """Test analytics report with session limit parameter."""
        # Create multiple sessions
        for i in range(5):
            session_id = f"session-{i:03d}"
            _start_session_impl(session_id)
            _end_session_impl(session_id)

        # Test with limit
        limited_report = _generate_analytics_report_impl(limit_sessions=3)
        self.assertEqual(limited_report["total_sessions"], 3)

        # Test without limit
        full_report = _generate_analytics_report_impl()
        self.assertEqual(full_report["total_sessions"], 5)

    def test_analytics_report_date_range_calculation(self):
        """Test that date range is calculated correctly."""
        # Create sessions with known timestamps
        base_time = datetime.now(UTC)

        # Create first session (oldest)
        session1_time = base_time - timedelta(hours=2)
        _start_session_impl("session-1")

        # Manually set timestamp in session data to control the date range
        session1_dir = get_session_directory("session-1")
        session1_file = session1_dir / "session.json"
        session1_data = load_json_data(session1_file, {})
        session1_data["timestamp"] = session1_time.isoformat()
        save_json_data(session1_file, session1_data)

        # Create second session (newest)
        session2_time = base_time
        _start_session_impl("session-2")
        session2_dir = get_session_directory("session-2")
        session2_file = session2_dir / "session.json"
        session2_data = load_json_data(session2_file, {})
        session2_data["timestamp"] = session2_time.isoformat()
        save_json_data(session2_file, session2_data)

        # Generate report and check date range
        report = _generate_analytics_report_impl()

        date_range = report["date_range"]
        self.assertEqual(date_range["start"], session1_time.isoformat())
        self.assertEqual(date_range["end"], session2_time.isoformat())

    def test_analytics_report_tool_success_rate_calculation(self):
        """Test accurate success rate calculation for tools."""
        session_id = "success-rate-test"
        agent_id = "test-agent"

        _start_session_impl(session_id)
        _register_agent_impl(session_id, agent_id, "test-agent")

        # Log tool with mixed success/failure pattern
        _log_tool_request_impl(
            session_id, agent_id, "flaky_tool", True, {}, True
        )  # Success
        _log_tool_request_impl(
            session_id, agent_id, "flaky_tool", True, {}, False
        )  # Failure
        _log_tool_request_impl(
            session_id, agent_id, "flaky_tool", True, {}, True
        )  # Success
        _log_tool_request_impl(
            session_id, agent_id, "flaky_tool", True, {}, False
        )  # Failure
        _log_tool_request_impl(
            session_id, agent_id, "flaky_tool", True, {}, True
        )  # Success

        _end_session_impl(session_id)

        report = _generate_analytics_report_impl()

        # Find the flaky_tool in results
        flaky_tool = next(
            (
                t
                for t in report["frequently_used_tools"]
                if t["tool_name"] == "flaky_tool"
            ),
            None,
        )

        self.assertIsNotNone(flaky_tool)
        self.assertEqual(flaky_tool["usage_count"], 5)
        self.assertEqual(flaky_tool["success_count"], 3)
        self.assertEqual(flaky_tool["success_rate"], 60.0)  # 3/5 * 100

    def test_analytics_report_error_handling(self):
        """Test analytics report error handling for corrupted data."""
        # Create a session with corrupted agent data
        session_id = "corrupted-session"
        _start_session_impl(session_id)

        # Manually corrupt the agent data
        session_dir = get_session_directory(session_id)
        agents_dir = session_dir / "agents" / "corrupted-agent"
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Create invalid JSON in tools.json
        tools_file = agents_dir / "tools.json"
        with open(tools_file, "w") as f:
            f.write("{ invalid json")

        # Should handle corrupted data gracefully
        report = _generate_analytics_report_impl()

        # Should still return a valid report structure
        self.assertIsInstance(report, dict)
        self.assertIn("total_sessions", report)

    def test_analytics_report_timestamp_tracking(self):
        """Test that first/last usage timestamps are tracked correctly."""
        session_id = "timestamp-test"
        agent_id = "test-agent"

        _start_session_impl(session_id)
        _register_agent_impl(session_id, agent_id, "test-agent")

        # Log tool requests with controlled timing
        base_time = datetime.now(UTC)

        # First usage
        first_time = base_time - timedelta(minutes=5)
        _log_tool_request_impl(session_id, agent_id, "timestamp_tool", True, {}, True)

        # Update the timestamp manually in the logged data
        agent_dir = get_session_directory(session_id) / "agents" / agent_id
        tools_file = agent_dir / "tools.json"
        tools_data = load_json_data(tools_file, [])
        if tools_data:
            tools_data[0]["timestamp"] = first_time.isoformat()
            save_json_data(tools_file, tools_data)

        # Second usage (last)
        last_time = base_time
        _log_tool_request_impl(session_id, agent_id, "timestamp_tool", True, {}, True)

        # Update the second timestamp
        tools_data = load_json_data(tools_file, [])
        if len(tools_data) > 1:
            tools_data[1]["timestamp"] = last_time.isoformat()
            save_json_data(tools_file, tools_data)

        _end_session_impl(session_id)

        report = _generate_analytics_report_impl()

        # Find the tool and verify timestamps
        timestamp_tool = next(
            (
                t
                for t in report["frequently_used_tools"]
                if t["tool_name"] == "timestamp_tool"
            ),
            None,
        )

        self.assertIsNotNone(timestamp_tool)
        self.assertEqual(timestamp_tool["first_used"], first_time.isoformat())
        self.assertEqual(timestamp_tool["last_used"], last_time.isoformat())


class TestAnalyticsReportIntegration(TestCase):
    """Integration tests for analytics report functionality."""

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

    def test_realistic_development_session_analytics(self):
        """Test analytics with realistic development session data."""
        session_id = "dev-session-001"
        agent_id = "code-assistant"

        # Start session
        _start_session_impl(session_id)
        _register_agent_impl(
            session_id,
            agent_id,
            "code-assistant",
            purpose="AI coding assistant",
            capabilities=["code-editing", "git-operations", "testing"],
        )

        # Simulate realistic development workflow
        development_tools = [
            # Git operations
            ("git_status", True, True),
            ("git_diff", True, True),
            ("git_add", True, True),
            ("git_commit", True, True),
            # Code editing
            ("edit_file", True, True),
            ("read_file", True, True),
            ("create_file", True, True),
            # Testing
            ("run_tests", True, True),
            ("run_linter", True, False),  # Linter found issues
            # Missing tools that would be useful
            ("format_code", False, False),
            ("run_coverage", False, False),
            ("deploy_preview", False, False),
        ]

        for tool_name, available, success in development_tools:
            _log_tool_request_impl(
                session_id,
                agent_id,
                tool_name,
                available,
                {"context": "development_workflow"},
                success,
            )

        _end_session_impl(session_id, outcome="development_task_completed")

        # Generate analytics report
        report = _generate_analytics_report_impl(include_session_details=True)

        # Verify comprehensive analysis
        self.assertEqual(report["total_sessions"], 1)
        self.assertEqual(report["total_tool_requests"], len(development_tools))

        # Should identify the most commonly used git tools
        git_tools = [
            t
            for t in report["frequently_used_tools"]
            if t["tool_name"].startswith("git_")
        ]
        self.assertGreaterEqual(len(git_tools), 4)

        # Should identify missing development tools
        self.assertEqual(report["total_missing_tools"], 3)
        missing_tool_names = [t["tool_name"] for t in report["missing_tools"]]
        self.assertIn("format_code", missing_tool_names)
        self.assertIn("run_coverage", missing_tool_names)
        self.assertIn("deploy_preview", missing_tool_names)

    def test_cross_session_tool_usage_patterns(self):
        """Test analytics across multiple sessions to identify usage patterns."""
        # Create multiple sessions with different tool usage patterns
        sessions = [
            {
                "session_id": "frontend-work",
                "tools": [
                    ("npm_install", True, True),
                    ("webpack_build", True, True),
                    ("browser_test", False, False),
                ],
            },
            {
                "session_id": "backend-work",
                "tools": [
                    ("run_server", True, True),
                    ("database_migrate", True, True),
                    ("api_test", True, False),
                ],
            },
            {
                "session_id": "devops-work",
                "tools": [
                    ("docker_build", True, True),
                    ("kubernetes_deploy", False, False),
                    ("monitor_logs", True, True),
                ],
            },
        ]

        for session_data in sessions:
            session_id = session_data["session_id"]
            agent_id = f"{session_id}-agent"

            _start_session_impl(session_id)
            _register_agent_impl(session_id, agent_id, "specialized-agent")

            for tool_name, available, success in session_data["tools"]:
                _log_tool_request_impl(
                    session_id, agent_id, tool_name, available, {}, success
                )

            _end_session_impl(session_id)

        # Generate analytics report
        report = _generate_analytics_report_impl()

        # Verify cross-session analysis
        self.assertEqual(report["total_sessions"], 3)

        # Should identify patterns across different types of work
        self.assertGreater(len(report["frequently_used_tools"]), 0)
        self.assertGreater(len(report["missing_tools"]), 0)

        # Should identify missing tools that span multiple domains
        missing_tools = [t["tool_name"] for t in report["missing_tools"]]
        self.assertIn("browser_test", missing_tools)
        self.assertIn("kubernetes_deploy", missing_tools)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
