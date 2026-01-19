"""
Tests for logging operations - inserting logs at various levels.
"""

import pytest
import uuid
from datetime import datetime


class TestBasicLogging:
    """Test basic logging operations."""
    
    def test_info_log(self, logger):
        """Test logging an INFO message."""
        log_uuid = logger.info(
            "User logged in successfully",
            table="user_actions",
            user_id="user_123",
            action="login",
            ip_address="192.168.1.100"
        )
        
        assert log_uuid is not None
        assert isinstance(log_uuid, str)
        # Validate it's a valid UUID
        uuid.UUID(log_uuid)
    
    def test_debug_log(self, logger):
        """Test logging a DEBUG message."""
        log_uuid = logger.debug(
            "Debug information",
            table="system_events",
            event_type="debug",
            description="Debugging application state"
        )
        
        assert log_uuid is not None
        uuid.UUID(log_uuid)
    
    def test_warning_log(self, logger):
        """Test logging a WARNING message."""
        log_uuid = logger.warning(
            "High memory usage detected",
            table="system_events",
            event_type="warning",
            description="Memory usage at 85%",
            duration_ms=150.5
        )
        
        assert log_uuid is not None
        uuid.UUID(log_uuid)
    
    def test_error_log(self, logger):
        """Test logging an ERROR message."""
        log_uuid = logger.error(
            "Database connection failed",
            table="errors",
            error_code=500,
            error_message="Connection timeout after 30s",
            severity="high"
        )
        
        assert log_uuid is not None
        uuid.UUID(log_uuid)
    
    def test_critical_log(self, logger):
        """Test logging a CRITICAL message."""
        log_uuid = logger.critical(
            "System shutdown imminent",
            table="errors",
            error_code=999,
            error_message="Critical system failure",
            severity="critical"
        )
        
        assert log_uuid is not None
        uuid.UUID(log_uuid)
    
    def test_generic_log_method(self, logger):
        """Test using the generic log method."""
        log_uuid = logger.log(
            logger.INFO,
            "Custom log level",
            table="user_actions",
            user_id="user_456",
            action="custom_action"
        )
        
        assert log_uuid is not None
        uuid.UUID(log_uuid)


class TestComplexLogging:
    """Test complex logging scenarios with various data types."""
    
    def test_json_field_logging(self, logger):
        """Test logging with JSON field."""
        metadata = {
            "browser": "Chrome",
            "version": "120.0",
            "plugins": ["adblock", "vpn"],
            "settings": {
                "dark_mode": True,
                "notifications": False
            }
        }
        
        log_uuid = logger.info(
            "User preferences updated",
            table="user_actions",
            user_id="user_789",
            action="update_preferences",
            metadata=metadata
        )
        
        assert log_uuid is not None
    
    def test_nullable_fields(self, logger):
        """Test logging with nullable fields omitted."""
        log_uuid = logger.info(
            "Anonymous user action",
            table="user_actions",
            user_id="anonymous",
            action="view_page"
            # ip_address and metadata are nullable and omitted
        )
        
        assert log_uuid is not None
    
    def test_float_field(self, logger):
        """Test logging with float values."""
        log_uuid = logger.info(
            "API request completed",
            table="api_requests",
            endpoint="/api/v1/users",
            method="GET",
            status_code=200,
            response_time_ms=245.67
        )
        
        assert log_uuid is not None
    
    def test_api_request_with_bodies(self, logger):
        """Test logging API request with request/response bodies."""
        request_body = {
            "username": "testuser",
            "email": "test@example.com"
        }
        
        response_body = {
            "id": 12345,
            "username": "testuser",
            "created_at": "2026-01-19T10:00:00Z"
        }
        
        log_uuid = logger.info(
            "User creation API call",
            table="api_requests",
            endpoint="/api/v1/users",
            method="POST",
            status_code=201,
            response_time_ms=389.12,
            request_body=request_body,
            response_body=response_body
        )
        
        assert log_uuid is not None
    
    def test_error_with_stack_trace(self, logger):
        """Test logging error with stack trace."""
        stack_trace = """
        Traceback (most recent call last):
          File "main.py", line 42, in process_request
            result = database.query(user_id)
          File "database.py", line 128, in query
            raise DatabaseError("Connection lost")
        DatabaseError: Connection lost
        """
        
        log_uuid = logger.error(
            "Database query failed",
            table="errors",
            error_code=503,
            error_message="Database connection lost during query",
            stack_trace=stack_trace.strip(),
            severity="high"
        )
        
        assert log_uuid is not None


class TestLoggingErrors:
    """Test error handling in logging operations."""
    
    def test_missing_required_field(self, logger):
        """Test that missing required fields raise an error."""
        with pytest.raises(ValueError, match="Required field"):
            logger.info(
                "Incomplete log",
                table="errors",
                error_code=404
                # error_message and severity are required but missing
            )
    
    def test_invalid_table_name(self, logger):
        """Test logging to non-existent table."""
        with pytest.raises(ValueError, match="Table.*not found"):
            logger.info(
                "Invalid table",
                table="nonexistent_table",
                some_field="value"
            )
    
    def test_extra_fields_ignored(self, logger):
        """Test that extra fields not in schema are handled."""
        # Should succeed - extra fields are just ignored in kwargs
        log_uuid = logger.info(
            "Log with extra fields",
            table="system_events",
            event_type="test",
            description="Testing extra fields",
            extra_field_1="ignored",
            extra_field_2="also_ignored"
        )
        
        assert log_uuid is not None


class TestBulkLogging:
    """Test logging multiple entries in succession."""
    
    def test_multiple_logs_same_table(self, logger):
        """Test logging multiple entries to the same table."""
        uuids = []
        
        for i in range(10):
            log_uuid = logger.info(
                f"Bulk log {i}",
                table="user_actions",
                user_id=f"user_{i}",
                action="bulk_test",
                ip_address=f"192.168.1.{i}"
            )
            uuids.append(log_uuid)
        
        assert len(uuids) == 10
        assert len(set(uuids)) == 10  # All unique
    
    def test_multiple_logs_different_tables(self, logger):
        """Test logging to multiple different tables."""
        log1 = logger.info(
            "User action",
            table="user_actions",
            user_id="user_1",
            action="login"
        )
        
        log2 = logger.error(
            "Error occurred",
            table="errors",
            error_code=500,
            error_message="Internal error",
            severity="medium"
        )
        
        log3 = logger.info(
            "System event",
            table="system_events",
            event_type="startup",
            description="Application started"
        )
        
        log4 = logger.info(
            "API request",
            table="api_requests",
            endpoint="/api/health",
            method="GET",
            status_code=200,
            response_time_ms=12.3
        )
        
        assert all([log1, log2, log3, log4])
        assert len({log1, log2, log3, log4}) == 4
    
    def test_mixed_log_levels(self, logger):
        """Test logging with mixed severity levels."""
        logs = []
        
        logs.append(logger.debug("Debug message", table="system_events",
                                 event_type="debug", description="Debug info"))
        logs.append(logger.info("Info message", table="system_events",
                                event_type="info", description="Info message"))
        logs.append(logger.warning("Warning message", table="system_events",
                                   event_type="warning", description="Warning occurred"))
        logs.append(logger.error("Error message", table="errors",
                                 error_code=400, error_message="Bad request", severity="low"))
        logs.append(logger.critical("Critical message", table="errors",
                                    error_code=999, error_message="Critical failure", severity="critical"))
        
        assert len(logs) == 5
        assert len(set(logs)) == 5
