#!/usr/bin/env python3

import asyncio
from session_notes.server import app


async def main():
    tools = await app.get_tools()
    resources = await app.get_resources()

    print("Registered Tools:")
    for tool in tools:
        print(f"  - {tool} (type: {type(tool)})")

    print("\nRegistered Resources:")
    for resource in resources:
        print(f"  - {resource} (type: {type(resource)})")

    print(f"\nApp name: {app.name}")
    print(f"App has version attr: {hasattr(app, 'version')}")

    # Check what attributes tools have
    if tools:
        first_tool = tools[0]
        print(f"First tool attributes: {dir(first_tool)}")

    # Check what attributes resources have
    if resources:
        first_resource = resources[0]
        print(f"First resource attributes: {dir(first_resource)}")

    # Test calling a tool directly
    try:
        from session_notes.server import start_session

        result = start_session("test-session-123")
        print(f"Direct tool call result: {result}")
    except Exception as e:
        print(f"Error calling tool directly: {e}")

    # Test getting a resource directly
    try:
        from session_notes.server import get_session

        result = get_session("test-session")
        print(f"Direct resource call result type: {type(result)}")
    except Exception as e:
        print(f"Error calling resource directly: {e}")


if __name__ == "__main__":
    asyncio.run(main())
