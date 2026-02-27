"""
Tests for context management and advanced features.
"""

import pytest

from mogger import Mogger


class TestContextManagement:
    """Test context data management."""
    
    def test_set_context(self, logger):
        """Test setting context data."""
        # Context fields are not defined in schema, so use log_to_csv=False
        logger.set_context(request_id="req_123", session_id="sess_456")
        
        # Log should include context data (sent to Loki if configured, not to CSV)
        log_uuid = logger.info("Action with context", category="user_actions",
                              user_id="u1", action="test", log_to_csv=False)
        
        assert log_uuid is not None
    
    def test_clear_context(self, logger):
        """Test clearing context data."""
        logger.set_context(request_id="req_123")
        logger.clear_context()
        
        # Log without context
        log_uuid = logger.info("Action without context", category="user_actions",
                              user_id="u1", action="test")
        assert log_uuid is not None
    
    def test_context_persists_across_logs(self, logger):
        """Test that context persists across multiple log calls."""
        logger.set_context(session_id="sess_789")
        
        # Context fields not in schema, so use log_to_csv=False
        uuid1 = logger.info("Log 1", category="user_actions", user_id="u1", action="a1", log_to_csv=False)
        uuid2 = logger.info("Log 2", category="user_actions", user_id="u2", action="a2", log_to_csv=False)
        uuid3 = logger.info("Log 3", category="user_actions", user_id="u3", action="a3", log_to_csv=False)
        
        assert all([uuid1, uuid2, uuid3])
        logger.clear_context()
    
    def test_update_context(self, logger):
        """Test updating existing context."""
        logger.set_context(key1="value1", key2="value2")
        logger.set_context(key2="updated", key3="value3")  # Update key2, add key3
        
        # Context fields not in schema, so use log_to_csv=False
        log_uuid = logger.info("Updated context", category="user_actions",
                              user_id="u1", action="test", log_to_csv=False)
        assert log_uuid is not None
        logger.clear_context()


class TestLoggerState:
    """Test logger state management."""
    
    def test_terminal_toggle(self, logger):
        """Test toggling terminal output."""
        # Initially disabled in test config
        logger.set_terminal(True)
        log1 = logger.info("Terminal on", category="system_events",
                          event_type="test", description="Terminal enabled")
        
        logger.set_terminal(False)
        log2 = logger.info("Terminal off", category="system_events",
                          event_type="test", description="Terminal disabled")
        
        assert all([log1, log2])
    
    def test_logger_multiple_logs(self, logger):
        """Test logging multiple messages."""
        uuid1 = logger.info("Log 1", category="system_events",
                   event_type="test", description="Test 1")
        uuid2 = logger.info("Log 2", category="system_events",
                   event_type="test", description="Test 2")
        
        assert uuid1 is not None
        assert uuid2 is not None
        assert uuid1 != uuid2
    
    def test_multiple_logger_instances(self, test_config_path, clean_test_logs):
        """Test multiple logger instances."""
        logger1 = Mogger(test_config_path)
        logger2 = Mogger(test_config_path)
        
        uuid1 = logger1.info("From logger1", category="system_events",
                           event_type="l1", description="Logger 1")
        uuid2 = logger2.info("From logger2", category="system_events",
                           event_type="l2", description="Logger 2")
        
        # Both should work and produce unique UUIDs
        assert uuid1 != uuid2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_string_values(self, logger):
        """Test logging with empty string values."""
        log_uuid = logger.info("Empty strings", category="user_actions",
                              user_id="", action="")
        assert log_uuid is not None
    
    def test_very_long_text(self, logger):
        """Test logging with very long text."""
        long_text = "A" * 10000
        
        log_uuid = logger.error("Long error", category="errors",
                               error_code=500,
                               error_message=long_text,
                               severity="high")
        assert log_uuid is not None
    
    def test_special_characters(self, logger):
        """Test logging with special characters."""
        special_text = "Test with 'quotes', \"double quotes\", and symbols: @#$%^&*()"
        
        log_uuid = logger.info("Special chars", category="system_events",
                              event_type="special",
                              description=special_text)
        assert log_uuid is not None
    
    def test_unicode_characters(self, logger):
        """Test logging with Unicode characters."""
        unicode_text = "Hello 世界 🌍 Привет مرحبا"
        
        log_uuid = logger.info("Unicode test", category="system_events",
                              event_type="unicode",
                              description=unicode_text)
        assert log_uuid is not None
    
    def test_null_vs_missing_nullable_field(self, logger):
        """Test difference between None and omitted nullable fields."""
        # Omit nullable field
        uuid1 = logger.info("Omitted", category="user_actions",
                           user_id="u1", action="test")
        
        # Explicitly set to None (if supported by serialization)
        uuid2 = logger.info("None value", category="user_actions",
                           user_id="u2", action="test", ip_address=None)
        
        assert uuid1 != uuid2
    
    def test_zero_and_negative_numbers(self, logger):
        """Test logging with zero and negative numbers."""
        log_uuid = logger.error("Negative error code", category="errors",
                               error_code=-1,
                               error_message="Test negative",
                               severity="low")
        assert log_uuid is not None
    
    def test_boolean_like_strings(self, logger):
        """Test logging strings that look like booleans."""
        metadata = {"enabled": "true", "disabled": "false", "null": "null"}
        
        log_uuid = logger.info("Boolean strings", category="user_actions",
                              user_id="u1", action="test", metadata=metadata)
        assert log_uuid is not None
    
    def test_nested_json_structures(self, logger):
        """Test logging deeply nested JSON."""
        complex_json = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "data": [1, 2, 3, 4, 5],
                            "nested_obj": {"key": "value"}
                        }
                    }
                }
            },
            "array": [
                {"id": 1, "name": "First"},
                {"id": 2, "name": "Second"}
            ]
        }
        
        log_uuid = logger.info("Nested JSON", category="user_actions",
                              user_id="u1", action="test", metadata=complex_json)
        assert log_uuid is not None


class TestConcurrentAccess:
    """Test concurrent access scenarios."""
    
    def test_rapid_sequential_logging(self, logger):
        """Test rapid sequential log insertion."""
        uuids = []
        for i in range(100):
            uuid = logger.info(f"Rapid {i}", category="system_events",
                             event_type="rapid", description=f"Log {i}")
            uuids.append(uuid)
        
        assert len(set(uuids)) == 100  # All unique
    
    def test_alternating_tables(self, logger):
        """Test rapidly alternating between different tables."""
        tables = ["user_actions", "errors", "system_events", "api_requests"]
        
        uuids = []
        for i in range(40):  # 10 per table
            table = tables[i % 4]
            
            if table == "user_actions":
                uuid = logger.info(f"Log {i}", category=table, user_id=f"u{i}", action="test")
            elif table == "errors":
                uuid = logger.error(f"Log {i}", category=table, error_code=i,
                           error_message=f"Error {i}", severity="low")
            elif table == "system_events":
                uuid = logger.info(f"Log {i}", category=table, event_type="test",
                          description=f"Event {i}")
            elif table == "api_requests":
                uuid = logger.info(f"Log {i}", category=table, endpoint="/api",
                          method="GET", status_code=200, response_time_ms=float(i))
            uuids.append(uuid)
        
        # Verify all UUIDs are unique
        assert len(set(uuids)) == 40
