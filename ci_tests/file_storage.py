#!/usr/bin/env python3
"""File Storage Operations Test"""

import sys
sys.path.insert(0, "src")

def main():
    print("Testing file storage operations...")
    
    try:
        from session_notes.server import get_session_directory, save_json_data, load_json_data, ensure_directory
        from pathlib import Path
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            session_dir = get_session_directory("test-session")
            ensure_directory(session_dir)
            assert session_dir.exists(), "Session directory not created"
            print("Directory creation works")

            test_data = {"test": "data", "number": 42}
            json_file = session_dir / "test.json"
            save_json_data(json_file, test_data)
            assert json_file.exists(), "JSON file not created"

            loaded_data = load_json_data(json_file)
            assert loaded_data == test_data, "JSON data mismatch"
            print("JSON operations work")
        
        print("File storage operations complete")
        return 0
        
    except Exception as e:
        print("Storage operations failed:", str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())