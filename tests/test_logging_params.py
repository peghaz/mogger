"""
Tests for Mogger logging parameters: use_local_db and log_to_shell.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from mogger import Mogger


@pytest.fixture
def test_config_path():
    """Return path to test configuration file."""
    return Path(__file__).parent / "test_config.yaml"


@pytest.fixture
def test_db_path(tmp_path):
    """Return path to temporary test database file."""
    return str(tmp_path / "mogger_test_logs.db")


class TestUseLocalDbParameter:
    """Tests for use_local_db parameter."""

    def test_mogger_with_use_local_db_false_in_init(self, test_config_path, test_db_path):
        """Test that DB manager is not initialized when use_local_db=False in __init__."""
        mogger = Mogger(test_config_path, db_path=test_db_path, use_local_db=False)
        
        # Database manager should not be initialized
        assert mogger._Mogger__db_manager is None
        assert mogger._Mogger__use_local_db is False
        
        mogger.close()

    def test_mogger_with_use_local_db_true_in_init(self, test_config_path, test_db_path):
        """Test that DB manager is initialized when use_local_db=True (default)."""
        mogger = Mogger(test_config_path, db_path=test_db_path, use_local_db=True)
        
        # Database manager should be initialized
        assert mogger._Mogger__db_manager is not None
        assert mogger._Mogger__use_local_db is True
        
        mogger.close()

    def test_mogger_default_use_local_db_in_init(self, test_config_path, test_db_path):
        """Test that DB manager is initialized by default."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        # Database manager should be initialized by default
        assert mogger._Mogger__db_manager is not None
        assert mogger._Mogger__use_local_db is True
        
        mogger.close()

    def test_log_with_use_local_db_false_no_db_write(self, test_config_path, test_db_path):
        """Test that log is not written to DB when use_local_db=False in method."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        # Mock the db_manager's insert_log method
        with patch.object(mogger._Mogger__db_manager, 'insert_log') as mock_insert:
            uuid = mogger.info(
                "Test message",
                category="user_actions",
                user_id="test",
                action="test",
                use_local_db=False
            )
            
            # insert_log should NOT be called
            mock_insert.assert_not_called()
            # UUID should still be generated
            assert uuid is not None
        
        mogger.close()

    def test_log_with_use_local_db_true_writes_to_db(self, test_config_path, test_db_path):
        """Test that log is written to DB when use_local_db=True (default)."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        # Mock the db_manager's insert_log method
        with patch.object(mogger._Mogger__db_manager, 'insert_log') as mock_insert:
            uuid = mogger.info(
                "Test message",
                category="user_actions",
                user_id="test",
                action="test",
                use_local_db=True
            )
            
            # insert_log should be called
            mock_insert.assert_called_once()
            assert uuid is not None
        
        mogger.close()

    def test_log_with_db_disabled_globally_and_enabled_locally(self, test_config_path, test_db_path):
        """Test that log is not written when DB is disabled globally, even if enabled in method."""
        mogger = Mogger(test_config_path, db_path=test_db_path, use_local_db=False)
        
        # Even with use_local_db=True in method, DB is disabled globally
        uuid = mogger.info(
            "Test message",
            category="user_actions",
            user_id="test",
            action="test",
            use_local_db=True
        )
        
        # Should still return UUID
        assert uuid is not None
        # DB manager should be None
        assert mogger._Mogger__db_manager is None
        
        mogger.close()

    def test_all_log_levels_with_use_local_db_false(self, test_config_path, test_db_path):
        """Test that all log level methods respect use_local_db=False."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        with patch.object(mogger._Mogger__db_manager, 'insert_log') as mock_insert:
            # Test all log levels
            mogger.debug("Debug", category="user_actions", user_id="test", action="debug", use_local_db=False)
            mogger.info("Info", category="user_actions", user_id="test", action="info", use_local_db=False)
            mogger.warning("Warning", category="errors", error_code=400, error_message="warn", severity="low", use_local_db=False)
            mogger.error("Error", category="errors", error_code=500, error_message="err", severity="high", use_local_db=False)
            mogger.critical("Critical", category="errors", error_code=503, error_message="crit", severity="critical", use_local_db=False)
            
            # insert_log should not be called for any of them
            mock_insert.assert_not_called()
        
        mogger.close()


class TestLogToShellParameter:
    """Tests for log_to_shell parameter."""

    def test_log_with_log_to_shell_false_no_terminal_output(self, test_config_path, test_db_path):
        """Test that no terminal output when log_to_shell=False."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        # Mock the __print_to_terminal method
        with patch.object(mogger, '_Mogger__print_to_terminal') as mock_print:
            uuid = mogger.info(
                "Test message",
                category="user_actions",
                user_id="test",
                action="test",
                log_to_shell=False
            )
            
            # __print_to_terminal should NOT be called
            mock_print.assert_not_called()
            assert uuid is not None
        
        mogger.close()

    def test_log_with_log_to_shell_true_has_terminal_output(self, test_config_path, test_db_path):
        """Test that terminal output is shown when log_to_shell=True (default)."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        # Mock the __print_to_terminal method
        with patch.object(mogger, '_Mogger__print_to_terminal') as mock_print:
            uuid = mogger.info(
                "Test message",
                category="user_actions",
                user_id="test",
                action="test",
                log_to_shell=True
            )
            
            # __print_to_terminal should be called
            mock_print.assert_called_once()
            assert uuid is not None
        
        mogger.close()

    def test_log_default_log_to_shell_has_terminal_output(self, test_config_path, test_db_path):
        """Test that terminal output is shown by default."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        # Mock the __print_to_terminal method
        with patch.object(mogger, '_Mogger__print_to_terminal') as mock_print:
            uuid = mogger.info(
                "Test message",
                category="user_actions",
                user_id="test",
                action="test"
            )
            
            # __print_to_terminal should be called by default
            mock_print.assert_called_once()
            assert uuid is not None
        
        mogger.close()

    def test_all_log_levels_with_log_to_shell_false(self, test_config_path, test_db_path):
        """Test that all log level methods respect log_to_shell=False."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        with patch.object(mogger, '_Mogger__print_to_terminal') as mock_print:
            # Test all log levels
            mogger.debug("Debug", category="user_actions", user_id="test", action="debug", log_to_shell=False)
            mogger.info("Info", category="user_actions", user_id="test", action="info", log_to_shell=False)
            mogger.warning("Warning", category="errors", error_code=400, error_message="warn", severity="low", log_to_shell=False)
            mogger.error("Error", category="errors", error_code=500, error_message="err", severity="high", log_to_shell=False)
            mogger.critical("Critical", category="errors", error_code=503, error_message="crit", severity="critical", log_to_shell=False)
            
            # __print_to_terminal should not be called for any of them
            mock_print.assert_not_called()
        
        mogger.close()


class TestCombinedParameters:
    """Tests for combined use of use_local_db and log_to_shell parameters."""

    def test_both_params_false_silent_logging(self, test_config_path, test_db_path):
        """Test logging with both use_local_db=False and log_to_shell=False."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        with patch.object(mogger._Mogger__db_manager, 'insert_log') as mock_insert, \
             patch.object(mogger, '_Mogger__print_to_terminal') as mock_print:
            
            uuid = mogger.info(
                "Silent message",
                category="user_actions",
                user_id="test",
                action="test",
                use_local_db=False,
                log_to_shell=False
            )
            
            # Neither DB nor terminal should be used
            mock_insert.assert_not_called()
            mock_print.assert_not_called()
            # But UUID should still be generated
            assert uuid is not None
        
        mogger.close()

    def test_use_local_db_false_log_to_shell_true(self, test_config_path, test_db_path):
        """Test logging to shell only, skipping DB."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        with patch.object(mogger._Mogger__db_manager, 'insert_log') as mock_insert, \
             patch.object(mogger, '_Mogger__print_to_terminal') as mock_print:
            
            uuid = mogger.info(
                "Shell only",
                category="user_actions",
                user_id="test",
                action="test",
                use_local_db=False,
                log_to_shell=True
            )
            
            # DB should not be used
            mock_insert.assert_not_called()
            # Terminal should be used
            mock_print.assert_called_once()
            assert uuid is not None
        
        mogger.close()

    def test_use_local_db_true_log_to_shell_false(self, test_config_path, test_db_path):
        """Test logging to DB only, skipping shell."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        with patch.object(mogger._Mogger__db_manager, 'insert_log') as mock_insert, \
             patch.object(mogger, '_Mogger__print_to_terminal') as mock_print:
            
            uuid = mogger.info(
                "DB only",
                category="user_actions",
                user_id="test",
                action="test",
                use_local_db=True,
                log_to_shell=False
            )
            
            # DB should be used
            mock_insert.assert_called_once()
            # Terminal should not be used
            mock_print.assert_not_called()
            assert uuid is not None
        
        mogger.close()

    def test_no_db_init_with_loki_only(self, test_config_path, test_db_path):
        """Test Mogger can work with Loki only, no DB."""
        from mogger import LokiConfig
        
        loki_config = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
            tags={"application": "test"},
        )
        
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            use_local_db=False,
            loki_config=loki_config
        )
        
        # DB manager should be None
        assert mogger._Mogger__db_manager is None
        # Loki logger should be initialized
        assert mogger._Mogger__loki_logger is not None
        
        # Should be able to log without errors
        uuid = mogger.info(
            "Loki only message",
            category="user_actions",
            user_id="test",
            action="test"
        )
        assert uuid is not None
        
        mogger.close()

    def test_multiple_logs_with_different_params(self, test_config_path, test_db_path):
        """Test multiple logs with different parameter combinations."""
        mogger = Mogger(test_config_path, db_path=test_db_path)
        
        with patch.object(mogger._Mogger__db_manager, 'insert_log') as mock_insert, \
             patch.object(mogger, '_Mogger__print_to_terminal') as mock_print:
            
            # Log 1: Both enabled (default)
            mogger.info("Log 1", category="user_actions", user_id="1", action="test1")
            assert mock_insert.call_count == 1
            assert mock_print.call_count == 1
            
            # Log 2: DB only
            mogger.info("Log 2", category="user_actions", user_id="2", action="test2", log_to_shell=False)
            assert mock_insert.call_count == 2
            assert mock_print.call_count == 1  # Still 1
            
            # Log 3: Shell only
            mogger.info("Log 3", category="user_actions", user_id="3", action="test3", use_local_db=False)
            assert mock_insert.call_count == 2  # Still 2
            assert mock_print.call_count == 2
            
            # Log 4: Neither
            mogger.info("Log 4", category="user_actions", user_id="4", action="test4", use_local_db=False, log_to_shell=False)
            assert mock_insert.call_count == 2  # Still 2
            assert mock_print.call_count == 2  # Still 2
        
        mogger.close()
