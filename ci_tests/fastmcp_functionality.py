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
        from session_notes.server import (
            start_session, end_session, log_agent_execution,
            log_tool_request, register_agent
        )
        print("Core tools successfully imported and available")
    except ImportError as e:
        print("Core tool import failed:", str(e))
        sys.exit(1)
    
    try:
        from session_notes.server import SessionInfo, AgentExecution, ToolRequest
        print("Data models successfully imported")
    except ImportError as e:
        print("Data model import failed:", str(e))
        sys.exit(1)
    
    try:
        from session_notes.server import (
            get_session_directory, save_json_data, load_json_data
        )
        print("Utility functions successfully imported")
    except ImportError as e:
        print("Utility function import failed:", str(e))
        sys.exit(1)
    
    print("FastMCP server validation complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())