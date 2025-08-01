#!/usr/bin/env python3
"""
Test suite for detailed agent interaction tracking functionality in the session-notes MCP server.

Tests the enhanced AgentInteraction model, log_agent_interaction tool, and comprehensive
interaction statistics and analysis capabilities.
"""

import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from session_notes.server import (
    AgentInteraction,
    _get_agent_metadata_impl,
    _get_session_impl,
    _log_agent_interaction_impl,
    _register_agent_impl,
    _start_session_impl,
    agent_exists,
    get_agent_directory,
    get_agent_interaction_statistics,
    get_last_agent_activity,
    load_json_data,
)


class TestAgentInteractionModel:
    """Test the AgentInteraction Pydantic model."""

    def test_agent_interaction_creation_minimal(self):
        """Test creating AgentInteraction with minimal required fields."""
        interaction = AgentInteraction(
            interaction_id="test-interaction-123",
            agent_id="test-agent-123",
            agent_type="test-agent",
            timestamp="2023-01-01T00:00:00Z",
            action="test-action",
            interaction_type="general",
        )

        assert interaction.interaction_id == "test-interaction-123"
        assert interaction.agent_id == "test-agent-123"
        assert interaction.agent_type == "test-agent"
        assert interaction.timestamp == "2023-01-01T00:00:00Z"
        assert interaction.action == "test-action"
        assert interaction.interaction_type == "general"
        assert interaction.parameters == {}
        assert interaction.result is None
        assert interaction.execution_time is None
        assert interaction.context == {}
        assert interaction.decision_context is None
        assert interaction.communication_data is None
        assert interaction.parent_interaction_id is None
        assert interaction.related_execution_ids == []
        assert interaction.workflow_stage is None
        assert interaction.success is True
        assert interaction.outcome_assessment is None
        assert interaction.tags == []
        assert interaction.metadata == {}

    def test_agent_interaction_creation_comprehensive(self):
        """Test creating AgentInteraction with all fields populated."""
        interaction = AgentInteraction(
            interaction_id="comprehensive-interaction",
            agent_id="comprehensive-agent",
            agent_type="decision-maker",
            timestamp="2023-01-01T12:00:00Z",
            action="analyze-code-quality",
            interaction_type="decision",
            parameters={"file_path": "test.py", "strictness": "high"},
            result={"quality_score": 85, "issues": ["minor", "style"]},
            execution_time=1250.5,
            context={"trigger": "pull_request", "reviewer": "senior_dev"},
            decision_context={
                "alternatives": ["approve", "request_changes", "comment"],
                "chosen": "request_changes",
                "reasoning": "Quality score below threshold",
            },
            communication_data={"messages": 3, "channels": ["pr_comment", "slack"]},
            parent_interaction_id="parent-123",
            related_execution_ids=["exec-1", "exec-2"],
            workflow_stage="code_review",
            success=True,
            outcome_assessment={"effectiveness": "high", "user_satisfaction": 4.5},
            tags=["code_quality", "automated", "critical"],
            metadata={"version": "2.1", "config": {"timeout": 30}},
        )

        assert interaction.interaction_id == "comprehensive-interaction"
        assert interaction.action == "analyze-code-quality"
        assert interaction.interaction_type == "decision"
        assert interaction.parameters["strictness"] == "high"
        assert interaction.result["quality_score"] == 85
        assert interaction.execution_time == 1250.5
        assert interaction.context["trigger"] == "pull_request"
        assert interaction.decision_context["chosen"] == "request_changes"
        assert interaction.communication_data["messages"] == 3
        assert interaction.parent_interaction_id == "parent-123"
        assert len(interaction.related_execution_ids) == 2
        assert interaction.workflow_stage == "code_review"
        assert interaction.success is True
        assert interaction.outcome_assessment["effectiveness"] == "high"
        assert "automated" in interaction.tags
        assert interaction.metadata["version"] == "2.1"

    def test_agent_interaction_serialization(self):
        """Test AgentInteraction serialization to dict."""
        interaction = AgentInteraction(
            interaction_id="serialization-test",
            agent_id="test-agent",
            agent_type="test-type",
            timestamp="2023-01-01T00:00:00Z",
            action="test-action",
            interaction_type="analysis",
            parameters={"param1": "value1"},
            tags=["test", "serialization"],
            metadata={"test_key": "test_value"},
        )

        data = interaction.model_dump()

        assert isinstance(data, dict)
        assert data["interaction_id"] == "serialization-test"
        assert data["action"] == "test-action"
        assert data["interaction_type"] == "analysis"
        assert data["parameters"]["param1"] == "value1"
        assert data["tags"] == ["test", "serialization"]
        assert data["metadata"]["test_key"] == "test_value"


class TestAgentInteractionLogging:
    """Test detailed agent interaction logging functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())

        # Patch the session directory to use our temp directory
        self.session_dir_patcher = patch(
            "session_notes.server.get_session_directory",
            return_value=self.test_dir / ".claude" / "session-notes" / self.session_id,
        )
        self.session_dir_patcher.start()

        # Create a test session
        _start_session_impl(self.session_id, auto_collect_environment=False)

    def teardown_method(self):
        """Clean up after each test."""
        self.session_dir_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_log_interaction_minimal(self):
        """Test logging an interaction with minimal parameters."""
        result = _log_agent_interaction_impl(
            session_id=self.session_id,
            agent_id="minimal-agent",
            agent_type="test-agent",
            action="test-action",
        )

        assert "Logged interaction" in result
        assert "minimal-agent" in result
        assert agent_exists(self.session_id, "minimal-agent")

        # Verify interactions.json was created and contains the interaction
        agent_dir = get_agent_directory(self.session_id, "minimal-agent")
        interactions_file = agent_dir / "interactions.json"
        assert interactions_file.exists()

        interactions = load_json_data(interactions_file, [])
        assert len(interactions) == 1

        interaction = interactions[0]
        assert interaction["agent_id"] == "minimal-agent"
        assert interaction["action"] == "test-action"
        assert interaction["interaction_type"] == "general"
        assert interaction["success"] is True

    def test_log_interaction_comprehensive(self):
        """Test logging an interaction with comprehensive data."""
        # Pre-register agent
        _register_agent_impl(
            session_id=self.session_id,
            agent_id="comprehensive-agent",
            agent_type="decision-maker",
        )

        result = _log_agent_interaction_impl(
            session_id=self.session_id,
            agent_id="comprehensive-agent",
            agent_type="decision-maker",
            action="evaluate-pull-request",
            interaction_type="decision",
            parameters={"pr_id": "123", "files_changed": 5},
            result={"decision": "approve", "confidence": 0.95},
            execution_time=2500.0,
            context={"triggered_by": "webhook", "urgency": "high"},
            decision_context={
                "alternatives": ["approve", "request_changes", "reject"],
                "criteria": ["test_coverage", "code_quality", "security"],
                "scores": {"test_coverage": 95, "code_quality": 88, "security": 92},
                "chosen": "approve",
                "reasoning": "All criteria meet standards",
            },
            communication_data={
                "notification_sent": True,
                "channels": ["email", "slack"],
                "recipients": 3,
            },
            workflow_stage="final_review",
            success=True,
            outcome_assessment={"user_feedback": 5, "accuracy": 0.98},
            tags=["automated", "pr_review", "high_confidence"],
            metadata={"model_version": "v2.1", "config": {"strict_mode": True}},
            auto_register=False,
        )

        assert "Logged interaction" in result
        assert "comprehensive-agent" in result

        # Verify comprehensive data was stored correctly
        agent_dir = get_agent_directory(self.session_id, "comprehensive-agent")
        interactions = load_json_data(agent_dir / "interactions.json", [])

        assert len(interactions) == 1
        interaction = interactions[0]

        assert interaction["action"] == "evaluate-pull-request"
        assert interaction["interaction_type"] == "decision"
        assert interaction["parameters"]["pr_id"] == "123"
        assert interaction["result"]["decision"] == "approve"
        assert interaction["execution_time"] == 2500.0
        assert interaction["context"]["urgency"] == "high"
        assert interaction["decision_context"]["chosen"] == "approve"
        assert interaction["communication_data"]["recipients"] == 3
        assert interaction["workflow_stage"] == "final_review"
        assert interaction["outcome_assessment"]["accuracy"] == 0.98
        assert "automated" in interaction["tags"]
        assert interaction["metadata"]["model_version"] == "v2.1"

    def test_log_interaction_with_auto_registration(self):
        """Test that agents are auto-registered when logging interactions."""
        agent_id = "auto-registered-interaction-agent"

        # Verify agent doesn't exist initially
        assert not agent_exists(self.session_id, agent_id)

        # Log interaction with auto-registration enabled
        result = _log_agent_interaction_impl(
            session_id=self.session_id,
            agent_id=agent_id,
            agent_type="auto-interaction-agent",
            action="first-interaction",
            interaction_type="communication",
            auto_register=True,
        )

        assert "Logged interaction" in result

        # Verify agent was auto-registered
        assert agent_exists(self.session_id, agent_id)

        # Verify auto-registration metadata
        metadata = _get_agent_metadata_impl(self.session_id, agent_id)
        assert metadata["agent_type"] == "auto-interaction-agent"
        assert "Auto-registered" in metadata["purpose"]
        assert metadata["registration_context"]["auto_registered"] is True
        assert metadata["registration_context"]["first_action"] == "first-interaction"
        assert (
            metadata["registration_context"]["registration_trigger"]
            == "log_agent_interaction"
        )

    def test_log_interaction_custom_id(self):
        """Test logging interaction with custom interaction ID."""
        custom_id = "custom-interaction-123"

        result = _log_agent_interaction_impl(
            session_id=self.session_id,
            agent_id="custom-id-agent",
            agent_type="test-agent",
            action="custom-id-test",
            interaction_id=custom_id,
        )

        assert custom_id in result

        # Verify custom ID was used
        agent_dir = get_agent_directory(self.session_id, "custom-id-agent")
        interactions = load_json_data(agent_dir / "interactions.json", [])

        assert len(interactions) == 1
        assert interactions[0]["interaction_id"] == custom_id

    def test_log_multiple_interactions_ordering(self):
        """Test that multiple interactions are stored in chronological order."""
        agent_id = "multi-interaction-agent"

        # Log multiple interactions
        for i in range(3):
            _log_agent_interaction_impl(
                session_id=self.session_id,
                agent_id=agent_id,
                agent_type="test-agent",
                action=f"action-{i}",
                interaction_type="workflow",
                workflow_stage=f"stage-{i}",
            )

        # Verify all interactions were stored in order
        agent_dir = get_agent_directory(self.session_id, agent_id)
        interactions = load_json_data(agent_dir / "interactions.json", [])

        assert len(interactions) == 3

        # Verify chronological ordering by checking timestamps
        timestamps = [interaction["timestamp"] for interaction in interactions]
        assert timestamps == sorted(timestamps)

        # Verify actions are in order
        actions = [interaction["action"] for interaction in interactions]
        assert actions == ["action-0", "action-1", "action-2"]


class TestInteractionStatistics:
    """Test interaction statistics and analysis functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())

        # Patch the session directory to use our temp directory
        self.session_dir_patcher = patch(
            "session_notes.server.get_session_directory",
            return_value=self.test_dir / ".claude" / "session-notes" / self.session_id,
        )
        self.session_dir_patcher.start()

        # Create a test session and agent
        _start_session_impl(self.session_id, auto_collect_environment=False)
        self.agent_id = "stats-test-agent"
        _register_agent_impl(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_type="statistics-test",
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.session_dir_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_interaction_statistics_empty(self):
        """Test interaction statistics for agent with no interactions."""
        stats = get_agent_interaction_statistics(self.session_id, self.agent_id)

        assert stats["total_interactions"] == 0
        assert stats["interaction_types"] == {}
        assert stats["success_rate"] == 0.0
        assert stats["avg_execution_time"] is None
        assert stats["workflow_stages"] == []
        assert stats["communication_count"] == 0
        assert stats["decision_count"] == 0

    def test_interaction_statistics_comprehensive(self):
        """Test comprehensive interaction statistics calculation."""
        # Log various types of interactions
        interactions_data = [
            {
                "action": "analyze-code",
                "interaction_type": "analysis",
                "execution_time": 1000.0,
                "success": True,
                "workflow_stage": "code_review",
            },
            {
                "action": "make-decision",
                "interaction_type": "decision",
                "execution_time": 500.0,
                "success": True,
                "workflow_stage": "approval",
                "decision_context": {"alternatives": ["approve", "reject"]},
            },
            {
                "action": "send-notification",
                "interaction_type": "communication",
                "execution_time": 200.0,
                "success": False,
                "communication_data": {"channels": ["email"]},
            },
            {
                "action": "analyze-security",
                "interaction_type": "analysis",
                "execution_time": 1500.0,
                "success": True,
                "workflow_stage": "security_check",
            },
        ]

        for data in interactions_data:
            _log_agent_interaction_impl(
                session_id=self.session_id,
                agent_id=self.agent_id,
                agent_type="statistics-test",
                **data,
            )

        # Get statistics
        stats = get_agent_interaction_statistics(self.session_id, self.agent_id)

        # Verify basic counts
        assert stats["total_interactions"] == 4
        assert stats["success_rate"] == 0.75  # 3 out of 4 successful

        # Verify interaction type breakdown
        expected_types = {"analysis": 2, "decision": 1, "communication": 1}
        assert stats["interaction_types"] == expected_types

        # Verify execution time average
        expected_avg = (1000.0 + 500.0 + 200.0 + 1500.0) / 4
        assert stats["avg_execution_time"] == expected_avg

        # Verify workflow stages
        expected_stages = ["code_review", "approval", "security_check"]
        assert set(stats["workflow_stages"]) == set(expected_stages)

        # Verify communication and decision counts
        assert stats["communication_count"] == 1
        assert stats["decision_count"] == 1

    def test_last_activity_includes_interactions(self):
        """Test that last activity tracking includes interaction timestamps."""
        # Initially no activity
        assert get_last_agent_activity(self.session_id, self.agent_id) is None

        # Log an interaction
        _log_agent_interaction_impl(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_type="statistics-test",
            action="test-interaction",
        )

        # Should have last activity timestamp
        last_activity = get_last_agent_activity(self.session_id, self.agent_id)
        assert last_activity is not None

        # Parse timestamp to verify it's recent
        activity_time = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        time_diff = (now - activity_time).total_seconds()
        assert time_diff < 60  # Should be within last minute


class TestAgentMetadataIntegration:
    """Test integration of interaction tracking with agent metadata."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())

        # Patch the session directory to use our temp directory
        self.session_dir_patcher = patch(
            "session_notes.server.get_session_directory",
            return_value=self.test_dir / ".claude" / "session-notes" / self.session_id,
        )
        self.session_dir_patcher.start()

        # Create a test session and agent
        _start_session_impl(self.session_id, auto_collect_environment=False)
        self.agent_id = "integration-test-agent"
        _register_agent_impl(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_type="integration-test",
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.session_dir_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_agent_metadata_includes_interaction_statistics(self):
        """Test that agent metadata includes interaction statistics."""
        # Log some interactions
        _log_agent_interaction_impl(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_type="integration-test",
            action="interaction-1",
            interaction_type="analysis",
            auto_register=False,
        )
        _log_agent_interaction_impl(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_type="integration-test",
            action="interaction-2",
            interaction_type="decision",
            auto_register=False,
        )

        metadata = _get_agent_metadata_impl(self.session_id, self.agent_id)

        assert "statistics" in metadata
        assert "interactions" in metadata["statistics"]

        interaction_stats = metadata["statistics"]["interactions"]
        assert interaction_stats["total_interactions"] == 2
        assert interaction_stats["interaction_types"]["analysis"] == 1
        assert interaction_stats["interaction_types"]["decision"] == 1
        assert interaction_stats["success_rate"] == 1.0

    def test_session_includes_interaction_data(self):
        """Test that session data includes interaction data."""
        # Log an interaction
        _log_agent_interaction_impl(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_type="integration-test",
            action="session-integration-test",
            interaction_type="workflow",
            auto_register=False,
        )

        # Get session data
        session_data = _get_session_impl(self.session_id)

        assert "agents" in session_data
        assert self.agent_id in session_data["agents"]

        agent_data = session_data["agents"][self.agent_id]
        assert "interactions" in agent_data
        assert len(agent_data["interactions"]) == 1

        interaction = agent_data["interactions"][0]
        assert interaction["action"] == "session-integration-test"
        assert interaction["interaction_type"] == "workflow"


class TestInteractionWorkflows:
    """Test complex interaction workflows and relationships."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())

        # Patch the session directory to use our temp directory
        self.session_dir_patcher = patch(
            "session_notes.server.get_session_directory",
            return_value=self.test_dir / ".claude" / "session-notes" / self.session_id,
        )
        self.session_dir_patcher.start()

        # Create a test session and agent
        _start_session_impl(self.session_id, auto_collect_environment=False)
        self.agent_id = "workflow-test-agent"
        _register_agent_impl(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_type="workflow-test",
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.session_dir_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_hierarchical_interactions(self):
        """Test hierarchical parent-child interaction relationships."""
        # Log parent interaction
        parent_result = _log_agent_interaction_impl(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_type="workflow-test",
            action="parent-workflow",
            interaction_type="workflow",
            workflow_stage="orchestration",
            auto_register=False,
        )

        # Extract parent interaction ID from result
        import re

        match = re.search(r"ID: ([a-f0-9\-]+)", parent_result)
        assert match
        parent_id = match.group(1)

        # Log child interactions
        for i in range(2):
            _log_agent_interaction_impl(
                session_id=self.session_id,
                agent_id=self.agent_id,
                agent_type="workflow-test",
                action=f"child-task-{i}",
                interaction_type="analysis",
                parent_interaction_id=parent_id,
                workflow_stage="execution",
                auto_register=False,
            )

        # Verify relationships
        agent_dir = get_agent_directory(self.session_id, self.agent_id)
        interactions = load_json_data(agent_dir / "interactions.json", [])

        assert len(interactions) == 3

        # Find parent and children
        parent_interaction = next(
            i for i in interactions if i["action"] == "parent-workflow"
        )
        child_interactions = [
            i for i in interactions if i["parent_interaction_id"] == parent_id
        ]

        assert len(child_interactions) == 2
        assert all(
            child["workflow_stage"] == "execution" for child in child_interactions
        )
        assert parent_interaction["workflow_stage"] == "orchestration"

    def test_complex_decision_workflow(self):
        """Test complex decision-making workflow with multiple stages."""
        # Simulate a code review decision workflow
        workflow_stages = [
            {
                "action": "receive-pr",
                "interaction_type": "communication",
                "stage": "intake",
                "context": {"pr_id": "123", "author": "dev1"},
            },
            {
                "action": "analyze-diff",
                "interaction_type": "analysis",
                "stage": "analysis",
                "execution_time": 2000.0,
                "result": {"files_changed": 5, "complexity_score": 7.2},
            },
            {
                "action": "make-decision",
                "interaction_type": "decision",
                "stage": "decision",
                "decision_context": {
                    "alternatives": ["approve", "request_changes", "reject"],
                    "criteria": ["quality", "security", "performance"],
                    "scores": {"quality": 8, "security": 9, "performance": 7},
                    "chosen": "approve",
                    "reasoning": "Meets all criteria thresholds",
                },
            },
            {
                "action": "notify-outcome",
                "interaction_type": "communication",
                "stage": "notification",
                "communication_data": {
                    "channels": ["github", "slack"],
                    "recipients": ["dev1", "team-lead"],
                },
            },
        ]

        interaction_ids = []
        for stage_data in workflow_stages:
            result = _log_agent_interaction_impl(
                session_id=self.session_id,
                agent_id=self.agent_id,
                agent_type="workflow-test",
                workflow_stage=stage_data["stage"],
                auto_register=False,
                **{k: v for k, v in stage_data.items() if k != "stage"},
            )

            # Extract interaction ID
            import re

            match = re.search(r"ID: ([a-f0-9\-]+)", result)
            assert match
            interaction_ids.append(match.group(1))

        # Verify workflow was logged correctly
        agent_dir = get_agent_directory(self.session_id, self.agent_id)
        interactions = load_json_data(agent_dir / "interactions.json", [])

        assert len(interactions) == 4

        # Verify workflow stages are in correct order
        stages = [i["workflow_stage"] for i in interactions]
        expected_stages = ["intake", "analysis", "decision", "notification"]
        assert stages == expected_stages

        # Verify decision context was captured
        decision_interaction = next(
            i for i in interactions if i["workflow_stage"] == "decision"
        )
        assert decision_interaction["decision_context"]["chosen"] == "approve"
        assert len(decision_interaction["decision_context"]["alternatives"]) == 3

        # Verify communication data was captured
        comm_interactions = [
            i for i in interactions if i["interaction_type"] == "communication"
        ]
        assert len(comm_interactions) == 2

        notification_interaction = next(
            i for i in comm_interactions if i["workflow_stage"] == "notification"
        )
        assert "github" in notification_interaction["communication_data"]["channels"]


if __name__ == "__main__":
    pytest.main([__file__])
