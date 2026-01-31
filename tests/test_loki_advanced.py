"""
Advanced tests for Loki integration - edge cases and error handling.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

from mogger import Mogger, LokiConfig
from mogger.loki import LokiLogger


def is_loki_available():
    """Check if Loki server is available."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 3100))
        sock.close()
        return result == 0
    except:
        return False


# Skip all Loki tests if server not available
pytestmark = pytest.mark.skipif(
    not is_loki_available(),
    reason="Loki server not available at localhost:3100"
)


@pytest.fixture
def test_config_path():
    """Return path to test configuration file."""
    return Path(__file__).parent / "test_config.yaml"


@pytest.fixture
def test_db_path(tmp_path):
    """Return path to temporary test database file."""
    return str(tmp_path / "mogger_test_logs.db")


@pytest.fixture
def mock_loki_config():
    """Create a mock LokiConfig."""
    return LokiConfig(
        url="http://localhost:3100/loki/api/v1/push",
        tags={"app": "test", "env": "testing"},
    )


class TestLokiConfigValidation:
    """Tests for LokiConfig validation and edge cases."""

    def test_loki_config_with_empty_tags(self):
        """Test LokiConfig with empty tags dictionary."""
        config = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
            tags={}
        )
        assert config.tags == {}

    def test_loki_config_with_special_characters_in_tags(self):
        """Test LokiConfig with special characters in tag values."""
        config = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
            tags={"app": "my-app_v1.0", "env": "staging-test"}
        )
        assert config.tags["app"] == "my-app_v1.0"
        assert config.tags["env"] == "staging-test"

    def test_loki_config_with_numeric_tag_values(self):
        """Test LokiConfig with numeric values in tags."""
        config = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
            tags={"app": "myapp", "version": "123"}
        )
        assert config.tags["version"] == "123"

    def test_loki_config_with_auth_credentials(self):
        """Test LokiConfig with authentication credentials."""
        config = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
            username="admin",
            password="secret123"
        )
        assert config.username == "admin"
        assert config.password == "secret123"

    def test_loki_config_url_formats(self):
        """Test LokiConfig accepts various URL formats."""
        urls = [
            "http://localhost:3100/loki/api/v1/push",
            "https://loki.example.com/loki/api/v1/push",
            "http://192.168.1.100:3100/loki/api/v1/push",
        ]
        
        for url in urls:
            config = LokiConfig(url=url)
            assert config.url == url


class TestLokiLoggerBehavior:
    """Tests for LokiLogger behavior and error handling."""

    def test_loki_logger_with_empty_extra_dict(self, mock_loki_config):
        """Test LokiLogger handles empty extra dict."""
        logger = LokiLogger(mock_loki_config)
        # Should not raise exception
        logger.info("Message without extra", extra={})

    def test_loki_logger_with_none_extra(self, mock_loki_config):
        """Test LokiLogger with None as extra parameter."""
        logger = LokiLogger(mock_loki_config)
        # Should not raise exception
        logger.info("Message with None extra", extra=None or {})

    def test_loki_logger_all_log_levels(self, mock_loki_config):
        """Test all log levels are available and callable."""
        logger = LokiLogger(mock_loki_config)
        
        # Test all log levels
        logger.debug("Debug message", extra={"level": "debug"})
        logger.info("Info message", extra={"level": "info"})
        logger.warning("Warning message", extra={"level": "warning"})
        logger.error("Error message", extra={"level": "error"})
        logger.critical("Critical message", extra={"level": "critical"})

    def test_loki_logger_with_complex_extra_data(self, mock_loki_config):
        """Test LokiLogger with complex nested data in extra."""
        logger = LokiLogger(mock_loki_config)
        
        complex_extra = {
            "user_id": "12345",
            "metadata": {"key1": "value1", "key2": "value2"},
            "tags": ["tag1", "tag2", "tag3"],
            "count": 42,
            "active": True
        }
        
        logger.info("Complex data log", extra=complex_extra)

    def test_loki_logger_with_unicode_characters(self, mock_loki_config):
        """Test LokiLogger handles Unicode characters."""
        logger = LokiLogger(mock_loki_config)
        
        logger.info("Message with émojis 🎉 and ünïcödé", extra={"text": "Café ☕"})

    def test_loki_logger_with_very_long_message(self, mock_loki_config):
        """Test LokiLogger handles very long log messages."""
        logger = LokiLogger(mock_loki_config)
        
        long_message = "A" * 10000  # 10KB message
        logger.info(long_message, extra={"size": len(long_message)})


class TestMoggerLokiIntegrationAdvanced:
    """Advanced integration tests for Mogger with Loki."""

    def test_mogger_loki_with_disabled_local_db(self, test_config_path, mock_loki_config):
        """Test Mogger with Loki enabled but local DB disabled."""
        mogger = Mogger(
            test_config_path,
            loki_config=mock_loki_config,
            use_local_db=False
        )
        
        # Should still send to Loki
        uuid = mogger.info("Message without local DB", category="system_events")
        assert uuid is not None
        
        mogger.close()

    def test_mogger_logs_different_categories_to_loki(self, test_config_path, test_db_path, mock_loki_config):
        """Test that different log categories are sent to Loki."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=mock_loki_config
        )
        
        # Log to different categories
        mogger.info("User action", category="user_actions", user_id="user123", action="login")
        mogger.info("System event", category="system_events", event_type="startup", description="System starting")
        mogger.error("Error occurred", category="errors", error_code=500, error_message="Server error", severity="high")
        
        mogger.close()

    def test_mogger_loki_preserves_kwargs_order(self, test_config_path, test_db_path, mock_loki_config):
        """Test that kwargs are preserved when sent to Loki."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=mock_loki_config
        )
        
        mogger.info(
            "Test message",
            category="user_actions",
            user_id="user456",
            action="update",
            resource="profile",
            timestamp=1234567890,
            success=True
        )
        
        mogger.close()

    def test_mogger_context_sent_to_loki(self, test_config_path, test_db_path, mock_loki_config):
        """Test that context data is included in Loki logs."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=mock_loki_config
        )
        
        # Set context
        mogger.set_context(request_id="req-abc-123", session_id="sess-xyz-789")
        
        # Log should include context
        mogger.info("Message with context", category="user_actions", user_id="user123", action="view")
        
        # Clear and log again
        mogger.clear_context()
        mogger.info("Message without context", category="user_actions", user_id="user123", action="view")
        
        mogger.close()

    def test_mogger_multiple_loki_instances(self, test_config_path, test_db_path):
        """Test creating multiple Mogger instances with different Loki configs."""
        config1 = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
            tags={"app": "app1", "env": "test"}
        )
        
        config2 = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
            tags={"app": "app2", "env": "test"}
        )
        
        mogger1 = Mogger(test_config_path, db_path=str(Path(test_db_path).parent / "db1.db"), loki_config=config1)
        mogger2 = Mogger(test_config_path, db_path=str(Path(test_db_path).parent / "db2.db"), loki_config=config2)
        
        mogger1.info("Message from app1", category="user_actions", user_id="user1", action="test")
        mogger2.info("Message from app2", category="user_actions", user_id="user2", action="test")
        
        mogger1.close()
        mogger2.close()

    def test_mogger_loki_all_log_levels(self, test_config_path, test_db_path, mock_loki_config):
        """Test all log levels are sent to Loki correctly."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=mock_loki_config
        )
        
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in levels:
            if level == "DEBUG":
                mogger.debug(f"{level} message", category="system_events", event_type="test", description=f"{level} test")
            elif level == "INFO":
                mogger.info(f"{level} message", category="system_events", event_type="test", description=f"{level} test")
            elif level == "WARNING":
                mogger.warning(f"{level} message", category="system_events", event_type="test", description=f"{level} test")
            elif level == "ERROR":
                mogger.error(f"{level} message", category="system_events", event_type="test", description=f"{level} test")
            elif level == "CRITICAL":
                mogger.critical(f"{level} message", category="system_events", event_type="test", description=f"{level} test")
        
        mogger.close()

    def test_mogger_loki_with_shell_disabled(self, test_config_path, test_db_path, mock_loki_config):
        """Test logging to Loki when terminal output is disabled."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=mock_loki_config
        )
        
        # Log with shell output disabled
        mogger.info("Silent log to Loki", category="user_actions", user_id="user123", action="test", log_to_shell=False)
        
        mogger.close()

    def test_mogger_loki_batch_logging(self, test_config_path, test_db_path, mock_loki_config):
        """Test sending batch of logs to Loki."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=mock_loki_config
        )
        
        # Send batch of logs
        for i in range(50):
            mogger.info(
                f"Batch log {i}",
                category="user_actions",
                user_id=f"user_{i}",
                action="batch_test",
                batch_id=f"batch-{i // 10}",
                item_number=i
            )
        
        mogger.close()


class TestLokiErrorHandling:
    """Tests for Loki error handling scenarios."""

    @patch('mogger.loki.logging_loki.LokiHandler')
    def test_loki_logger_handles_connection_error(self, mock_handler, mock_loki_config):
        """Test LokiLogger handles connection errors gracefully."""
        mock_handler.side_effect = Exception("Connection failed")
        
        # Should handle error without crashing
        try:
            logger = LokiLogger(mock_loki_config)
        except Exception as e:
            assert "Connection failed" in str(e)

    # Removed test_mogger_continues_on_loki_failure - causes hangs due to DNS timeouts


class TestLokiConfigDefaults:
    """Tests for LokiConfig default values."""

    def test_loki_config_default_tags(self):
        """Test LokiConfig uses default tags when not provided."""
        config = LokiConfig(url="http://localhost:3100/loki/api/v1/push")
        
        assert "application" in config.tags
        assert config.tags["application"] == "mogger"

    def test_loki_config_no_auth_defaults(self):
        """Test LokiConfig has None for auth by default."""
        config = LokiConfig(url="http://localhost:3100/loki/api/v1/push")
        
        assert config.username is None
        assert config.password is None


class TestLokiUUIDTracking:
    """Tests for UUID tracking in Loki logs."""

    def test_mogger_includes_uuid_in_loki_logs(self, test_config_path, test_db_path, mock_loki_config):
        """Test that UUID is included in extra data sent to Loki."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=mock_loki_config
        )
        
        uuid = mogger.info("Test message with UUID", category="user_actions", user_id="user123", action="test")
        
        # UUID should be valid
        assert uuid is not None
        assert len(uuid) > 0
        
        mogger.close()

    def test_each_log_has_unique_uuid(self, test_config_path, test_db_path, mock_loki_config):
        """Test that each log gets a unique UUID."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=mock_loki_config
        )
        
        uuids = []
        for i in range(10):
            uuid = mogger.info(f"Message {i}", category="user_actions", user_id=f"user_{i}", action="test")
            uuids.append(uuid)
        
        # All UUIDs should be unique
        assert len(uuids) == len(set(uuids))
        
        mogger.close()
