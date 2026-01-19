"""
Integration tests for complete logging workflows.
"""

import pytest
from datetime import datetime
import uuid


class TestCompleteWorkflows:
    """Test complete real-world logging workflows."""
    
    def test_user_session_workflow(self, logger):
        """Test logging a complete user session."""
        session_id = str(uuid.uuid4())
        
        # User logs in
        login_uuid = logger.info(
            "User logged in",
            category="user_actions",
            user_id="user_alice",
            action="login",
            ip_address="203.0.113.42",
            metadata={"device": "mobile", "app_version": "2.1.0"}
        )
        
        # User performs various actions
        logger.info(
            "Viewed profile",
            category="user_actions",
            user_id="user_alice",
            action="view_profile",
            metadata={"profile_id": "12345"}
        )
        
        logger.info(
            "Updated settings",
            category="user_actions",
            user_id="user_alice",
            action="update_settings",
            metadata={"settings": {"notifications": True, "theme": "dark"}}
        )
        
        # User encounters an error
        logger.error(
            "Failed to upload file",
            category="errors",
            error_code=413,
            error_message="File size exceeds 10MB limit",
            severity="low"
        )
        
        # User logs out
        logout_uuid = logger.info(
            "User logged out",
            category="user_actions",
            user_id="user_alice",
            action="logout",
            ip_address="203.0.113.42"
        )
        
        # Verify all logs are recorded
        user_actions = logger.query(category="user_actions", user_id="user_alice")
        assert len(user_actions) == 4
        
        errors = logger.query(category="errors")
        assert len(errors) == 1
    
    def test_api_monitoring_workflow(self, logger):
        """Test API request monitoring workflow."""
        endpoints = [
            ("/api/v1/users", "GET", 200, 145.2),
            ("/api/v1/users", "POST", 201, 289.5),
            ("/api/v1/users/123", "GET", 200, 98.3),
            ("/api/v1/users/123", "PUT", 200, 312.7),
            ("/api/v1/users/456", "GET", 404, 45.1),
            ("/api/v1/posts", "GET", 200, 234.8),
            ("/api/v1/posts", "POST", 201, 456.2),
            ("/api/v1/health", "GET", 200, 12.3),
        ]
        
        for endpoint, method, status, response_time in endpoints:
            logger.info(
                f"{method} {endpoint}",
                category="api_requests",
                endpoint=endpoint,
                method=method,
                status_code=status,
                response_time_ms=response_time
            )
        
        # Query all API requests
        all_requests = logger.query(category="api_requests")
        assert len(all_requests) == 8
        
        # Query successful requests
        successful = logger.query(category="api_requests", status_code=200)
        assert len(successful) == 5
        
        # Query POST requests
        posts = logger.query(category="api_requests", method="POST")
        assert len(posts) == 2
    
    def test_error_tracking_workflow(self, logger):
        """Test error tracking and debugging workflow."""
        # Application startup
        logger.info(
            "Application started",
            category="system_events",
            event_type="startup",
            description="Application initialized successfully",
            duration_ms=1234.5
        )
        
        # Various errors occur
        errors = [
            (400, "Invalid JSON in request body", "low"),
            (401, "Authentication token expired", "medium"),
            (403, "Insufficient permissions", "medium"),
            (500, "Database connection timeout", "high"),
            (503, "External service unavailable", "high"),
            (500, "Unhandled exception in payment processor", "critical"),
        ]
        
        for code, message, severity in errors:
            logger.error(
                f"Error {code}",
                category="errors",
                error_code=code,
                error_message=message,
                severity=severity
            )
        
        # System warnings
        logger.warning(
            "High memory usage",
            category="system_events",
            event_type="warning",
            description="Memory usage at 85%"
        )
        
        logger.warning(
            "Slow query detected",
            category="system_events",
            event_type="warning",
            description="Database query took 5.2 seconds",
            duration_ms=5200.0
        )
        
        # Query critical errors
        critical_errors = logger.query(category="errors", severity="critical")
        assert len(critical_errors) == 1
        assert critical_errors[0]["error_code"] == 500
        
        # Query high severity errors
        high_errors = logger.query(category="errors", severity="high")
        assert len(high_errors) == 2
        
        # Query all warnings
        warnings = logger.query(category="logs_master", log_level="WARNING")
        assert len(warnings) == 2
    
    def test_mixed_logging_with_context(self, logger):
        """Test complex workflow with context management."""
        # Set request context
        logger.set_context(request_id="req_xyz789")
        
        # API request comes in
        logger.info(
            "Incoming API request",
            category="api_requests",
            endpoint="/api/v1/checkout",
            method="POST",
            status_code=200,
            response_time_ms=456.7
        )
        
        # User action
        logger.info(
            "User initiated checkout",
            category="user_actions",
            user_id="user_bob",
            action="checkout",
            metadata={"cart_items": 3, "total": 99.99}
        )
        
        # System event
        logger.info(
            "Payment processing started",
            category="system_events",
            event_type="payment",
            description="Processing credit card payment"
        )
        
        # Error occurs
        logger.error(
            "Payment gateway timeout",
            category="errors",
            error_code=504,
            error_message="Payment gateway did not respond within 30s",
            severity="high"
        )
        
        # Clear context for next request
        logger.clear_context()
        
        # New request without context
        logger.info(
            "Health check",
            category="api_requests",
            endpoint="/health",
            method="GET",
            status_code=200,
            response_time_ms=5.2
        )
        
        # Verify all logs were created
        master_logs = logger.query(category="logs_master")
        assert len(master_logs) == 5
    
    def test_daily_operations_simulation(self, logger):
        """Simulate a day's worth of varied operations."""
        # Morning: System startup
        logger.info(
            "Daily startup",
            category="system_events",
            event_type="startup",
            description="System initialized for the day"
        )
        
        # Morning: User activity
        for i in range(10):
            logger.info(
                f"User {i} login",
                category="user_actions",
                user_id=f"user_{i}",
                action="login",
                ip_address=f"192.168.1.{100 + i}"
            )
        
        # Midday: High API traffic
        for i in range(50):
            status = 200 if i % 10 != 0 else 500
            logger.info(
                f"API call {i}",
                category="api_requests",
                endpoint="/api/data",
                method="GET",
                status_code=status,
                response_time_ms=50.0 + (i * 2.5)
            )
        
        # Afternoon: Some errors
        for i in range(5):
            logger.error(
                f"Afternoon error {i}",
                category="errors",
                error_code=500 + i,
                error_message=f"Error message {i}",
                severity="medium"
            )
        
        # Evening: System events
        logger.warning(
            "Database backup started",
            category="system_events",
            event_type="backup",
            description="Automated evening backup"
        )
        
        logger.info(
            "Backup completed",
            category="system_events",
            event_type="backup",
            description="Backup finished successfully",
            duration_ms=45000.0
        )
        
        # Verify totals
        total_logs = logger.query(category="logs_master")
        assert len(total_logs) == 10 + 1 + 50 + 5 + 2  # 68 total
        
        user_actions = logger.query(category="user_actions")
        assert len(user_actions) == 10
        
        api_requests = logger.query(category="api_requests")
        assert len(api_requests) == 50
        
        errors = logger.query(category="errors")
        assert len(errors) == 5
        
        system_events = logger.query(category="system_events")
        assert len(system_events) == 3


class TestDataIntegrity:
    """Test data integrity across operations."""
    
    def test_uuid_uniqueness(self, logger):
        """Test that all UUIDs are unique."""
        uuids = []
        for i in range(50):
            uuid_val = logger.info(
                f"Test {i}",
                category="system_events",
                event_type="test",
                description=f"Test {i}"
            )
            uuids.append(uuid_val)
        
        # All UUIDs should be unique
        assert len(set(uuids)) == 50
        
        # Verify in master table
        master_logs = logger.query(category="logs_master")
        master_uuids = [log["uuid"] for log in master_logs]
        assert len(set(master_uuids)) == 50
    
    def test_referential_integrity(self, logger):
        """Test that log UUIDs in dynamic tables match master table."""
        # Insert logs
        for i in range(10):
            logger.info(f"Log {i}", category="user_actions",
                       user_id=f"u{i}", action="test")
        
        # Get UUIDs from master table
        master_logs = logger.query(category="logs_master")
        master_uuids = set(log["uuid"] for log in master_logs)
        
        # Get UUIDs from user_actions table
        user_actions = logger.query(category="user_actions")
        action_uuids = set(log["log_uuid"] for log in user_actions)
        
        # All action UUIDs should be in master
        assert action_uuids.issubset(master_uuids)
    
    def test_timestamp_consistency(self, logger):
        """Test that timestamps are recorded correctly."""
        before = datetime.now()
        
        logger.info("Test", category="system_events",
                   event_type="test", description="Test")
        
        after = datetime.now()
        
        # Query and check timestamp
        results = logger.query(category="logs_master")
        log_time = results[0]["created_at"]
        
        # Timestamp should be between before and after
        assert before <= log_time <= after
    
    def test_table_name_consistency(self, logger):
        """Test that table names are recorded correctly in master."""
        tables_to_test = ["user_actions", "errors", "system_events", "api_requests"]
        
        for table_name in tables_to_test:
            if table_name == "user_actions":
                logger.info("Test", category=table_name, user_id="u1", action="a")
            elif table_name == "errors":
                logger.error("Test", category=table_name, error_code=500,
                           error_message="e", severity="low")
            elif table_name == "system_events":
                logger.info("Test", category=table_name, event_type="e", description="d")
            elif table_name == "api_requests":
                logger.info("Test", category=table_name, endpoint="/api", method="GET",
                          status_code=200, response_time_ms=10.0)
        
        # Verify each table is recorded in master
        for table_name in tables_to_test:
            results = logger.query(category="logs_master", table_name=table_name)
            assert len(results) == 1
            assert results[0]["table_name"] == table_name
