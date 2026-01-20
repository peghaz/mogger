"""
Pytest configuration and fixtures for Mogger tests.
"""

import os
import subprocess
from pathlib import Path

import pytest


def pytest_sessionstart(session):
    """
    Hook that runs before the test session starts.
    Automatically installs the package in editable mode.
    """
    project_root = Path(__file__).parent.parent
    print("\n🔧 Installing mogger package in editable mode...")

    try:
        result = subprocess.run(
            ["uv", "pip", "install", "-e", "."],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Package installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install package: {e.stderr}")
        raise


@pytest.fixture
def test_config_path():
    """Return path to test configuration file."""
    return Path(__file__).parent / "test_config.yaml"


@pytest.fixture
def test_db_path():
    """Return path to test database file."""
    return Path(__file__).parent.parent / "mogger_test_logs.db"


@pytest.fixture
def clean_test_db(test_db_path):
    """Remove test database before tests (but keep it after for inspection)."""
    # Remove before test if it exists from previous run
    if test_db_path.exists():
        test_db_path.unlink()

    yield

    # Keep the database after tests for inspection
    # It will be deleted in the next test run


from mogger import Mogger


@pytest.fixture
def logger(test_config_path, clean_test_db):
    """Create a Mogger instance for testing."""
    mogger = Mogger(test_config_path)
    yield mogger
    if mogger is not None:
        mogger.close()


@pytest.fixture
def logger_with_terminal(test_config_path, clean_test_db):
    """Create a Mogger instance with terminal output enabled."""
    mogger = Mogger(test_config_path)
    mogger.set_terminal(True)
    yield mogger
    if mogger is not None:
        mogger.close()
