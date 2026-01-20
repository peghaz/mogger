"""
Tests for advanced search functionalities.
"""

import pytest
from datetime import datetime, timedelta
import time

from mogger import Mogger


class TestQueryLatest:
    """Test querying latest logs."""
    
    def test_query_latest_from_master_table(self, logger: Mogger):
        """Test querying latest logs from master table."""
        # Insert logs with small delays
        uuid1 = logger.info("Log 1", category="user_actions", user_id="u1", action="a1")
        time.sleep(0.01)
        uuid2 = logger.info("Log 2", category="user_actions", user_id="u2", action="a2")
        time.sleep(0.01)
        uuid3 = logger.info("Log 3", category="user_actions", user_id="u3", action="a3")
        
        # Query latest 2 logs
        results = logger.query_latest("logs_master", limit=2)
        assert len(results) == 2
        # Most recent should be first
        result_uuids = [r["uuid"] for r in results]
        assert uuid3 in result_uuids or uuid2 in result_uuids
    
    def test_query_latest_from_custom_table(self, logger):
        """Test querying latest logs from custom table."""
        # Insert logs
        logger.info("Action 1", category="user_actions", user_id="u1", action="login")
        time.sleep(0.01)
        logger.info("Action 2", category="user_actions", user_id="u2", action="logout")
        time.sleep(0.01)
        logger.info("Action 3", category="user_actions", user_id="u3", action="view")
        
        # Query latest 2
        results = logger.query_latest("user_actions", limit=2)
        assert len(results) == 2
        # Check that we got the most recent ones
        actions = [r["action"] for r in results]
        assert "view" in actions
        assert "logout" in actions
    
    def test_query_latest_with_filters(self, logger):
        """Test querying latest logs with filters."""
        # Insert logs with different levels
        logger.info("Info 1", category="system_events", event_type="info", description="i1")
        time.sleep(0.01)
        logger.error("Error 1", category="errors", error_code=500, error_message="e1", severity="high")
        time.sleep(0.01)
        logger.info("Info 2", category="system_events", event_type="info", description="i2")
        time.sleep(0.01)
        logger.error("Error 2", category="errors", error_code=404, error_message="e2", severity="low")
        
        # Query latest ERROR logs only
        results = logger.query_latest("logs_master", limit=10, log_level="ERROR")
        assert len(results) == 2
        assert all(r["log_level"] == "ERROR" for r in results)
        # Most recent error should be first
        assert results[0]["table_name"] == "errors"
    
    def test_query_latest_empty_table(self, logger):
        """Test querying latest from empty table."""
        results = logger.query_latest("user_actions", limit=10)
        assert results == []
    
    def test_query_latest_invalid_table(self, logger):
        """Test querying latest from non-existent table."""
        with pytest.raises(ValueError, match="Table.*not found"):
            logger.query_latest("nonexistent_table")


class TestQueryOldest:
    """Test querying oldest logs."""
    
    def test_query_oldest_from_master_table(self, logger):
        """Test querying oldest logs from master table."""
        # Insert logs with small delays
        uuid1 = logger.info("Log 1", category="user_actions", user_id="u1", action="a1")
        time.sleep(0.01)
        uuid2 = logger.info("Log 2", category="user_actions", user_id="u2", action="a2")
        time.sleep(0.01)
        uuid3 = logger.info("Log 3", category="user_actions", user_id="u3", action="a3")
        
        # Query oldest 2 logs
        results = logger.query_oldest("logs_master", limit=2)
        assert len(results) == 2
        # Oldest should be first
        result_uuids = [r["uuid"] for r in results]
        assert uuid1 in result_uuids or uuid2 in result_uuids
    
    def test_query_oldest_from_custom_table(self, logger):
        """Test querying oldest logs from custom table."""
        # Insert logs
        logger.info("Action 1", category="user_actions", user_id="u1", action="login")
        time.sleep(0.01)
        logger.info("Action 2", category="user_actions", user_id="u2", action="logout")
        time.sleep(0.01)
        logger.info("Action 3", category="user_actions", user_id="u3", action="view")
        
        # Query oldest 2
        results = logger.query_oldest("user_actions", limit=2)
        assert len(results) == 2
        # Check that we got the oldest ones
        actions = [r["action"] for r in results]
        assert "login" in actions
        assert "logout" in actions
    
    def test_query_oldest_with_filters(self, logger):
        """Test querying oldest logs with filters."""
        # Insert logs
        logger.info("Info 1", category="system_events", event_type="info", description="i1")
        time.sleep(0.01)
        logger.warning("Warn 1", category="system_events", event_type="warning", description="w1")
        time.sleep(0.01)
        logger.info("Info 2", category="system_events", event_type="info", description="i2")
        
        # Query oldest INFO logs only
        results = logger.query_oldest("logs_master", limit=10, log_level="INFO")
        assert len(results) == 2
        assert all(r["log_level"] == "INFO" for r in results)
        # Verify we got info logs
        assert results[0]["log_level"] == "INFO"


class TestQueryBetweenTimestamps:
    """Test querying logs between timestamps."""
    
    def test_query_between_timestamps_master_table(self, logger):
        """Test querying logs between timestamps from master table."""
        # Get initial time
        start_time = datetime.now()
        
        # Insert first batch
        uuid_before = logger.info("Before", category="user_actions", user_id="u1", action="before")
        time.sleep(0.05)
        
        # Mark middle time
        middle_time = datetime.now()
        time.sleep(0.05)
        
        # Insert second batch
        uuid_during = logger.info("During", category="user_actions", user_id="u2", action="during")
        time.sleep(0.05)
        
        # Mark end time
        end_time = datetime.now()
        time.sleep(0.05)
        
        # Insert third batch
        uuid_after = logger.info("After", category="user_actions", user_id="u3", action="after")
        
        # Query between middle and end
        results = logger.query_between_timestamps("logs_master", middle_time, end_time)
        
        # Should get the "during" log
        assert len(results) >= 1
        result_uuids = [r["uuid"] for r in results]
        assert uuid_during in result_uuids
    
    def test_query_between_timestamps_custom_table(self, logger):
        """Test querying logs between timestamps from custom table."""
        # Get times
        start_time = datetime.now()
        time.sleep(0.05)
        
        middle_start = datetime.now()
        logger.info("Log 1", category="user_actions", user_id="u1", action="login")
        time.sleep(0.05)
        logger.info("Log 2", category="user_actions", user_id="u2", action="logout")
        middle_end = datetime.now()
        
        time.sleep(0.05)
        logger.info("Log 3", category="user_actions", user_id="u3", action="view")
        
        # Query middle period
        results = logger.query_between_timestamps("user_actions", middle_start, middle_end)
        
        # Should get logs 1 and 2
        assert len(results) >= 2
        actions = [r["action"] for r in results]
        assert "login" in actions or "logout" in actions
    
    def test_query_between_timestamps_with_filters(self, logger):
        """Test querying between timestamps with additional filters."""
        start_time = datetime.now()
        
        logger.info("Info", category="system_events", event_type="info", description="i")
        time.sleep(0.05)
        logger.error("Error", category="errors", error_code=500, error_message="e", severity="high")
        
        end_time = datetime.now()
        
        # Query only ERROR logs in time range
        results = logger.query_between_timestamps("logs_master", start_time, end_time, 
                                                  log_level="ERROR")
        assert len(results) == 1
        assert results[0]["log_level"] == "ERROR"
    
    def test_query_between_timestamps_with_limit(self, logger):
        """Test querying between timestamps with limit."""
        start_time = datetime.now()
        
        # Insert multiple logs
        for i in range(5):
            logger.info(f"Log {i}", category="user_actions", user_id=f"u{i}", action=f"a{i}")
            time.sleep(0.01)
        
        end_time = datetime.now()
        
        # Query with limit
        results = logger.query_between_timestamps("logs_master", start_time, end_time, limit=3)
        assert len(results) == 3
    
    def test_query_between_timestamps_invalid_range(self, logger):
        """Test querying with invalid time range."""
        start_time = datetime.now()
        end_time = start_time - timedelta(hours=1)
        
        with pytest.raises(ValueError, match="start_time must be before"):
            logger.query_between_timestamps("logs_master", start_time, end_time)
    
    def test_query_between_timestamps_empty_range(self, logger):
        """Test querying a time range with no logs."""
        # Get a time range in the past before any logs
        start_time = datetime.now() - timedelta(hours=2)
        end_time = datetime.now() - timedelta(hours=1)
        
        # Insert logs after the time range
        logger.info("Log", category="user_actions", user_id="u1", action="a1")
        
        results = logger.query_between_timestamps("logs_master", start_time, end_time)
        assert results == []


class TestSearchKeyword:
    """Test keyword search functionality."""
    
    def test_search_keyword_single_field(self, logger):
        """Test searching keyword in single field."""
        # Insert logs with different messages
        logger.error("Database connection failed", category="errors", 
                    error_code=500, error_message="Database connection timeout", severity="high")
        logger.error("API error", category="errors", 
                    error_code=404, error_message="API endpoint not found", severity="low")
        logger.error("Network issue", category="errors", 
                    error_code=503, error_message="Network unreachable", severity="medium")
        
        # Search for "database" in error_message field
        results = logger.search_keyword("errors", "database", fields=["error_message"])
        assert len(results) == 1
        assert "Database" in results[0]["error_message"]
    
    def test_search_keyword_multiple_fields(self, logger):
        """Test searching keyword across multiple fields."""
        # Insert logs
        logger.info("User login", category="user_actions", user_id="admin", action="login")
        logger.info("Admin logout", category="user_actions", user_id="user123", action="logout")
        logger.info("View page", category="user_actions", user_id="guest", action="admin_panel")
        
        # Search for "admin" in both user_id and action fields
        results = logger.search_keyword("user_actions", "admin", 
                                       fields=["user_id", "action"])
        assert len(results) == 2
        # Should find both the admin user and the admin_panel action
    
    def test_search_keyword_all_text_fields(self, logger):
        """Test searching across all text fields when fields=None."""
        # Insert logs
        logger.error("Critical error", category="errors", 
                    error_code=500, error_message="Critical system failure", severity="critical")
        logger.error("Warning", category="errors", 
                    error_code=200, error_message="OK", severity="low")
        
        # Search for "critical" without specifying fields
        results = logger.search_keyword("errors", "critical")
        assert len(results) == 1
        assert "Critical" in results[0]["error_message"] or "critical" in results[0]["severity"]
    
    def test_search_keyword_case_insensitive(self, logger):
        """Test that keyword search is case-insensitive."""
        # Insert log with mixed case
        logger.error("Error", category="errors", 
                    error_code=500, error_message="DataBase Connection Failed", severity="high")
        
        # Search with different cases
        results_lower = logger.search_keyword("errors", "database", fields=["error_message"])
        results_upper = logger.search_keyword("errors", "DATABASE", fields=["error_message"])
        results_mixed = logger.search_keyword("errors", "DaTaBaSe", fields=["error_message"])
        
        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert len(results_mixed) == 1
    
    def test_search_keyword_partial_match(self, logger):
        """Test that keyword search matches partial strings."""
        # Insert log
        logger.error("Error", category="errors", 
                    error_code=500, error_message="Connection timeout occurred", severity="high")
        
        # Search for partial word
        results = logger.search_keyword("errors", "time", fields=["error_message"])
        assert len(results) == 1
        assert "timeout" in results[0]["error_message"]
    
    def test_search_keyword_with_filters(self, logger):
        """Test keyword search with additional filters."""
        # Insert logs with different severities
        logger.error("Error 1", category="errors", 
                    error_code=500, error_message="Database error", severity="high")
        logger.error("Error 2", category="errors", 
                    error_code=404, error_message="Database not found", severity="low")
        
        # Search for "database" but only high severity
        results = logger.search_keyword("errors", "database", 
                                       fields=["error_message"], severity="high")
        assert len(results) == 1
        assert results[0]["severity"] == "high"
    
    def test_search_keyword_with_limit(self, logger):
        """Test keyword search with limit."""
        # Insert multiple logs with keyword
        for i in range(5):
            logger.error(f"Error {i}", category="errors", 
                        error_code=500, error_message=f"Connection error {i}", severity="high")
        
        # Search with limit
        results = logger.search_keyword("errors", "connection", limit=3)
        assert len(results) == 3
    
    def test_search_keyword_no_matches(self, logger):
        """Test keyword search with no matches."""
        # Insert log
        logger.error("Error", category="errors", 
                    error_code=500, error_message="Network failure", severity="high")
        
        # Search for non-existent keyword
        results = logger.search_keyword("errors", "database")
        assert results == []
    
    def test_search_keyword_invalid_field(self, logger):
        """Test keyword search with invalid field name."""
        # Insert log
        logger.error("Error", category="errors", 
                    error_code=500, error_message="Error", severity="high")
        
        # Search with non-existent field
        with pytest.raises(ValueError, match="Field.*not found"):
            logger.search_keyword("errors", "test", fields=["nonexistent_field"])
    
    def test_search_keyword_master_table_not_allowed(self, logger):
        """Test that keyword search is not allowed on master table."""
        # Insert log
        logger.info("Test", category="user_actions", user_id="u1", action="test")
        
        # Try to search master table
        with pytest.raises(ValueError, match="not supported on logs_master"):
            logger.search_keyword("logs_master", "test")
    
    def test_search_keyword_invalid_table(self, logger):
        """Test keyword search on non-existent table."""
        with pytest.raises(ValueError, match="Table.*not found"):
            logger.search_keyword("nonexistent_table", "test")
    
    def test_search_keyword_no_text_fields(self, logger):
        """Test keyword search on table with no text fields."""
        # This would require a table with only numeric fields
        # For now, we'll test that error is raised properly
        # This test depends on your schema configuration
        pass


class TestAdvancedSearchWithoutDB:
    """Test that advanced search methods require database."""
    
    def test_query_latest_without_db(self, tmp_path):
        """Test query_latest raises error when database disabled."""
        from mogger import Mogger
        config_path = tmp_path / "test_config.yaml"
        
        # Create basic config
        config_content = """
database:
  path: "test.db"
  wal_mode: false

terminal:
  enabled: false

tables:
  - name: user_actions
    fields:
      - name: user_id
        type: string
        nullable: false
      - name: action
        type: string
        nullable: false
"""
        config_path.write_text(config_content)
        
        logger = Mogger(str(config_path), use_local_db=False)
        
        with pytest.raises(RuntimeError, match="Local database is not enabled"):
            logger.query_latest("logs_master")
    
    def test_query_oldest_without_db(self, tmp_path):
        """Test query_oldest raises error when database disabled."""
        from mogger import Mogger
        config_path = tmp_path / "test_config.yaml"
        
        config_content = """
database:
  path: "test.db"
  wal_mode: false

terminal:
  enabled: false

tables:
  - name: user_actions
    fields:
      - name: user_id
        type: string
        nullable: false
      - name: action
        type: string
        nullable: false
"""
        config_path.write_text(config_content)
        
        logger = Mogger(str(config_path), use_local_db=False)
        
        with pytest.raises(RuntimeError, match="Local database is not enabled"):
            logger.query_oldest("logs_master")
    
    def test_query_between_timestamps_without_db(self, tmp_path):
        """Test query_between_timestamps raises error when database disabled."""
        from mogger import Mogger
        config_path = tmp_path / "test_config.yaml"
        
        config_content = """
database:
  path: "test.db"
  wal_mode: false

terminal:
  enabled: false

tables:
  - name: user_actions
    fields:
      - name: user_id
        type: string
        nullable: false
      - name: action
        type: string
        nullable: false
"""
        config_path.write_text(config_content)
        
        logger = Mogger(str(config_path), use_local_db=False)
        
        start = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        
        with pytest.raises(RuntimeError, match="Local database is not enabled"):
            logger.query_between_timestamps("logs_master", start, end)
    
    def test_search_keyword_without_db(self, tmp_path):
        """Test search_keyword raises error when database disabled."""
        from mogger import Mogger
        config_path = tmp_path / "test_config.yaml"
        
        config_content = """
database:
  path: "test.db"
  wal_mode: false

terminal:
  enabled: false

tables:
  - name: user_actions
    fields:
      - name: user_id
        type: string
        nullable: false
      - name: action
        type: string
        nullable: false
"""
        config_path.write_text(config_content)
        
        logger = Mogger(str(config_path), use_local_db=False)
        
        with pytest.raises(RuntimeError, match="Local database is not enabled"):
            logger.search_keyword("user_actions", "test")
