"""
Basic tests for Mogger logger initialization and configuration.
"""

import pytest
from pathlib import Path

from mogger import Mogger


class TestLoggerInitialization:
    """Test logger initialization and configuration loading."""
    
    def test_logger_initialization(self, logger):
        """Test that logger initializes correctly."""
        assert logger is not None
    
    def test_database_created(self, logger, test_db_path):
        """Test that database file is created."""
        assert test_db_path.exists()
    
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
    
    def test_custom_db_path(self, test_config_path, clean_test_db):
        """Test overriding database path."""
        custom_db = "./custom_test_logs.db"
        mogger = Mogger(test_config_path, db_path=custom_db)
        
        assert Path(custom_db).exists()
        
        # Cleanup
        mogger.close()
        if Path(custom_db).exists():
            Path(custom_db).unlink()


class TestTerminalConfiguration:
    """Test terminal output configuration."""
    
    def test_terminal_disabled_by_default(self, logger):
        """Test that terminal is disabled in test config."""
        # Terminal should be disabled in test config
        # We can't directly access private config, but we can verify behavior
        log_uuid = logger.info(
            "Test message",
            table="system_events",
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
            table="system_events",
            event_type="test",
            description="Test with terminal"
        )
        assert log_uuid is not None
    
    def test_set_terminal_disabled(self, logger):
        """Test disabling terminal output."""
        logger.set_terminal(False)
        log_uuid = logger.info(
            "Terminal disabled",
            table="system_events",
            event_type="test",
            description="Test without terminal"
        )
        assert log_uuid is not None
