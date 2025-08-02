#!/usr/bin/env python3

import sys

print("pytest in sys.modules:", "pytest" in sys.modules)

try:
    from src.session_notes.server import TESTING_MODE
    print("TESTING_MODE:", TESTING_MODE)
except Exception as e:
    print("Error importing TESTING_MODE:", e)

try:
    from src.session_notes.server import analyze_missing_tools
    print("analyze_missing_tools type:", type(analyze_missing_tools))
    print("Has __name__:", hasattr(analyze_missing_tools, '__name__'))
    if hasattr(analyze_missing_tools, '__name__'):
        print("analyze_missing_tools.__name__:", analyze_missing_tools.__name__)
    else:
        print("analyze_missing_tools is a:", analyze_missing_tools.__class__.__name__)
except Exception as e:
    print("Error importing analyze_missing_tools:", e)