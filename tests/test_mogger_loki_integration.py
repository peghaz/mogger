"""
Tests for Mogger with Loki integration.
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

from mogger import Mogger, LokiConfig


@pytest.fixture
def load_env_vars():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    yield


@pytest.fixture
def test_config_path():
    """Return path to test configuration file."""
    return Path(__file__).parent / "test_config.yaml"


@pytest.fixture
def test_db_path(tmp_path):
    """Return path to temporary test database file."""
    return str(tmp_path / "mogger_test_logs.db")


@pytest.fixture
def loki_config_from_env(load_env_vars):
    """Create LokiConfig from environment variables if available."""
    loki_url = os.getenv("LOKI_URL")
    if not loki_url:
        pytest.skip("LOKI_URL not set in environment")
    
    return LokiConfig(
        url=loki_url,
        tags={"application": "mogger-test", "environment": "test"},
        username=os.getenv("LOKI_AUTH_USERNAME"),
        password=os.getenv("LOKI_AUTH_PASSWORD"),
    )


class TestMoggerLokiIntegration:
    """Tests for Mogger with Loki integration."""

    def test_mogger_without_loki(self, test_config_path, test_db_path):
        """Test Mogger works without Loki config."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        # Should work without Loki
        uuid = mogger.info("Test message without Loki", category="user_actions", user_id="test_user", action="test")
        assert uuid is not None
        
        mogger.close()

    def test_mogger_with_loki_config(self, test_config_path, test_db_path, loki_config_from_env):
        """Test Mogger initialization with Loki config."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_from_env
        )
        
        assert mogger is not None
        mogger.close()

    def test_mogger_logs_to_loki(self, test_config_path, test_db_path, loki_config_from_env):
        """Test that Mogger sends logs to Loki when configured."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_from_env
        )
        
        # Log at different levels
        mogger.debug("Debug message with Loki", category="user_actions", user_id="debug_user", action="debug_action")
        mogger.info("Info message with Loki", category="user_actions", user_id="info_user", action="info_action")
        mogger.warning("Warning message with Loki", category="errors", error_code=400, error_message="Test warning", severity="medium")
        mogger.error("Error message with Loki", category="errors", error_code=500, error_message="Test error", severity="high")
        mogger.critical("Critical message with Loki", category="errors", error_code=503, error_message="Test critical", severity="critical")
        
        mogger.close()

    def test_mogger_loki_with_context(self, test_config_path, test_db_path, loki_config_from_env):
        """Test that context data is sent to Loki."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_from_env
        )
        
        # Set context
        mogger.set_context(request_id="req-12345", user="test_user")
        
        # Log with context - should be sent to Loki
        mogger.info("Message with context", category="user_actions", user_id="context_user", action="login")
        
        mogger.clear_context()
        mogger.close()

    def test_mogger_loki_multiple_logs(self, test_config_path, test_db_path, loki_config_from_env):
        """Test sending multiple logs to Loki."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_from_env
        )
        
        # Send multiple logs
        for i in range(10):
            mogger.info(
                f"Test log message {i}",
                category="system_events",
                event_type="test",
                description=f"Test event {i}"
            )
        
        mogger.close()

    def test_mogger_loki_with_custom_tags(self, test_config_path, test_db_path, load_env_vars):
        """Test Mogger with custom Loki tags."""
        loki_url = os.getenv("LOKI_URL")
        if not loki_url:
            pytest.skip("LOKI_URL not set in environment")
        
        custom_config = LokiConfig(
            url=loki_url,
            tags={
                "application": "mogger-custom",
                "environment": "test",
                "team": "backend",
                "version": "1.0.0"
            },
            username=os.getenv("LOKI_AUTH_USERNAME"),
            password=os.getenv("LOKI_AUTH_PASSWORD"),
        )
        
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=custom_config
        )
        
        mogger.info("Message with custom tags", category="user_actions", user_id="custom_user", action="test")
        mogger.close()
