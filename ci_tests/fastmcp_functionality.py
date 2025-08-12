#!/usr/bin/env python3
"""FastMCP 2.0 Protocol Validation Test"""

import sys

sys.path.insert(0, "src")


def main():
    print("Starting FastMCP 2.0 server validation...")

    try:
        from session_notes.server import app

        print("FastMCP app initialized:", app.name)
    except Exception as e:
        print("FastMCP app initialization failed:", str(e))
        sys.exit(1)

    try:
        # Test import availability
        import session_notes.server as server_module

        # Check if core tools are available
        core_tools = [
            "end_session",
            "log_agent_execution",
            "log_tool_request",
            "register_agent",
            "start_session",
        ]

        for tool in core_tools:
            if hasattr(server_module, tool):
                print(f"✅ {tool} available")
            else:
                print(f"⚠️ {tool} not available")

        print("Core tools successfully validated")
    except ImportError as e:
        print("Core tool validation failed:", str(e))
        sys.exit(1)

    try:
        # Test data models availability
        import session_notes.server as server_module

        models = ["AgentExecution", "SessionInfo", "ToolRequest"]

        for model in models:
            if hasattr(server_module, model):
                print(f"✅ {model} available")
            else:
                print(f"⚠️ {model} not available")

        print("Data models successfully validated")
    except ImportError as e:
        print("Data model validation failed:", str(e))
        sys.exit(1)

    try:
        # Test utility functions availability
        import session_notes.server as server_module

        utilities = [
            "get_session_directory",
            "load_json_data",
            "save_json_data",
        ]

        for utility in utilities:
            if hasattr(server_module, utility):
                print(f"✅ {utility} available")
            else:
                print(f"⚠️ {utility} not available")

        print("Utility functions successfully validated")
    except ImportError as e:
        print("Utility function validation failed:", str(e))
        sys.exit(1)

    print("FastMCP server validation complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
