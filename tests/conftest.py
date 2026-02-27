"""
Pytest configuration and fixtures for Mogger tests.
"""

import os
import shutil
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
def clean_test_logs(test_config_path):
    """Remove test logs directory before tests."""
    logs_dir = Path(__file__).parent / ".mogger.logs"
    
    # Remove before test if it exists from previous run
    if logs_dir.exists():
        shutil.rmtree(logs_dir)

    yield

    # Keep the logs after tests for inspection
    # They will be deleted in the next test run


from mogger import Mogger


@pytest.fixture
def logger(test_config_path, clean_test_logs):
    """Create a Mogger instance for testing."""
    mogger = Mogger(test_config_path)
    yield mogger


@pytest.fixture
def logger_with_terminal(test_config_path, clean_test_logs):
    """Create a Mogger instance with terminal output enabled."""
    mogger = Mogger(test_config_path)
    mogger.set_terminal(True)
    yield mogger
