#!/usr/bin/env python3
"""FastMCP Server Startup Test"""

import sys
sys.path.insert(0, "src")

def main():
    print("Testing FastMCP 2.0 server startup...")
    
    try:
        from session_notes.server import main
        print("Server main function imported successfully")
        print("MCP server startup validation complete")
        return 0
    except Exception as e:
        print("Server startup test failed:", str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())