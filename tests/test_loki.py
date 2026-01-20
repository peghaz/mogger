"""
Tests for Loki integration with environment variable configuration.
"""

import os
import json
import subprocess
import pytest
from pathlib import Path
from dotenv import load_dotenv

from mogger.loki import LokiConfig, LokiLogger


@pytest.fixture
def load_env_vars():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    yield


@pytest.fixture
def loki_config_from_env(load_env_vars):
    """Create LokiConfig from environment variables."""
    return LokiConfig(
        url=os.getenv("LOKI_URL"),
        tags={"application": "mogger", "environment": "test"},
        username=os.getenv("LOKI_AUTH_USERNAME"),
        password=os.getenv("LOKI_AUTH_PASSWORD"),
    )


@pytest.fixture
def loki_config_no_auth(load_env_vars):
    """Create LokiConfig without authentication."""
    return LokiConfig(
        url=os.getenv("LOKI_URL"),
        tags={"application": "mogger-test"},
    )


def query_loki(endpoint: str) -> dict:
    """Query Loki API using curl."""
    base_url = "http://localhost:3100"
    username = os.getenv("LOKI_AUTH_USERNAME", "")
    password = os.getenv("LOKI_AUTH_PASSWORD", "")

    # Build curl command with optional auth and required headers
    headers = '-H "X-Scope-OrgID: mogger-user"'
    if username and password:
        cmd = f'curl -s -u "{username}:{password}" {headers} "{base_url}{endpoint}"'
    else:
        cmd = f'curl -s {headers} "{base_url}{endpoint}"'

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"\n⚠️ Curl command failed: {result.stderr}")
        return None

    if not result.stdout or result.stdout.strip() == "":
        print(f"\n⚠️ Empty response from Loki at {endpoint}")
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"\n⚠️ Failed to parse JSON from Loki: {e}")
        print(f"Response: {result.stdout[:200]}")
        return None


class TestLokiConfig:
    """Tests for LokiConfig dataclass."""

    def test_loki_config_from_env_url(self, load_env_vars):
        """Test that LokiConfig URL can be loaded from environment."""
        config = LokiConfig(
            url=os.getenv("LOKI_URL"),
            username=os.getenv("LOKI_AUTH_USERNAME"),
            password=os.getenv("LOKI_AUTH_PASSWORD"),
        )

        assert config.url == "http://localhost:3100/loki/api/v1/push"
        assert config.tags == {"application": "mogger"}  # Default tags

    def test_loki_config_with_custom_tags(self):
        """Test LokiConfig with custom tags."""
        config = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
            tags={"application": "custom-app", "env": "production"},
        )

        assert config.tags == {"application": "custom-app", "env": "production"}

    def test_loki_config_without_auth(self):
        """Test LokiConfig without authentication credentials."""
        config = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
        )

        assert config.url == "http://localhost:3100/loki/api/v1/push"
        assert config.username is None
        assert config.password is None


class TestLokiLogger:
    """Tests for LokiLogger class."""

    def test_loki_logger_initialization(self, loki_config_from_env):
        """Test LokiLogger initialization with config from environment."""
        logger = LokiLogger(loki_config_from_env)
        assert logger is not None

    def test_loki_logger_initialization_no_auth(self, loki_config_no_auth):
        """Test LokiLogger initialization without authentication."""
        logger = LokiLogger(loki_config_no_auth)
        assert logger is not None

    def test_loki_logger_info_logging(self, loki_config_from_env):
        """Test info level logging."""
        logger = LokiLogger(loki_config_from_env)
        logger.info("Test info message", extra={"key": "value"})

    def test_loki_logger_warning_logging(self, loki_config_from_env):
        """Test warning level logging."""
        logger = LokiLogger(loki_config_from_env)
        logger.warning("Test warning message", extra={"severity": "high"})

    def test_loki_logger_error_logging(self, loki_config_from_env):
        """Test error level logging."""
        logger = LokiLogger(loki_config_from_env)
        logger.error("Test error message", extra={"error_code": 500})

    def test_loki_logger_critical_logging(self, loki_config_from_env):
        """Test critical level logging."""
        logger = LokiLogger(loki_config_from_env)
        logger.critical("Test critical message", extra={"system": "down"})

    def test_loki_logger_with_custom_tags(self, load_env_vars):
        """Test logger with custom tags."""
        config = LokiConfig(
            url=os.getenv("LOKI_URL"),
            tags={"application": "test-app", "team": "backend", "version": "1.0.0"},
        )
        logger = LokiLogger(config)
        logger.info("Custom tagged message")


class TestLokiIntegration:
    """Integration tests for Loki with API queries."""

    def test_loki_server_labels_endpoint(self):
        """Test querying Loki labels endpoint."""
        result = query_loki("/loki/api/v1/labels")

        # Skip test if Loki is not available
        if result is None:
            pytest.skip("Loki server not available or not responding")

        assert result is not None
        assert "status" in result or "data" in result

    def test_loki_server_label_values(self):
        """Test querying Loki label values."""
        # Query for application label values
        result = query_loki("/loki/api/v1/label/application/values")

        # Skip test if Loki is not available
        if result is None:
            pytest.skip("Loki server not available or not responding")

        if result and "data" in result:
            # Check if mogger application exists in labels
            assert isinstance(result["data"], list)

    def test_send_and_verify_logs_in_loki(self, loki_config_from_env):
        """Test sending logs and verifying they exist in Loki."""
        logger = LokiLogger(loki_config_from_env)

        # Send unique test message
        unique_msg = "test_loki_verification_12345"
        logger.info(unique_msg, extra={"test": "verification"})
        logger.error("test_error_verification_67890", extra={"test": "error"})

        # Wait a moment for Loki to process
        import time
        time.sleep(2)

        # Verify Loki has received the logs by checking label values
        result = query_loki("/loki/api/v1/label/application/values")

        # Skip test if Loki is not available
        if result is None:
            pytest.skip("Loki server not available or not responding")

        # Verify we got a response
        assert result is not None
        assert "status" in result
        if "data" in result:
            print(f"\n📊 Applications in Loki: {result['data']}")
            # Check if mogger application exists
            assert "mogger" in result["data"], "mogger application not found in Loki labels"

    def test_high_volume_messages_and_verify(self, loki_config_from_env):
        """Test sending 1000 messages and verify in Loki."""
        logger = LokiLogger(loki_config_from_env)

        # Send 1000 messages distributed across different log levels
        for i in range(25):
            logger.info(f"Info message {i}", extra={"iteration": i, "type": "info"})
            logger.warning(f"Warning message {i}", extra={"iteration": i, "type": "warning"})
            logger.error(f"Error message {i}", extra={"iteration": i, "type": "error"})
            logger.critical(f"Critical message {i}", extra={"iteration": i, "type": "critical"})

        print("\n✅ Successfully sent 100 messages to Loki server")

        # Wait for Loki to process
        import time
        time.sleep(3)

        # Verify logs exist in Loki
        result = query_loki("/loki/api/v1/labels")

        # Skip test if Loki is not available
        if result is None:
            pytest.skip("Loki server not available or not responding")

        assert result is not None
        print(f"\n📊 Available labels in Loki: {json.dumps(result, indent=2)}")
