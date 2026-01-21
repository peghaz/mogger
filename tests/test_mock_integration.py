"""
Integration test based on mock.py - real-world usage scenario.
Tests logging to Loki and retrieving logs with the new API methods.
"""

from mogger import Mogger, LokiConfig


class TestRealWorldIntegration:
    """Test real-world usage scenarios from mock.py."""

    def test_logging_with_loki_and_retrieval(self, test_config_path, test_db_path, clean_test_db):
        """
        Test logging to both Loki and local database, then retrieving logs.

        This test simulates the real-world scenario from mock.py where we:
        1. Log various messages to system_events table
        2. Retrieve the latest logs using the new get_latest_logs method
        """
        # Initialize logger with Loki config
        loki_config = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
        )

        logger = Mogger(
            config_path=test_config_path,
            db_path=test_db_path,
            loki_config=loki_config
        )

        # Log info message (from mock.py)
        uuid_info = logger.info(
            message="This is an info message",
            category="system_events",
            event_type="startup",
            description="The system has started successfully.",
            duration_ms=123.45,
        )

        # Log error message (from mock.py)
        uuid_error = logger.error(
            message="This is an error message",
            category="system_events",
            event_type="shutdown",
            description="The system encountered an error during shutdown.",
            duration_ms=67.89,
        )

        # Log debug message (from mock.py)
        uuid_debug = logger.debug(
            message="This is a debug message",
            category="system_events",
            event_type="debug_info",
            description="Debugging information for developers.",
        )

        # Retrieve latest logs using new API (from mock.py)
        data = logger.get_latest_logs(category="system_events", limit=5)

        # Verify we got the logs
        assert len(data) == 3

        # Verify log UUIDs are present
        log_uuids = [log["log_uuid"] for log in data]
        assert uuid_info in log_uuids
        assert uuid_error in log_uuids
        assert uuid_debug in log_uuids

        # Verify event types
        event_types = [log["event_type"] for log in data]
        assert "startup" in event_types
        assert "shutdown" in event_types
        assert "debug_info" in event_types

        # Verify descriptions
        descriptions = [log["description"] for log in data]
        assert "The system has started successfully." in descriptions
        assert "The system encountered an error during shutdown." in descriptions
        assert "Debugging information for developers." in descriptions

        logger.close()

    def test_logging_without_loki_retrieval(self, test_config_path, test_db_path, clean_test_db):
        """
        Test logging without Loki, only to local database.
        Focuses on the new retrieval methods.
        """
        logger = Mogger(
            config_path=test_config_path,
            db_path=test_db_path
        )

        # Log multiple events
        logger.info(
            message="App started",
            category="system_events",
            event_type="startup",
            description="Application initialization complete",
            duration_ms=50.0,
        )

        logger.warning(
            message="Low memory",
            category="system_events",
            event_type="warning",
            description="Memory usage above 80%",
        )

        logger.error(
            message="Connection failed",
            category="system_events",
            event_type="error",
            description="Database connection timeout",
            duration_ms=5000.0,
        )

        # Test get_latest_logs
        latest = logger.get_latest_logs(category="system_events", limit=2)
        assert len(latest) == 2

        # Test get_oldest_logs
        oldest = logger.get_oldest_logs(category="system_events", limit=2)
        assert len(oldest) == 2
        assert oldest[0]["event_type"] == "startup"  # First one logged

        # Test search_logs
        error_logs = logger.search_logs(
            category="system_events",
            keyword="connection",
            fields=["description"]
        )
        assert len(error_logs) == 1
        assert "Database connection timeout" in error_logs[0]["description"]

        logger.close()

    def test_filtering_with_new_methods(self, test_config_path, test_db_path, clean_test_db):
        """Test that filters work correctly with new method names."""
        logger = Mogger(
            config_path=test_config_path,
            db_path=test_db_path
        )

        # Create logs with different event types
        for i in range(5):
            logger.info(
                message=f"Startup event {i}",
                category="system_events",
                event_type="startup",
                description=f"Startup description {i}",
            )

        for i in range(3):
            logger.info(
                message=f"Shutdown event {i}",
                category="system_events",
                event_type="shutdown",
                description=f"Shutdown description {i}",
            )

        # Get latest startup events only
        startup_logs = logger.get_latest_logs(
            category="system_events",
            limit=10,
            event_type="startup"
        )
        assert len(startup_logs) == 5
        assert all(log["event_type"] == "startup" for log in startup_logs)

        # Get oldest shutdown events
        shutdown_logs = logger.get_oldest_logs(
            category="system_events",
            limit=2,
            event_type="shutdown"
        )
        assert len(shutdown_logs) == 2
        assert all(log["event_type"] == "shutdown" for log in shutdown_logs)

        # Search within shutdown events only
        searched = logger.search_logs(
            category="system_events",
            keyword="Shutdown",
            event_type="shutdown"
        )
        assert len(searched) == 3

        logger.close()

    def test_time_based_retrieval(self, test_config_path, test_db_path, clean_test_db):
        """Test time-based log retrieval with get_logs_between."""
        from datetime import datetime, timedelta
        import time

        logger = Mogger(
            config_path=test_config_path,
            db_path=test_db_path
        )

        # Mark start time
        start_time = datetime.now()
        time.sleep(0.05)

        # Log first batch
        logger.info(
            message="First batch",
            category="system_events",
            event_type="batch1",
            description="First batch of logs",
        )
        time.sleep(0.05)

        # Mark middle time
        middle_time = datetime.now()
        time.sleep(0.05)

        # Log second batch
        logger.info(
            message="Second batch",
            category="system_events",
            event_type="batch2",
            description="Second batch of logs",
        )
        time.sleep(0.05)

        # Mark end time
        end_time = datetime.now()

        # Get all logs
        all_logs = logger.get_logs_between(
            category="system_events",
            start_time=start_time,
            end_time=end_time
        )
        assert len(all_logs) >= 2

        # Get logs from middle to end (should get batch2)
        recent_logs = logger.get_logs_between(
            category="system_events",
            start_time=middle_time,
            end_time=end_time
        )
        assert len(recent_logs) >= 1
        event_types = [log["event_type"] for log in recent_logs]
        assert "batch2" in event_types

        logger.close()


class TestMockIntegrationEdgeCases:
    """Test edge cases discovered from mock.py usage."""

    def test_optional_fields_in_logging(self, test_config_path, test_db_path, clean_test_db):
        """Test that optional fields (nullable) work correctly."""
        logger = Mogger(
            config_path=test_config_path,
            db_path=test_db_path
        )

        # Log with all fields (like in mock.py)
        logger.info(
            message="Full log",
            category="system_events",
            event_type="test",
            description="Test description",
            duration_ms=100.0,
        )

        # Log without optional duration_ms field
        logger.info(
            message="Partial log",
            category="system_events",
            event_type="test",
            description="Test without duration",
        )

        # Retrieve and verify
        logs = logger.get_latest_logs(category="system_events", limit=2)
        assert len(logs) == 2

        # One should have duration_ms, one shouldn't (or it's None)
        durations = [log.get("duration_ms") for log in logs]
        assert 100.0 in durations
        assert None in durations or any(d is None for d in durations)

        logger.close()

    def test_retrieval_with_limit_variations(self, test_config_path, test_db_path, clean_test_db):
        """Test different limit values in retrieval methods."""
        logger = Mogger(
            config_path=test_config_path,
            db_path=test_db_path
        )

        # Create 10 logs
        for i in range(10):
            logger.info(
                message=f"Log {i}",
                category="system_events",
                event_type=f"event_{i}",
                description=f"Description {i}",
            )

        # Test default limit (10)
        default_logs = logger.get_latest_logs(category="system_events")
        assert len(default_logs) == 10

        # Test custom limit (5, as in mock.py)
        limited_logs = logger.get_latest_logs(category="system_events", limit=5)
        assert len(limited_logs) == 5

        # Test limit=1
        single_log = logger.get_latest_logs(category="system_events", limit=1)
        assert len(single_log) == 1

        logger.close()
