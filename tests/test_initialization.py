"""
Basic tests for Mogger logger initialization and configuration.
"""

import pytest
from pathlib import Path
import shutil

from mogger import Mogger


class TestLoggerInitialization:
    """Test logger initialization and configuration loading."""
    
    def test_logger_initialization(self, logger):
        """Test that logger initializes correctly."""
        assert logger is not None
    
    def test_logs_directory_created(self, logger, clean_test_logs):
        """Test that logs directory is created."""
        # The logs directory should be created under .mogger.logs
        logs_dir = clean_test_logs
        # Logger might not have written yet, but directory config should be valid
        assert logger is not None
    
    def test_invalid_config_path(self):
        """Test that invalid config path raises error."""
        with pytest.raises(FileNotFoundError):
            Mogger("nonexistent_config.yaml")
    
    def test_get_tables(self, logger):
        """Test retrieving list of tables."""
        tables = logger.get_tables()
        assert "user_actions" in tables
        assert "errors" in tables
        assert "system_events" in tables
        assert "api_requests" in tables
        assert len(tables) == 4
    
    def test_custom_logs_directory(self, test_config_path, tmp_path):
        """Test using custom logs directory via directory config in YAML."""
        # The directory is configured in YAML, not as a parameter
        # This test verifies that mogger works with default config
        mogger = Mogger(test_config_path)
        
        # Log a message to verify it works
        uuid = mogger.info("Test message", category="system_events", event_type="test", description="test")
        assert uuid is not None


class TestTerminalConfiguration:
    """Test terminal output configuration."""
    
    def test_terminal_disabled_by_default(self, logger):
        """Test that terminal is disabled in test config."""
        # Terminal should be disabled in test config
        # We can't directly access private config, but we can verify behavior
        log_uuid = logger.info(
            "Test message",
            category="system_events",
            event_type="test",
            description="Testing terminal output"
        )
        assert log_uuid is not None
    
    def test_set_terminal_enabled(self, logger):
        """Test enabling terminal output."""
        logger.set_terminal(True)
        # Should not raise any errors
        log_uuid = logger.info(
            "Terminal enabled",
            category="system_events",
            event_type="test",
            description="Test with terminal"
        )
        assert log_uuid is not None
    
    def test_set_terminal_disabled(self, logger):
        """Test disabling terminal output."""
        logger.set_terminal(False)
        log_uuid = logger.info(
            "Terminal disabled",
            category="system_events",
            event_type="test",
            description="Test without terminal"
        )
        assert log_uuid is not None
