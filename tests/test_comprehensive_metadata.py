#!/usr/bin/env python3
"""
Tests for comprehensive session metadata collection functionality.

This test suite validates the enhanced metadata collection capabilities including
automatic environment detection, metadata updates, and comprehensive metrics calculation.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest import TestCase

import pytest


class TestComprehensiveMetadata(TestCase):
    """Test suite for comprehensive session metadata collection."""

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

    def test_collect_environment_metadata(self):
        """Test automatic environment metadata collection."""
        from session_notes.server import collect_environment_metadata

        env_data = collect_environment_metadata()

        # Verify structure
        self.assertIn("system", env_data)
        self.assertIn("python", env_data)
        self.assertIn("process", env_data)
        self.assertIn("environment_vars", env_data)
        self.assertIn("collection_metadata", env_data)

        # Verify system information
        system_info = env_data["system"]
        self.assertIn("platform", system_info)
        self.assertIn("architecture", system_info)
        self.assertIn("machine", system_info)

        # Verify Python information
        python_info = env_data["python"]
        self.assertIn("version", python_info)
        self.assertIn("implementation", python_info)
        self.assertIn("executable", python_info)

        # Verify process information
        process_info = env_data["process"]
        self.assertIn("pid", process_info)
        self.assertIn("working_directory", process_info)
        self.assertIn("user", process_info)

        # Verify collection metadata
        collection_info = env_data["collection_metadata"]
        self.assertIn("timestamp", collection_info)
        self.assertIn("collector_version", collection_info)

    def test_merge_environment_metadata(self):
        """Test merging provided environment data with auto-collected metadata."""
        from session_notes.server import merge_environment_metadata

        provided_env = {
            "custom_field": "custom_value",
            "system": {"custom_system_field": "custom_system_value"},
            "application": {"name": "test_app", "version": "1.0.0"},
        }

        merged_env = merge_environment_metadata(provided_env, auto_collect=True)

        # Verify custom fields are preserved
        self.assertEqual(merged_env["custom_field"], "custom_value")
        self.assertEqual(merged_env["application"]["name"], "test_app")

        # Verify auto-collected data is present
        self.assertIn("python", merged_env)
        self.assertIn("process", merged_env)

        # Verify merging within nested dictionaries
        self.assertIn("custom_system_field", merged_env["system"])
        self.assertIn("platform", merged_env["system"])  # Auto-collected

    def test_merge_environment_metadata_no_auto_collect(self):
        """Test merging when auto-collection is disabled."""
        from session_notes.server import merge_environment_metadata

        provided_env = {"custom_field": "custom_value"}
        merged_env = merge_environment_metadata(provided_env, auto_collect=False)

        # Should only contain provided data
        self.assertEqual(merged_env, provided_env)
        self.assertNotIn("system", merged_env)
        self.assertNotIn("python", merged_env)

    def test_start_session_with_comprehensive_metadata(self):
        """Test start_session with comprehensive metadata collection."""
        from session_notes.server import get_session_directory, start_session

        session_id = "test-comprehensive-metadata"
        custom_env = {"project": "test_project", "user_config": {"theme": "dark"}}

        result = start_session(session_id, custom_env, auto_collect_environment=True)

        # Verify result message
        self.assertIn(session_id, result)
        self.assertIn("comprehensive metadata collection", result)

        # Load and verify session data
        session_dir = get_session_directory(session_id)
        session_file = session_dir / "session.json"

        with open(session_file, encoding="utf-8") as f:
            session_data = json.load(f)

        # Verify comprehensive environment data
        environment = session_data["environment"]

        # Custom data should be present
        self.assertEqual(environment["project"], "test_project")
        self.assertEqual(environment["user_config"]["theme"], "dark")

        # Auto-collected data should be present
        self.assertIn("system", environment)
        self.assertIn("python", environment)
        self.assertIn("process", environment)
        self.assertIn("collection_metadata", environment)

    def test_start_session_without_auto_collect(self):
        """Test start_session with auto-collection disabled."""
        from session_notes.server import get_session_directory, start_session

        session_id = "test-no-auto-collect"
        custom_env = {"project": "test_project"}

        start_session(session_id, custom_env, auto_collect_environment=False)

        # Load and verify session data
        session_dir = get_session_directory(session_id)
        session_file = session_dir / "session.json"

        with open(session_file, encoding="utf-8") as f:
            session_data = json.load(f)

        # Should only contain custom environment data
        environment = session_data["environment"]
        self.assertEqual(environment, custom_env)
        self.assertNotIn("system", environment)
        self.assertNotIn("python", environment)

    def test_calculate_session_metrics(self):
        """Test comprehensive session metrics calculation."""
        from session_notes.server import (
            calculate_session_metrics,
            get_session_directory,
            log_agent_execution,
            log_tool_request,
            start_session,
        )

        session_id = "test-metrics"
        start_session(session_id)

        # Add some agent data
        log_agent_execution(
            session_id,
            "agent-1",
            "code-reviewer",
            "review_code",
            {"file": "test.py"},
            {"status": "approved"},
            1500.0,
        )
        log_agent_execution(
            session_id,
            "agent-2",
            "task-executor",
            "run_task",
            {"task": "compile"},
            {"status": "success"},
            3000.0,
        )
        log_tool_request(session_id, "agent-1", "Edit", True, {"file": "test.py"}, True)
        log_tool_request(session_id, "agent-2", "Bash", True, {"command": "ls"}, True)

        # Calculate metrics
        session_dir = get_session_directory(session_id)
        duration = 120.0  # 2 minutes
        metrics = calculate_session_metrics(session_id, session_dir, duration)

        # Verify metrics
        self.assertEqual(metrics["agent_count"], 2)
        self.assertEqual(metrics["total_executions"], 2)
        self.assertEqual(metrics["total_tool_requests"], 2)
        self.assertEqual(
            set(metrics["unique_agent_types"]), {"code-reviewer", "task-executor"}
        )
        self.assertEqual(metrics["agent_type_count"], 2)

        # Verify rates
        self.assertAlmostEqual(metrics["executions_per_minute"], 1.0)
        self.assertAlmostEqual(metrics["tool_requests_per_minute"], 1.0)

    def test_end_session_with_comprehensive_metrics(self):
        """Test end_session with comprehensive metrics calculation."""
        from session_notes.server import (
            end_session,
            get_session_directory,
            log_agent_execution,
            start_session,
        )

        session_id = "test-end-comprehensive"
        start_session(session_id)

        # Add some activity
        log_agent_execution(session_id, "agent-1", "test-agent", "test_action")

        # Small delay to ensure measurable duration
        time.sleep(0.1)

        # End session with outcome
        outcome = "successful_completion"
        outcome_metrics = {"tasks_completed": 5, "errors": 0}
        result = end_session(session_id, outcome, outcome_metrics)

        # Verify result contains metrics
        self.assertIn("Duration:", result)
        self.assertIn("Agents: 1", result)
        self.assertIn("Executions: 1", result)

        # Load and verify session data
        session_dir = get_session_directory(session_id)
        session_file = session_dir / "session.json"

        with open(session_file, encoding="utf-8") as f:
            session_data = json.load(f)

        # Verify comprehensive session data
        self.assertEqual(session_data["status"], "completed")
        self.assertEqual(session_data["outcome"], outcome)
        self.assertEqual(session_data["outcome_metrics"], outcome_metrics)
        self.assertIn("duration", session_data)
        self.assertIn("end_timestamp", session_data)
        self.assertIn("session_metrics", session_data)

        # Verify session metrics
        metrics = session_data["session_metrics"]
        self.assertEqual(metrics["agent_count"], 1)
        self.assertEqual(metrics["total_executions"], 1)

    def test_update_session_metadata(self):
        """Test updating session metadata during session lifecycle."""
        from session_notes.server import (
            get_session_directory,
            start_session,
            update_session_metadata,
        )

        session_id = "test-update-metadata"
        start_session(session_id, {"initial": "data"})

        # Update metadata
        updates = {
            "progress": {"current_task": "task_1", "completion": 0.5},
            "environment": {"runtime_config": {"debug": True}},
            "custom_field": "custom_value",
        }

        result = update_session_metadata(session_id, updates, merge_environment=True)
        self.assertIn("updated successfully", result)

        # Load and verify updated data
        session_dir = get_session_directory(session_id)
        session_file = session_dir / "session.json"

        with open(session_file, encoding="utf-8") as f:
            session_data = json.load(f)

        # Verify updates
        self.assertEqual(session_data["progress"]["current_task"], "task_1")
        self.assertEqual(session_data["custom_field"], "custom_value")
        self.assertIn("last_updated", session_data)

        # Verify environment merging
        environment = session_data["environment"]
        self.assertEqual(environment["runtime_config"]["debug"], True)
        self.assertIn("initial", environment)  # Original custom data preserved

    def test_get_session_status(self):
        """Test getting current session status and metrics."""
        from session_notes.server import (
            get_session_status,
            log_agent_execution,
            start_session,
        )

        session_id = "test-status"
        start_session(session_id)

        # Add some activity
        log_agent_execution(session_id, "agent-1", "test-agent", "test_action")

        # Get status
        status = get_session_status(session_id)

        # Verify status information
        self.assertEqual(status["session_id"], session_id)
        self.assertEqual(status["status"], "active")
        self.assertIn("start_timestamp", status)
        self.assertIn("current_duration", status)
        self.assertEqual(status["agent_count"], 1)
        self.assertEqual(status["total_executions"], 1)
        self.assertEqual(status["total_tool_requests"], 0)
        self.assertTrue(status["environment_collected"])

    def test_get_session_status_nonexistent(self):
        """Test getting status for non-existent session."""
        from session_notes.server import get_session_status

        status = get_session_status("nonexistent-session")
        self.assertIn("error", status)
        self.assertIn("not found", status["error"])

    def test_environment_metadata_persistence(self):
        """Test that environment metadata persists correctly through session lifecycle."""
        from session_notes.server import (
            end_session,
            get_session_directory,
            start_session,
        )

        session_id = "test-persistence"
        custom_env = {"project_type": "python", "version": "3.12"}

        # Start session
        start_session(session_id, custom_env, auto_collect_environment=True)

        # End session
        end_session(session_id)

        # Load final session data
        session_dir = get_session_directory(session_id)
        session_file = session_dir / "session.json"

        with open(session_file, encoding="utf-8") as f:
            session_data = json.load(f)

        # Verify environment data survived the full lifecycle
        environment = session_data["environment"]
        self.assertEqual(environment["project_type"], "python")
        self.assertEqual(environment["version"], "3.12")
        self.assertIn("system", environment)  # Auto-collected data
        self.assertIn("python", environment)  # Auto-collected data


if __name__ == "__main__":
    pytest.main([__file__])
