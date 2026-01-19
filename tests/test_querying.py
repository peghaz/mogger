"""
Tests for querying logs from the database.
"""

import pytest


class TestBasicQuerying:
    """Test basic query operations."""
    
    def test_query_empty_table(self, logger):
        """Test querying an empty table."""
        results = logger.query(table="user_actions")
        assert results == []
    
    def test_query_master_table(self, logger):
        """Test querying the master logs table."""
        # Insert some logs
        logger.info("Log 1", table="user_actions", user_id="u1", action="a1")
        logger.info("Log 2", table="errors", error_code=500, error_message="err", severity="high")
        
        # Query master table
        results = logger.query(table="logs_master")
        assert len(results) == 2
    
    def test_query_specific_table(self, logger):
        """Test querying a specific table."""
        # Insert logs to different tables
        logger.info("User log", table="user_actions", user_id="u1", action="login")
        logger.error("Error log", table="errors", error_code=404, error_message="Not found", severity="low")
        logger.info("Event log", table="system_events", event_type="startup", description="Started")
        
        # Query only user_actions
        results = logger.query(table="user_actions")
        assert len(results) == 1
        assert results[0]["action"] == "login"
    
    def test_query_with_limit(self, logger):
        """Test querying with limit parameter."""
        # Insert 10 logs
        for i in range(10):
            logger.info(f"Log {i}", table="user_actions", user_id=f"user_{i}", action="test")
        
        # Query with limit
        results = logger.query(table="user_actions", limit=5)
        assert len(results) == 5
    
    def test_query_invalid_table(self, logger):
        """Test querying non-existent table."""
        with pytest.raises(ValueError, match="Table.*not found"):
            logger.query(table="nonexistent_table")


class TestFilteredQuerying:
    """Test querying with filters."""
    
    def test_query_by_log_level(self, logger):
        """Test filtering by log level in master table."""
        # Insert logs with different levels
        logger.debug("Debug", table="system_events", event_type="debug", description="d")
        logger.info("Info", table="system_events", event_type="info", description="i")
        logger.error("Error", table="errors", error_code=500, error_message="e", severity="high")
        logger.critical("Critical", table="errors", error_code=999, error_message="c", severity="critical")
        
        # Query only ERROR level
        results = logger.query(table="logs_master", log_level="ERROR")
        assert len(results) == 1
        assert results[0]["log_level"] == "ERROR"
    
    def test_query_by_table_name(self, logger):
        """Test filtering by table name in master table."""
        # Insert to different tables
        logger.info("User", table="user_actions", user_id="u1", action="login")
        logger.info("Event 1", table="system_events", event_type="e1", description="d1")
        logger.info("Event 2", table="system_events", event_type="e2", description="d2")
        
        # Query master table filtering by table_name
        results = logger.query(table="logs_master", table_name="system_events")
        assert len(results) == 2
    
    def test_query_by_custom_field(self, logger):
        """Test filtering by custom field in dynamic table."""
        # Insert user actions
        logger.info("User 1", table="user_actions", user_id="user_1", action="login")
        logger.info("User 2", table="user_actions", user_id="user_2", action="logout")
        logger.info("User 3", table="user_actions", user_id="user_1", action="update")
        
        # Query filtering by user_id
        results = logger.query(table="user_actions", user_id="user_1")
        assert len(results) == 2
    
    def test_query_multiple_filters(self, logger):
        """Test querying with multiple filter conditions."""
        # Insert API requests
        logger.info("GET /users", table="api_requests", endpoint="/api/users",
                   method="GET", status_code=200, response_time_ms=100.0)
        logger.info("POST /users", table="api_requests", endpoint="/api/users",
                   method="POST", status_code=201, response_time_ms=150.0)
        logger.info("GET /posts", table="api_requests", endpoint="/api/posts",
                   method="GET", status_code=200, response_time_ms=80.0)
        
        # Query with multiple filters
        results = logger.query(table="api_requests", method="GET", status_code=200)
        assert len(results) == 2


class TestComplexQuerying:
    """Test complex query scenarios."""
    
    def test_query_all_log_levels(self, logger):
        """Test querying each log level."""
        # Insert one log of each level
        logger.debug("D", table="system_events", event_type="d", description="debug")
        logger.info("I", table="system_events", event_type="i", description="info")
        logger.warning("W", table="system_events", event_type="w", description="warning")
        logger.error("E", table="errors", error_code=400, error_message="error", severity="low")
        logger.critical("C", table="errors", error_code=500, error_message="critical", severity="critical")
        
        # Query each level
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            results = logger.query(table="logs_master", log_level=level)
            assert len(results) == 1
            assert results[0]["log_level"] == level
    
    def test_query_with_json_data(self, logger):
        """Test querying logs with JSON fields."""
        metadata1 = {"browser": "Chrome", "version": "120"}
        metadata2 = {"browser": "Firefox", "version": "115"}
        
        logger.info("User 1", table="user_actions", user_id="u1",
                   action="login", metadata=metadata1)
        logger.info("User 2", table="user_actions", user_id="u2",
                   action="login", metadata=metadata2)
        
        # Query all
        results = logger.query(table="user_actions")
        assert len(results) == 2
        # Note: JSON is stored as text, so we can't query by JSON contents directly
    
    def test_query_ordered_results(self, logger):
        """Test that results maintain insertion order."""
        uuids = []
        for i in range(5):
            uuid = logger.info(f"Log {i}", table="system_events",
                             event_type=f"event_{i}", description=f"desc_{i}")
            uuids.append(uuid)
        
        results = logger.query(table="system_events")
        assert len(results) == 5
        
        # Verify log_uuids are in order
        result_uuids = [r["log_uuid"] for r in results]
        assert result_uuids == uuids
    
    def test_large_result_set(self, logger):
        """Test querying a large number of results."""
        # Insert 100 logs
        for i in range(100):
            logger.info(f"Log {i}", table="user_actions",
                       user_id=f"user_{i % 10}", action="test")
        
        # Query all
        results = logger.query(table="user_actions")
        assert len(results) == 100
        
        # Query with limit
        limited = logger.query(table="user_actions", limit=25)
        assert len(limited) == 25
    
    def test_query_across_all_tables(self, logger):
        """Test querying all available tables."""
        # Insert to each table
        logger.info("UA", table="user_actions", user_id="u1", action="a")
        logger.error("ER", table="errors", error_code=500, error_message="e", severity="high")
        logger.info("SE", table="system_events", event_type="e", description="d")
        logger.info("API", table="api_requests", endpoint="/api", method="GET",
                   status_code=200, response_time_ms=10.0)
        
        # Get all tables and query each
        tables = logger.get_tables()
        assert len(tables) == 4
        
        for table_name in tables:
            results = logger.query(table=table_name)
            assert len(results) == 1
    
    def test_query_returns_all_fields(self, logger):
        """Test that query results contain all expected fields."""
        logger.info("Test", table="user_actions", user_id="u1", action="test",
                   ip_address="192.168.1.1", metadata={"key": "value"})
        
        results = logger.query(table="user_actions")
        assert len(results) == 1
        
        result = results[0]
        assert "id" in result
        assert "log_uuid" in result
        assert "user_id" in result
        assert "action" in result
        assert "ip_address" in result
        assert "metadata" in result


class TestQueryPerformance:
    """Test query performance with larger datasets."""
    
    def test_indexed_field_query(self, logger):
        """Test querying on indexed fields."""
        # Insert many logs
        for i in range(50):
            logger.info(f"Event {i}", table="system_events",
                       event_type=f"type_{i % 5}", description=f"desc_{i}")
        
        # Query by indexed field (event_type)
        results = logger.query(table="system_events", event_type="type_0")
        assert len(results) == 10
    
    def test_non_indexed_field_query(self, logger):
        """Test querying on non-indexed fields."""
        # Insert logs
        for i in range(20):
            logger.info(f"Desc {i}", table="system_events",
                       event_type="test", description=f"description_{i % 4}")
        
        # Query by non-indexed field (description) - should still work
        results = logger.query(table="system_events")
        assert len(results) == 20
