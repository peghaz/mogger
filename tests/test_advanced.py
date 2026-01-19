"""
Tests for context management and advanced features.
"""

import pytest

from mogger import Mogger


class TestContextManagement:
    """Test context data management."""
    
    def test_set_context(self, logger):
        """Test setting context data."""
        logger.set_context(request_id="req_123", session_id="sess_456")
        
        # Log should include context data
        log_uuid = logger.info("Action with context", table="user_actions",
                              user_id="u1", action="test")
        
        # Query and verify (context data should be in the log)
        results = logger.query(table="user_actions")
        assert len(results) == 1
        # Note: context_data is merged into kwargs, so it depends on table schema
    
    def test_clear_context(self, logger):
        """Test clearing context data."""
        logger.set_context(request_id="req_123")
        logger.clear_context()
        
        # Log without context
        log_uuid = logger.info("Action without context", table="user_actions",
                              user_id="u1", action="test")
        assert log_uuid is not None
    
    def test_context_persists_across_logs(self, logger):
        """Test that context persists across multiple log calls."""
        logger.set_context(session_id="sess_789")
        
        uuid1 = logger.info("Log 1", table="user_actions", user_id="u1", action="a1")
        uuid2 = logger.info("Log 2", table="user_actions", user_id="u2", action="a2")
        uuid3 = logger.info("Log 3", table="user_actions", user_id="u3", action="a3")
        
        assert all([uuid1, uuid2, uuid3])
    
    def test_update_context(self, logger):
        """Test updating existing context."""
        logger.set_context(key1="value1", key2="value2")
        logger.set_context(key2="updated", key3="value3")  # Update key2, add key3
        
        log_uuid = logger.info("Updated context", table="user_actions",
                              user_id="u1", action="test")
        assert log_uuid is not None


class TestLoggerState:
    """Test logger state management."""
    
    def test_terminal_toggle(self, logger):
        """Test toggling terminal output."""
        # Initially disabled in test config
        logger.set_terminal(True)
        log1 = logger.info("Terminal on", table="system_events",
                          event_type="test", description="Terminal enabled")
        
        logger.set_terminal(False)
        log2 = logger.info("Terminal off", table="system_events",
                          event_type="test", description="Terminal disabled")
        
        assert all([log1, log2])
    
    def test_logger_close(self, logger):
        """Test closing logger."""
        logger.info("Before close", table="system_events",
                   event_type="test", description="Test")
        logger.close()
        
        # After close, attempting operations should fail
        # (depends on implementation - might just work with a new connection)
    
    def test_multiple_logger_instances(self, test_config_path, clean_test_db):
        """Test multiple logger instances on same database."""
        logger1 = Mogger(test_config_path)
        logger2 = Mogger(test_config_path)
        
        uuid1 = logger1.info("From logger1", table="system_events",
                           event_type="l1", description="Logger 1")
        uuid2 = logger2.info("From logger2", table="system_events",
                           event_type="l2", description="Logger 2")
        
        # Both should work
        assert uuid1 != uuid2
        
        # Query from both
        results1 = logger1.query(table="system_events")
        results2 = logger2.query(table="system_events")
        
        assert len(results1) == 2
        assert len(results2) == 2
        
        logger1.close()
        logger2.close()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_string_values(self, logger):
        """Test logging with empty string values."""
        log_uuid = logger.info("Empty strings", table="user_actions",
                              user_id="", action="")
        assert log_uuid is not None
        
        results = logger.query(table="user_actions")
        assert results[0]["user_id"] == ""
        assert results[0]["action"] == ""
    
    def test_very_long_text(self, logger):
        """Test logging with very long text."""
        long_text = "A" * 10000
        
        log_uuid = logger.error("Long error", table="errors",
                               error_code=500,
                               error_message=long_text,
                               severity="high")
        assert log_uuid is not None
        
        results = logger.query(table="errors")
        assert len(results[0]["error_message"]) == 10000
    
    def test_special_characters(self, logger):
        """Test logging with special characters."""
        special_text = "Test with 'quotes', \"double quotes\", and symbols: @#$%^&*()"
        
        log_uuid = logger.info("Special chars", table="system_events",
                              event_type="special",
                              description=special_text)
        assert log_uuid is not None
        
        results = logger.query(table="system_events")
        assert special_text in results[0]["description"]
    
    def test_unicode_characters(self, logger):
        """Test logging with Unicode characters."""
        unicode_text = "Hello 世界 🌍 Привет مرحبا"
        
        log_uuid = logger.info("Unicode test", table="system_events",
                              event_type="unicode",
                              description=unicode_text)
        assert log_uuid is not None
        
        results = logger.query(table="system_events")
        assert unicode_text in results[0]["description"]
    
    def test_null_vs_missing_nullable_field(self, logger):
        """Test difference between None and omitted nullable fields."""
        # Omit nullable field
        uuid1 = logger.info("Omitted", table="user_actions",
                           user_id="u1", action="test")
        
        # Explicitly set to None (if supported by serialization)
        uuid2 = logger.info("None value", table="user_actions",
                           user_id="u2", action="test", ip_address=None)
        
        assert uuid1 != uuid2
    
    def test_zero_and_negative_numbers(self, logger):
        """Test logging with zero and negative numbers."""
        log_uuid = logger.error("Negative error code", table="errors",
                               error_code=-1,
                               error_message="Test negative",
                               severity="low")
        assert log_uuid is not None
        
        results = logger.query(table="errors")
        assert results[0]["error_code"] == -1
    
    def test_boolean_like_strings(self, logger):
        """Test logging strings that look like booleans."""
        metadata = {"enabled": "true", "disabled": "false", "null": "null"}
        
        log_uuid = logger.info("Boolean strings", table="user_actions",
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
        
        log_uuid = logger.info("Nested JSON", table="user_actions",
                              user_id="u1", action="test", metadata=complex_json)
        assert log_uuid is not None


class TestConcurrentAccess:
    """Test concurrent access scenarios."""
    
    def test_rapid_sequential_logging(self, logger):
        """Test rapid sequential log insertion."""
        uuids = []
        for i in range(100):
            uuid = logger.info(f"Rapid {i}", table="system_events",
                             event_type="rapid", description=f"Log {i}")
            uuids.append(uuid)
        
        assert len(set(uuids)) == 100  # All unique
        
        results = logger.query(table="system_events")
        assert len(results) == 100
    
    def test_alternating_tables(self, logger):
        """Test rapidly alternating between different tables."""
        tables = ["user_actions", "errors", "system_events", "api_requests"]
        
        for i in range(40):  # 10 per table
            table = tables[i % 4]
            
            if table == "user_actions":
                logger.info(f"Log {i}", table=table, user_id=f"u{i}", action="test")
            elif table == "errors":
                logger.error(f"Log {i}", table=table, error_code=i,
                           error_message=f"Error {i}", severity="low")
            elif table == "system_events":
                logger.info(f"Log {i}", table=table, event_type="test",
                          description=f"Event {i}")
            elif table == "api_requests":
                logger.info(f"Log {i}", table=table, endpoint="/api",
                          method="GET", status_code=200, response_time_ms=float(i))
        
        # Verify all tables have 10 logs
        for table in tables:
            if table == "user_actions":
                results = logger.query(table=table)
            elif table == "errors":
                results = logger.query(table=table)
            elif table == "system_events":
                results = logger.query(table=table)
            elif table == "api_requests":
                results = logger.query(table=table)
            
            assert len(results) == 10
