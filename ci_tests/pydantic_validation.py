#!/usr/bin/env python3
"""Pydantic Model Validation Test"""

import sys

sys.path.insert(0, "src")


def main():
    print("Testing Pydantic model validation...")

    try:
        from datetime import UTC, datetime

        from session_notes.server import AgentExecution, SessionInfo, ToolRequest

        session = SessionInfo(
            session_id="test", timestamp=datetime.now(UTC).isoformat()
        )
        print("SessionInfo validation:", session.session_id)

        execution = AgentExecution(
            agent_id="test-agent",
            agent_type="test",
            timestamp=datetime.now(UTC).isoformat(),
            action="test-action",
        )
        print("AgentExecution validation:", execution.agent_id)

        tool_req = ToolRequest(
            tool_name="test-tool",
            available=True,
            success=True,
            timestamp=datetime.now(UTC).isoformat(),
        )
        print("ToolRequest validation:", tool_req.tool_name)

        print("Pydantic model validation complete")
        return 0

    except Exception as e:
        print("Pydantic validation failed:", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
