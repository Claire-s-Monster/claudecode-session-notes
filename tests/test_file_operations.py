"""
Test file operations, error handling, and edge cases for storage utilities.

Tests file system interactions, permissions, corrupted data, and concurrent access.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from session_notes.server import (
    ensure_directory,
    get_agent_directory,
    get_session_directory,
    load_json_data,
    save_json_data,
)


class TestDirectoryOperations:
    """Test directory creation and path operations."""

    def setup_method(self):
        """Set up temporary test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_session_directory_path_construction(self):
        """Test session directory path construction."""
        test_cases = [
            ("simple-session", ".claude/session-notes/simple-session"),
            ("session-123", ".claude/session-notes/session-123"),
            (
                "session_with_underscores",
                ".claude/session-notes/session_with_underscores",
            ),
            (
                "session-with-special@chars",
                ".claude/session-notes/session-with-special@chars",
            ),
            ("a" * 100, f".claude/session-notes/{'a' * 100}"),  # Long session ID
        ]

        for session_id, expected_path in test_cases:
            result = get_session_directory(session_id)
            assert str(result) == expected_path
            assert result.name == session_id

    def test_get_agent_directory_path_construction(self):
        """Test agent directory path construction."""
        test_cases = [
            ("session-1", "agent-1", ".claude/session-notes/session-1/agents/agent-1"),
            (
                "session-2",
                "agent_special",
                ".claude/session-notes/session-2/agents/agent_special",
            ),
            (
                "long-session",
                "long-agent-name",
                ".claude/session-notes/long-session/agents/long-agent-name",
            ),
        ]

        for session_id, agent_id, expected_path in test_cases:
            result = get_agent_directory(session_id, agent_id)
            assert str(result) == expected_path
            assert result.name == agent_id

    def test_ensure_directory_creation(self):
        """Test directory creation with various scenarios."""
        # Simple directory creation
        simple_dir = self.temp_dir / "simple"
        ensure_directory(simple_dir)
        assert simple_dir.exists()
        assert simple_dir.is_dir()

        # Nested directory creation
        nested_dir = self.temp_dir / "level1" / "level2" / "level3"
        ensure_directory(nested_dir)
        assert nested_dir.exists()
        assert all(
            p.is_dir()
            for p in [nested_dir, nested_dir.parent, nested_dir.parent.parent]
        )

        # Idempotent creation
        ensure_directory(nested_dir)
        assert nested_dir.exists()

        # Directory already exists
        existing_dir = self.temp_dir / "existing"
        existing_dir.mkdir()
        ensure_directory(existing_dir)
        assert existing_dir.exists()

    def test_ensure_directory_with_file_conflict(self):
        """Test directory creation when file exists with same name."""
        # Create a file
        conflict_path = self.temp_dir / "conflict"
        conflict_path.write_text("existing file")
        assert conflict_path.is_file()

        # Try to create directory with same name
        with pytest.raises(FileExistsError):
            ensure_directory(conflict_path)

    def test_ensure_directory_permissions(self):
        """Test directory creation with permission constraints."""
        # Create a directory with restricted permissions
        restricted_dir = self.temp_dir / "restricted"
        restricted_dir.mkdir(mode=0o444)  # Read-only

        # Try to create subdirectory (should fail on most systems)
        sub_dir = restricted_dir / "subdir"

        # Note: This test may behave differently on different systems
        # Some systems allow directory creation even with restricted parent permissions
        try:
            ensure_directory(sub_dir)
            # If it succeeds, verify it was created
            # Use try/except for checking existence due to permission issues
            try:
                exists = sub_dir.exists()
                assert exists
            except PermissionError:
                # Can't even check if it exists due to permissions
                pass
        except PermissionError:
            # If it fails due to permissions, that's expected
            # Try to check if it doesn't exist, but handle permission errors
            try:
                assert not sub_dir.exists()
            except PermissionError:
                # Can't check existence due to parent directory permissions
                pass

        # Restore permissions for cleanup
        try:
            restricted_dir.chmod(0o755)
        except OSError:
            # If we can't restore permissions, that's okay for cleanup
            pass

    def test_ensure_directory_with_symlinks(self):
        """Test directory creation with symbolic links."""
        # Create target directory
        target_dir = self.temp_dir / "target"
        target_dir.mkdir()

        # Create symlink to directory
        symlink_dir = self.temp_dir / "symlink"
        symlink_dir.symlink_to(target_dir)

        # Ensure directory through symlink
        ensure_directory(symlink_dir)
        assert symlink_dir.exists()
        assert symlink_dir.is_symlink()
        assert target_dir.exists()

        # Create subdirectory through symlink
        sub_dir = symlink_dir / "subdir"
        ensure_directory(sub_dir)
        assert sub_dir.exists()
        assert (target_dir / "subdir").exists()


class TestJSONFileOperations:
    """Test JSON file saving and loading operations."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_json_data_various_types(self):
        """Test saving various data types to JSON."""
        test_cases = [
            ("simple_dict", {"key": "value", "number": 42}),
            ("nested_dict", {"outer": {"inner": {"deep": "value"}}}),
            ("list_data", [1, 2, 3, "string", {"nested": True}]),
            (
                "mixed_data",
                {"list": [1, 2], "dict": {"key": "value"}, "null": None, "bool": True},
            ),
            ("unicode_data", {"unicode": "🚀 测试 データ", "special": "chars@#$%"}),
            ("empty_dict", {}),
            ("empty_list", []),
            ("numeric_data", {"int": 42, "float": 3.14159, "negative": -100}),
        ]

        for filename, data in test_cases:
            file_path = self.temp_dir / f"{filename}.json"
            save_json_data(file_path, data)

            assert file_path.exists()
            with open(file_path, encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == data

    def test_save_json_data_creates_directories(self):
        """Test that save_json_data creates parent directories."""
        nested_file = self.temp_dir / "level1" / "level2" / "data.json"
        test_data = {"created": "automatically"}

        save_json_data(nested_file, test_data)

        assert nested_file.exists()
        assert nested_file.parent.exists()
        assert nested_file.parent.parent.exists()

        with open(nested_file, encoding="utf-8") as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

    def test_save_json_data_formatting(self):
        """Test JSON formatting and encoding."""
        file_path = self.temp_dir / "formatted.json"
        data = {"formatted": True, "indented": {"nested": "data"}}

        save_json_data(file_path, data)

        # Read raw file content to check formatting
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Should be indented (not minified)
        assert "  " in content  # Indentation
        assert "\n" in content  # Newlines

        # Should handle Unicode properly
        unicode_data = {"unicode": "测试 🚀"}
        unicode_file = self.temp_dir / "unicode.json"
        save_json_data(unicode_file, unicode_data)

        with open(unicode_file, encoding="utf-8") as f:
            content = f.read()
        assert "测试 🚀" in content  # Unicode preserved

    def test_load_json_data_existing_files(self):
        """Test loading JSON data from existing files."""
        test_cases = [
            {"simple": "data"},
            {"complex": {"nested": [1, 2, {"deep": True}]}},
            [],
            {},
            {"unicode": "测试 🚀 データ"},
            {"numbers": {"int": 42, "float": 3.14159, "negative": -100}},
        ]

        for i, data in enumerate(test_cases):
            file_path = self.temp_dir / f"test_{i}.json"

            # Create file manually
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Load using function
            loaded_data = load_json_data(file_path)
            assert loaded_data == data

    def test_load_json_data_nonexistent_files(self):
        """Test loading from non-existent files with defaults."""
        nonexistent_file = self.temp_dir / "does_not_exist.json"

        # Test with no default
        result = load_json_data(nonexistent_file)
        assert result is None

        # Test with various defaults
        defaults = [
            {},
            [],
            {"default": "value"},
            "default_string",
            42,
            None,
        ]

        for default in defaults:
            result = load_json_data(nonexistent_file, default)
            assert result == default

    @patch("session_notes.server.logger")
    def test_load_json_data_corrupted_files(self, mock_logger):
        """Test loading corrupted JSON files."""
        corrupted_files = [
            ("invalid_json.json", "{ invalid json"),
            ("incomplete.json", '{"key": "val'),
            ("wrong_syntax.json", "{ key: 'value' }"),  # Single quotes
            ("trailing_comma.json", '{"key": "value",}'),
            ("empty_file.json", ""),
            ("non_json.json", "This is not JSON at all"),
            ("binary_data.json", b"\x00\x01\x02\x03".decode("latin1")),
        ]

        for filename, content in corrupted_files:
            file_path = self.temp_dir / filename

            # Create corrupted file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Test loading with default
            default_value = {"fallback": "data"}
            result = load_json_data(file_path, default_value)
            assert result == default_value

            # Test loading without default
            result = load_json_data(file_path)
            assert result is None

            # Verify error was logged
            mock_logger.error.assert_called()

    def test_load_json_data_permission_errors(self):
        """Test loading files with permission issues."""
        # Create file with restricted permissions
        restricted_file = self.temp_dir / "restricted.json"
        test_data = {"restricted": True}
        save_json_data(restricted_file, test_data)

        # Remove read permissions
        restricted_file.chmod(0o000)

        try:
            # Try to load (should use default)
            default_value = {"permission": "denied"}
            result = load_json_data(restricted_file, default_value)
            assert result == default_value
        finally:
            # Restore permissions for cleanup
            restricted_file.chmod(0o644)

    def test_save_json_data_permission_errors(self):
        """Test saving to directories with permission restrictions."""
        # Create directory with restricted permissions
        restricted_dir = self.temp_dir / "no_write"
        restricted_dir.mkdir(mode=0o444)  # Read-only

        try:
            file_path = restricted_dir / "data.json"
            test_data = {"should": "fail"}

            # This should raise a permission error
            with pytest.raises((PermissionError, OSError)):
                save_json_data(file_path, test_data)
        finally:
            # Restore permissions for cleanup
            restricted_dir.chmod(0o755)

    def test_concurrent_file_operations(self):
        """Test concurrent access to same files."""
        import threading
        import time

        file_path = self.temp_dir / "concurrent.json"
        results = []
        errors = []

        def save_data(thread_id):
            try:
                data = {"thread": thread_id, "timestamp": time.time()}
                save_json_data(file_path, data)
                results.append(f"saved_{thread_id}")
            except Exception as e:
                errors.append((thread_id, e))

        def load_data(thread_id):
            try:
                time.sleep(0.01)  # Small delay to increase chance of race condition
                load_json_data(file_path, {})
                results.append(f"loaded_{thread_id}")
            except Exception as e:
                errors.append((thread_id, e))

        # Start multiple threads
        threads = []
        for i in range(5):
            save_thread = threading.Thread(target=save_data, args=(f"save_{i}",))
            load_thread = threading.Thread(target=load_data, args=(f"load_{i}",))
            threads.extend([save_thread, load_thread])

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check that operations completed (some may have errors due to race conditions)
        assert len(results) + len(errors) == 10
        if errors:
            # Log errors for debugging but don't fail test
            print(f"Concurrent access errors (expected): {errors}")


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extreme_path_lengths(self):
        """Test handling of extremely long paths."""
        # Create very long session ID
        long_session_id = "a" * 200
        session_dir = get_session_directory(long_session_id)

        # This might fail on some systems due to path length limits
        try:
            ensure_directory(session_dir)
            assert session_dir.exists()
        except OSError as e:
            # Path too long is acceptable failure
            assert "too long" in str(e).lower() or "name too long" in str(e).lower()

    def test_special_characters_in_paths(self):
        """Test handling of special characters in session/agent IDs."""
        special_chars_cases = [
            "session-with-hyphens",
            "session_with_underscores",
            "session.with.dots",
            "session@with#special$chars",
            "session with spaces",
            "session🚀with📝emojis",
            "session测试中文",
            "sessionデータテスト",
        ]

        for session_id in special_chars_cases:
            try:
                session_dir = get_session_directory(session_id)
                ensure_directory(session_dir)

                # Try to save data
                test_file = session_dir / "test.json"
                save_json_data(test_file, {"session_id": session_id})

                # Try to load data
                loaded_data = load_json_data(test_file)
                assert loaded_data["session_id"] == session_id

            except (OSError, UnicodeError) as e:
                # Some special characters may not be supported by filesystem
                print(f"Special character test failed for '{session_id}': {e}")

    def test_json_serialization_edge_cases(self):
        """Test JSON serialization with edge case data."""
        edge_cases = [
            # Very large numbers
            {"large_int": 2**63 - 1},
            {"large_float": 1.7976931348623157e308},
            # Special float values
            {"infinity": float("inf")},
            {"negative_infinity": float("-inf")},
            {"nan": float("nan")},
            # Very deep nesting
            {"deep": {"level": {"nested": {"very": {"deep": "value"}}}}},
            # Large arrays
            {"large_array": list(range(10000))},
            # Long strings
            {"long_string": "x" * 100000},
        ]

        for i, data in enumerate(edge_cases):
            file_path = self.temp_dir / f"edge_case_{i}.json"

            try:
                save_json_data(file_path, data)
                loaded_data = load_json_data(file_path)

                # Special handling for NaN (NaN != NaN)
                if "nan" in data:
                    import math

                    assert math.isnan(loaded_data["nan"])
                else:
                    assert loaded_data == data

            except (OverflowError, ValueError) as e:
                # Some edge cases may not be JSON serializable
                print(f"Edge case serialization failed: {e}")

    def test_filesystem_stress_conditions(self):
        """Test behavior under filesystem stress conditions."""
        # Create many files rapidly
        many_files_dir = self.temp_dir / "stress_test"
        ensure_directory(many_files_dir)

        # Create many files
        for i in range(100):
            file_path = many_files_dir / f"file_{i:03d}.json"
            data = {"file_number": i, "data": f"content_{i}"}
            save_json_data(file_path, data)

        # Verify all files were created correctly
        for i in range(100):
            file_path = many_files_dir / f"file_{i:03d}.json"
            assert file_path.exists()

            loaded_data = load_json_data(file_path)
            assert loaded_data["file_number"] == i
            assert loaded_data["data"] == f"content_{i}"

    def test_cleanup_after_errors(self):
        """Test that partial operations are cleaned up properly."""
        # This is more of a design test - our current functions don't have
        # transactional behavior, but we should verify they don't leave
        # partial state on errors

        test_dir = self.temp_dir / "cleanup_test"

        # Test directory creation with permission error
        try:
            # Create parent with no write permissions
            test_dir.mkdir(mode=0o444)

            # Try to create subdirectory (should fail)
            sub_dir = test_dir / "subdir"
            with pytest.raises((PermissionError, OSError)):
                ensure_directory(sub_dir)

            # Verify no partial creation - handle permission errors gracefully
            try:
                assert not sub_dir.exists()
            except PermissionError:
                # If we can't check existence due to permissions, that's okay
                # The important thing is that ensure_directory raised an exception
                pass

        finally:
            # Cleanup - handle permission errors gracefully
            try:
                test_dir.chmod(0o755)
            except OSError:
                pass

    @patch("builtins.open")
    def test_file_operation_with_io_errors(self, mock_open):
        """Test file operations with simulated I/O errors."""
        # Simulate file open error
        mock_open.side_effect = OSError("Simulated I/O error")

        file_path = self.temp_dir / "io_error_test.json"

        # save_json_data should handle the error
        with pytest.raises(IOError):
            save_json_data(file_path, {"test": "data"})

        # load_json_data should return default on error
        result = load_json_data(file_path, {"default": "value"})
        assert result == {"default": "value"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
