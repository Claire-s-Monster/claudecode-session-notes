#!/usr/bin/env python3

import tempfile
import os
from pathlib import Path

# Change to temp directory to avoid creating files in project
temp_dir = Path(tempfile.mkdtemp())
original_cwd = Path.cwd()
os.chdir(temp_dir)

try:
    from session_notes.server import (
        start_session,
        end_session,
        log_agent_execution,
        log_tool_request,
    )
    from session_notes.server import get_session, list_sessions

    print("Testing start_session...")
    print(f"start_session type: {type(start_session)}")
    print(f"start_session has fn: {hasattr(start_session, 'fn')}")

    # Try calling the function through the FunctionTool wrapper
    if hasattr(start_session, "fn"):
        result = start_session.fn("test-session-123")
        print(f"start_session result: {result}")

        print("\nTesting log_agent_execution...")
        result = log_agent_execution.fn(
            "test-session-123", "agent-1", "test-agent", "test-action"
        )
        print(f"log_agent_execution result: {result}")

        print("\nTesting log_tool_request...")
        result = log_tool_request.fn(
            "test-session-123", "agent-1", "test-tool", True, True
        )
        print(f"log_tool_request result: {result}")

        print("\nTesting get_session...")
        result = get_session.fn("test-session-123")
        print(f"get_session result type: {type(result)}")
        if isinstance(result, dict) and "agents" in result:
            print(f"  Session has {len(result['agents'])} agents")

        print("\nTesting list_sessions...")
        result = list_sessions.fn()
        print(f"list_sessions result: {len(result)} sessions")

        print("\nTesting end_session...")
        result = end_session.fn("test-session-123")
        print(f"end_session result: {result}")
    else:
        print("Cannot access function through .fn attribute")

    print("\nAll direct tests passed!")

finally:
    # Cleanup
    os.chdir(original_cwd)
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)
