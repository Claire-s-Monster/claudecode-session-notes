"""
Comprehensive tests for CLI Data Access Endpoints (Task 16).

Tests all new CLI-friendly MCP resource endpoints for querying session and agent data
with advanced filtering, sorting, and data presentation capabilities.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from session_notes.server import (
    # CLI endpoint functions
    _get_agent_details_impl,
    _get_session_details_impl,
    _list_session_agents_cli_impl,
    _list_sessions_cli_impl,
    # Test data creation
    start_session,
    register_agent,
    log_agent_execution,
    log_tool_request,
    log_agent_interaction,
    end_session,
)


class TestCLISessionEndpoints:
    """Test CLI-friendly session data access endpoints."""

    def setup_method(self):
        """Set up test environment with sample data."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.temp_dir)

        # Create test session data
        self.session_id = "cli-test-session"
        self.create_test_session_data()

    def teardown_method(self):
        """Clean up test environment."""
        import os

        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_session_data(self):
        """Create comprehensive test session data."""
        # Create session
        start_session(
            self.session_id,
            environment_info={"test_env": "cli_endpoints", "platform": "test"},
        )

        # Register multiple agents with different types
        register_agent(
            self.session_id,
            agent_id="agent-1",
            agent_type="code-reviewer",
            purpose="Review code for quality",
            capabilities=["lint", "format", "security"],
        )

        register_agent(
            self.session_id,
            agent_id="agent-2",
            agent_type="task-executor",
            purpose="Execute development tasks",
            capabilities=["file-ops", "git", "testing"],
        )

        # Add executions and interactions
        log_agent_execution(
            self.session_id,
            "agent-1",
            "code-reviewer",
            "review_file",
            parameters={"file": "test.py", "severity": "high"},
            result={"issues_found": 2, "status": "completed"},
            execution_time=1200.0,
        )

        log_tool_request(
            self.session_id,
            "agent-1",
            "file_reader",
            available=True,
            parameters={"path": "test.py"},
            success=True,
        )

        log_agent_interaction(
            self.session_id,
            "agent-2",
            "task-executor",
            "plan_implementation",
            interaction_type="decision",
            parameters={"task_id": "123"},
            decision_context={
                "alternatives": ["approach_a", "approach_b"],
                "selected": "approach_b",
                "reasoning": "Better performance characteristics",
            },
            success=True,
        )

        # End session with outcome
        end_session(
            self.session_id, outcome="completed", outcome_metrics={"tasks_completed": 5}
        )

    def test_list_sessions_cli_basic(self):
        """Test basic CLI session listing functionality."""
        sessions = _list_sessions_cli_impl()

        assert len(sessions) == 1
        session = sessions[0]

        # Check core session fields
        assert session["session_id"] == self.session_id
        assert session["status"] == "completed"
        assert "timestamp" in session
        assert "duration" in session

        # Check agent summary information
        assert session["agent_count"] == 2
        assert "code-reviewer" in session["agent_types"]
        assert "task-executor" in session["agent_types"]
        assert session["total_executions"] == 1
        assert session["total_tool_requests"] == 1
        assert session["total_interactions"] == 1

    def test_list_sessions_cli_filtering(self):
        """Test CLI session listing with status filtering."""
        # Create additional session with different status
        session_id_2 = "active-session"
        start_session(session_id_2)

        # Test filtering by completed status
        completed_sessions = _list_sessions_cli_impl(status_filter="completed")
        assert len(completed_sessions) == 1
        assert completed_sessions[0]["session_id"] == self.session_id

        # Test filtering by active status
        active_sessions = _list_sessions_cli_impl(status_filter="active")
        assert len(active_sessions) == 1
        assert active_sessions[0]["session_id"] == session_id_2

        # Test filtering by non-existent status
        none_sessions = _list_sessions_cli_impl(status_filter="non-existent")
        assert len(none_sessions) == 0

    def test_list_sessions_cli_sorting(self):
        """Test CLI session listing with sorting options."""
        # Create multiple sessions for sorting
        session_ids = ["sort-session-1", "sort-session-2", "sort-session-3"]
        for i, sid in enumerate(session_ids):
            start_session(sid)
            # Add varying numbers of agents for sort testing
            for j in range(i + 1):
                register_agent(sid, agent_id=f"agent-{j}", agent_type="test")

        # Test sorting by agent count (ascending)
        sessions = _list_sessions_cli_impl(sort_by="agent_count", reverse=False)
        agent_counts = [s["agent_count"] for s in sessions]
        assert agent_counts == sorted(agent_counts)

        # Test sorting by agent count (descending)
        sessions = _list_sessions_cli_impl(sort_by="agent_count", reverse=True)
        agent_counts = [s["agent_count"] for s in sessions]
        assert agent_counts == sorted(agent_counts, reverse=True)

        # Test invalid sort key defaults to timestamp
        sessions = _list_sessions_cli_impl(sort_by="invalid_key")
        assert len(sessions) > 0  # Should not crash

    def test_list_sessions_cli_limit(self):
        """Test CLI session listing with result limiting."""
        # Create multiple sessions
        for i in range(5):
            start_session(f"limit-test-session-{i}")

        # Test with limit
        sessions = _list_sessions_cli_impl(limit=3)
        assert len(sessions) == 3

        # Test with limit larger than available
        sessions = _list_sessions_cli_impl(limit=20)
        assert len(sessions) == 6  # Original + 5 new sessions

    def test_get_session_details_basic(self):
        """Test basic CLI session details retrieval."""
        details = _get_session_details_impl(self.session_id)

        # Check session information
        assert details["session_id"] == self.session_id
        assert details["status"] == "completed"
        assert details["outcome"] == "completed"
        assert details["agent_count"] == 2

        # Check environment summary
        assert "environment_summary" in details
        env_summary = details["environment_summary"]
        assert "python_version" in env_summary
        assert "working_directory" in env_summary

        # Check agent summaries
        assert "agent_summaries" in details
        agent_summaries = details["agent_summaries"]
        assert len(agent_summaries) == 2

        # Verify agent summary structure
        agent_1 = next(a for a in agent_summaries if a["agent_id"] == "agent-1")
        assert agent_1["agent_type"] == "code-reviewer"
        assert agent_1["purpose"] == "Review code for quality"
        assert agent_1["execution_count"] == 1
        assert agent_1["tool_request_count"] == 1
        assert agent_1["interaction_count"] == 0

        agent_2 = next(a for a in agent_summaries if a["agent_id"] == "agent-2")
        assert agent_2["agent_type"] == "task-executor"
        assert agent_2["interaction_count"] == 1

    def test_get_session_details_with_raw_data(self):
        """Test CLI session details with raw data inclusion."""
        details = _get_session_details_impl(self.session_id, include_raw_data=True)

        # Should include full environment data
        assert "environment_full" in details
        assert "agents" in details  # Full agent data

        # Check full agent data structure
        agents = details["agents"]
        assert "agent-1" in agents
        assert "metadata" in agents["agent-1"]
        assert "executions" in agents["agent-1"]
        assert "tool_requests" in agents["agent-1"]
        assert "interactions" in agents["agent-1"]

    def test_get_session_details_not_found(self):
        """Test CLI session details for non-existent session."""
        details = _get_session_details_impl("non-existent-session")

        assert "error" in details
        assert "not found" in details["error"]


class TestCLIAgentEndpoints:
    """Test CLI-friendly agent data access endpoints."""

    def setup_method(self):
        """Set up test environment with sample agent data."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.temp_dir)

        # Create test session with agents
        self.session_id = "agent-test-session"
        start_session(self.session_id)

        # Create diverse agent data
        self.create_test_agent_data()

    def teardown_method(self):
        """Clean up test environment."""
        import os

        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_agent_data(self):
        """Create comprehensive test agent data."""
        # Register agents with different characteristics
        register_agent(
            self.session_id,
            agent_id="reviewer-agent",
            agent_type="code-reviewer",
            purpose="Review code quality",
            capabilities=["lint", "security", "performance"],
        )

        register_agent(
            self.session_id,
            agent_id="executor-agent",
            agent_type="task-executor",
            purpose="Execute development tasks",
            capabilities=["file-ops", "git", "testing", "deployment"],
        )

        register_agent(
            self.session_id,
            agent_id="analyzer-agent",
            agent_type="code-analyzer",
            purpose="Analyze code complexity",
            capabilities=["metrics", "dependencies", "architecture"],
        )

        # Add varied execution histories
        for i in range(3):
            log_agent_execution(
                self.session_id,
                "reviewer-agent",
                "code-reviewer",
                f"review_action_{i}",
                parameters={"file": f"file_{i}.py"},
                result={"issues": i},
                execution_time=1000 + i * 100,
            )

        for i in range(2):
            log_agent_execution(
                self.session_id,
                "executor-agent",
                "task-executor",
                f"execute_task_{i}",
                parameters={"task_id": f"task_{i}"},
                result={"status": "completed"},
                execution_time=2000 + i * 200,
            )

        # Add tool requests
        log_tool_request(
            self.session_id,
            "reviewer-agent",
            "file_reader",
            available=True,
            success=True,
        )

        log_tool_request(
            self.session_id,
            "executor-agent",
            "git_tool",
            available=True,
            success=True,
        )

        # Add interactions
        log_agent_interaction(
            self.session_id,
            "analyzer-agent",
            "code-analyzer",
            "analyze_complexity",
            interaction_type="analysis",
            parameters={"module": "core"},
            result={"complexity_score": 7.5},
            success=True,
        )

    def test_list_session_agents_cli_basic(self):
        """Test basic CLI agent listing functionality."""
        agents = _list_session_agents_cli_impl(self.session_id)

        assert len(agents) == 3

        # Check agent information structure
        agent_ids = {agent["agent_id"] for agent in agents}
        assert agent_ids == {"reviewer-agent", "executor-agent", "analyzer-agent"}

        # Check specific agent data
        reviewer = next(a for a in agents if a["agent_id"] == "reviewer-agent")
        assert reviewer["agent_type"] == "code-reviewer"
        assert reviewer["purpose"] == "Review code quality"
        assert "lint" in reviewer["capabilities"]
        assert reviewer["execution_count"] == 3
        assert reviewer["tool_request_count"] == 1
        assert reviewer["interaction_count"] == 0

    def test_list_session_agents_cli_filtering(self):
        """Test CLI agent listing with type filtering."""
        # Filter by code-reviewer type
        reviewers = _list_session_agents_cli_impl(
            self.session_id, agent_type_filter="code-reviewer"
        )
        assert len(reviewers) == 1
        assert reviewers[0]["agent_id"] == "reviewer-agent"

        # Filter by non-existent type
        none_agents = _list_session_agents_cli_impl(
            self.session_id, agent_type_filter="non-existent"
        )
        assert len(none_agents) == 0

    def test_list_session_agents_cli_sorting(self):
        """Test CLI agent listing with sorting options."""
        # Sort by execution count (ascending)
        agents = _list_session_agents_cli_impl(
            self.session_id, sort_by="execution_count"
        )
        execution_counts = [a["execution_count"] for a in agents]
        assert execution_counts == sorted(execution_counts)

        # Sort by agent type
        agents = _list_session_agents_cli_impl(self.session_id, sort_by="agent_type")
        agent_types = [a["agent_type"] for a in agents]
        assert agent_types == sorted(agent_types)

    def test_list_session_agents_cli_no_stats(self):
        """Test CLI agent listing without statistics."""
        agents = _list_session_agents_cli_impl(self.session_id, include_stats=False)

        assert len(agents) == 3

        # Should not include execution counts or stats
        for agent in agents:
            assert "execution_count" not in agent
            assert "tool_request_count" not in agent
            assert "interaction_count" not in agent
            assert "interaction_stats" not in agent

    def test_list_session_agents_cli_invalid_session(self):
        """Test CLI agent listing for non-existent session."""
        agents = _list_session_agents_cli_impl("non-existent-session")
        assert agents == []

    def test_get_agent_details_basic(self):
        """Test basic CLI agent details retrieval."""
        details = _get_agent_details_impl(self.session_id, "reviewer-agent")

        # Check core agent information
        assert details["agent_id"] == "reviewer-agent"
        assert details["session_id"] == self.session_id
        assert details["agent_type"] == "code-reviewer"
        assert details["purpose"] == "Review code quality"
        assert details["capabilities"] == ["lint", "security", "performance"]

        # Check activity statistics
        assert details["execution_count"] == 3
        assert details["tool_request_count"] == 1
        assert details["interaction_count"] == 0
        assert "last_activity" in details

    def test_get_agent_details_with_executions(self):
        """Test CLI agent details with execution history."""
        details = _get_agent_details_impl(
            self.session_id, "reviewer-agent", include_executions=True
        )

        assert "executions" in details
        executions = details["executions"]
        assert len(executions) == 3

        # Check execution structure
        execution = executions[0]
        assert "agent_id" in execution
        assert "action" in execution
        assert "parameters" in execution
        assert "result" in execution

    def test_get_agent_details_with_limit(self):
        """Test CLI agent details with execution limit."""
        details = _get_agent_details_impl(
            self.session_id,
            "reviewer-agent",
            include_executions=True,
            execution_limit=2,
        )

        assert "executions" in details
        executions = details["executions"]
        assert len(executions) == 2  # Limited to 2 most recent

    def test_get_agent_details_with_tools_and_interactions(self):
        """Test CLI agent details with tool and interaction data."""
        details = _get_agent_details_impl(
            self.session_id,
            "analyzer-agent",
            include_tools=True,
            include_interactions=True,
        )

        # Should include tool requests (even if empty for this agent)
        assert "tool_requests" in details

        # Should include interactions
        assert "interactions" in details
        interactions = details["interactions"]
        assert len(interactions) == 1

        interaction = interactions[0]
        assert interaction["action"] == "analyze_complexity"
        assert interaction["interaction_type"] == "analysis"

    def test_get_agent_details_not_found(self):
        """Test CLI agent details for non-existent agent."""
        # Non-existent session
        details = _get_agent_details_impl("non-existent-session", "agent")
        assert "error" in details
        assert "Session" in details["error"]

        # Non-existent agent
        details = _get_agent_details_impl(self.session_id, "non-existent-agent")
        assert "error" in details
        assert "Agent" in details["error"]


class TestCLIEndpointIntegration:
    """Integration tests for CLI endpoint workflows."""

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

    def test_full_cli_workflow(self):
        """Test complete CLI data access workflow."""
        # 1. Start with no sessions
        sessions = _list_sessions_cli_impl()
        assert len(sessions) == 0

        # 2. Create session with comprehensive data
        session_id = "workflow-test-session"
        start_session(session_id, {"test": "workflow"})

        # 3. Register agents
        register_agent(session_id, "agent-1", "code-reviewer", "Review code")
        register_agent(session_id, "agent-2", "task-executor", "Execute tasks")

        # 4. Add activities
        log_agent_execution(
            session_id,
            "agent-1",
            "code-reviewer",
            "review",
            parameters={"file": "main.py"},
            result={"issues": 1},
        )
        log_tool_request(session_id, "agent-1", "linter", True, success=True)
        log_agent_interaction(
            session_id,
            "agent-2",
            "task-executor",
            "plan",
            interaction_type="decision",
            success=True,
        )

        # 5. Test session listing shows new session
        sessions = _list_sessions_cli_impl()
        assert len(sessions) == 1
        session = sessions[0]
        assert session["session_id"] == session_id
        assert session["agent_count"] == 2
        assert session["total_executions"] == 1
        assert session["total_tool_requests"] == 1
        assert session["total_interactions"] == 1

        # 6. Test detailed session information
        details = _get_session_details_impl(session_id)
        assert details["agent_count"] == 2
        assert len(details["agent_summaries"]) == 2

        # 7. Test agent listing
        agents = _list_session_agents_cli_impl(session_id)
        assert len(agents) == 2
        agent_1 = next(a for a in agents if a["agent_id"] == "agent-1")
        assert agent_1["execution_count"] == 1
        assert agent_1["tool_request_count"] == 1

        # 8. Test detailed agent information
        agent_details = _get_agent_details_impl(
            session_id, "agent-2", include_interactions=True
        )
        assert agent_details["agent_id"] == "agent-2"
        assert "interactions" in agent_details
        assert len(agent_details["interactions"]) == 1

        # 9. End session and verify final state
        end_session(session_id, "completed")
        final_details = _get_session_details_impl(session_id)
        assert final_details["status"] == "completed"
        assert "duration" in final_details

    def test_cli_endpoint_error_handling(self):
        """Test CLI endpoint error handling and edge cases."""
        # Test with empty session directory
        sessions = _list_sessions_cli_impl()
        assert sessions == []

        # Test non-existent session details
        details = _get_session_details_impl("non-existent")
        assert "error" in details

        # Test non-existent agent listing
        agents = _list_session_agents_cli_impl("non-existent")
        assert agents == []

        # Test non-existent agent details
        agent_details = _get_agent_details_impl("non-existent", "non-existent")
        assert "error" in agent_details

    def test_cli_endpoint_data_consistency(self):
        """Test data consistency across CLI endpoints."""
        # Create session with known data
        session_id = "consistency-test"
        start_session(session_id)

        agent_id = "test-agent"
        register_agent(session_id, agent_id, "test-type", "Test purpose")

        # Add specific activities
        log_agent_execution(session_id, agent_id, "test-type", "action1")
        log_agent_execution(session_id, agent_id, "test-type", "action2")
        log_tool_request(session_id, agent_id, "tool1", True, success=True)

        # Verify consistency across endpoints
        # 1. Session list should show correct counts
        sessions = _list_sessions_cli_impl()
        session = sessions[0]
        assert session["agent_count"] == 1
        assert session["total_executions"] == 2
        assert session["total_tool_requests"] == 1

        # 2. Session details should match
        details = _get_session_details_impl(session_id)
        assert details["agent_count"] == 1
        assert len(details["agent_summaries"]) == 1
        agent_summary = details["agent_summaries"][0]
        assert agent_summary["execution_count"] == 2
        assert agent_summary["tool_request_count"] == 1

        # 3. Agent listing should match
        agents = _list_session_agents_cli_impl(session_id)
        assert len(agents) == 1
        agent = agents[0]
        assert agent["execution_count"] == 2
        assert agent["tool_request_count"] == 1

        # 4. Agent details should match
        agent_details = _get_agent_details_impl(session_id, agent_id)
        assert agent_details["execution_count"] == 2
        assert agent_details["tool_request_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
