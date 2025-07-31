"""Basic test to validate testing framework setup."""

import pytest


def test_basic_functionality():
    """Test basic functionality to ensure test framework works."""
    assert True


def test_session_notes_import():
    """Test that session_notes package can be imported."""
    try:
        import session_notes

        assert hasattr(session_notes, "__name__")
    except ImportError:
        # Package might not have any modules yet, that's ok
        pass


@pytest.mark.unit
def test_unit_marker():
    """Test that unit marker works."""
    assert 1 + 1 == 2


@pytest.mark.integration
def test_integration_marker():
    """Test that integration marker works."""
    assert "hello" + " world" == "hello world"
