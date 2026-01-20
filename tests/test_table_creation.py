"""
Tests to verify that tables defined in config are properly created in the database.
"""

import pytest
import sqlite3
from pathlib import Path


class TestTableCreation:
    """Test that database tables are created with correct schema."""

    def test_master_table_exists(self, logger, test_db_path):
        """Test that logs_master table is created."""
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='logs_master'
        """)
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == 'logs_master'

    def test_master_table_schema(self, logger, test_db_path):
        """Test that logs_master has correct columns."""
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        # Get table schema
        cursor.execute("PRAGMA table_info(logs_master)")
        columns = cursor.fetchall()
        conn.close()

        # Extract column names
        column_names = [col[1] for col in columns]

        # Verify required columns exist
        assert 'uuid' in column_names
        assert 'created_at' in column_names
        assert 'log_level' in column_names
        assert 'table_name' in column_names

    def test_custom_tables_exist(self, logger, test_db_path):
        """Test that all custom tables from config are created."""
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = cursor.fetchall()
        conn.close()

        table_names = [t[0] for t in tables]

        # Verify custom tables exist
        assert 'user_actions' in table_names
        assert 'errors' in table_names
        assert 'system_events' in table_names

    def test_user_actions_table_schema(self, logger, test_db_path):
        """Test that user_actions table has correct schema."""
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(user_actions)")
        columns = cursor.fetchall()
        conn.close()

        column_info = {col[1]: {'type': col[2], 'notnull': col[3]} for col in columns}

        # Verify base columns
        assert 'id' in column_info
        assert 'log_uuid' in column_info

        # Verify custom fields
        assert 'user_id' in column_info
        assert 'action' in column_info

    def test_errors_table_schema(self, logger, test_db_path):
        """Test that errors table has correct schema."""
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(errors)")
        columns = cursor.fetchall()
        conn.close()

        column_info = {col[1]: {'type': col[2], 'notnull': col[3]} for col in columns}

        # Verify base columns
        assert 'id' in column_info
        assert 'log_uuid' in column_info

        # Verify custom fields from mogger.config.yaml
        assert 'error_code' in column_info
        assert 'error_message' in column_info
        assert 'severity' in column_info

    def test_system_events_table_schema(self, logger, test_db_path):
        """Test that system_events table has correct schema."""
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(system_events)")
        columns = cursor.fetchall()
        conn.close()

        column_info = {col[1]: {'type': col[2], 'notnull': col[3]} for col in columns}

        # Verify base columns
        assert 'id' in column_info
        assert 'log_uuid' in column_info

        # Verify custom fields
        assert 'event_type' in column_info
        assert 'description' in column_info

    def test_indexed_columns(self, logger, test_db_path):
        """Test that indexed columns have indexes created."""
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        # Get all indexes
        cursor.execute("""
            SELECT name, tbl_name, sql FROM sqlite_master 
            WHERE type='index' AND sql IS NOT NULL
        """)
        indexes = cursor.fetchall()
        conn.close()

        index_info = [(idx[1], idx[2]) for idx in indexes]  # (table_name, sql)

        # Verify that master table columns are indexed
        master_indexes = [sql for table, sql in index_info if table == 'logs_master']
        assert any('created_at' in sql for sql in master_indexes)
        assert any('log_level' in sql for sql in master_indexes)
        assert any('table_name' in sql for sql in master_indexes)

    def test_nullable_fields(self, logger, test_db_path):
        """Test that nullable fields are correctly configured."""
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        # Check user_actions table
        cursor.execute("PRAGMA table_info(user_actions)")
        columns = cursor.fetchall()

        column_info = {col[1]: {'notnull': col[3]} for col in columns}

        # user_id and action should be NOT NULL (nullable: false by default)
        assert column_info['user_id']['notnull'] == 1
        assert column_info['action']['notnull'] == 1

        conn.close()

    def test_table_insert_matches_schema(self, logger, test_db_path):
        """Test that inserting a log actually creates rows in tables."""
        # Insert a log
        log_uuid = logger.info("Test message", category="user_actions",
                               user_id="test_user", action="test_action")

        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        # Check master table
        cursor.execute("SELECT * FROM logs_master WHERE uuid=?", (log_uuid,))
        master_row = cursor.fetchone()
        assert master_row is not None

        # Check custom table
        cursor.execute("SELECT * FROM user_actions WHERE log_uuid=?", (log_uuid,))
        custom_row = cursor.fetchone()
        assert custom_row is not None

        # Get column names for user_actions
        cursor.execute("PRAGMA table_info(user_actions)")
        columns = [col[1] for col in cursor.fetchall()]

        # Create dict from row
        row_dict = dict(zip(columns, custom_row))

        # Verify data
        assert row_dict['user_id'] == 'test_user'
        assert row_dict['action'] == 'test_action'
        assert row_dict['log_uuid'] == log_uuid

        conn.close()

    def test_missing_required_field_raises_error(self, logger):
        """Test that missing required fields raise an error."""
        # user_id is required (not nullable)
        with pytest.raises(ValueError, match="Required field.*not provided"):
            logger.info("Test", category="user_actions", action="test")

    def test_all_log_levels_insert_correctly(self, logger, test_db_path):
        """Test that all log levels insert correctly into master table."""
        logger.debug("Debug", category="system_events", event_type="debug", description="d")
        logger.info("Info", category="system_events", event_type="info", description="i")
        logger.warning("Warn", category="system_events", event_type="warn", description="w")
        logger.error("Error", category="errors", error_code=500, error_message="e", severity="high")
        logger.critical("Crit", category="errors", error_code=999, error_message="c", severity="critical")

        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT log_level FROM logs_master")
        levels = [row[0] for row in cursor.fetchall()]

        conn.close()

        assert 'DEBUG' in levels
        assert 'INFO' in levels
        assert 'WARNING' in levels
        assert 'ERROR' in levels
        assert 'CRITICAL' in levels


class TestTableCreationWithMessage:
    """Test table creation when tables have a 'message' field in schema."""

    def test_table_with_message_field(self, tmp_path):
        """Test creating a table that has a 'message' field defined."""
        from mogger import Mogger

        # Create config with message field
        config_path = tmp_path / "test_config.yaml"
        config_content = """
database:
  path: "test_with_message.db"
  wal_mode: false

terminal:
  enabled: false

tables:
  - name: app_logs
    fields:
      - name: message
        type: text
        nullable: false
      - name: user_id
        type: string
        nullable: true
"""
        config_path.write_text(config_content)

        # Initialize logger
        db_path = tmp_path / "test_with_message.db"
        logger = Mogger(str(config_path), db_path=str(db_path))

        # Check table schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(app_logs)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        conn.close()

        # Verify message field exists in schema
        assert 'message' in column_names
        assert 'user_id' in column_names

    def test_insert_with_message_field_in_schema(self, tmp_path):
        """Test that message parameter is inserted when table has message field."""
        from mogger import Mogger

        # Create config with message field
        config_path = tmp_path / "test_config.yaml"
        config_content = """
database:
  path: "test_with_message.db"
  wal_mode: false

terminal:
  enabled: false

tables:
  - name: app_logs
    fields:
      - name: message
        type: text
        nullable: false
      - name: user_id
        type: string
        nullable: true
"""
        config_path.write_text(config_content)

        # Initialize logger
        db_path = tmp_path / "test_with_message.db"
        logger = Mogger(str(config_path), db_path=str(db_path))

        # Insert log with message
        log_uuid = logger.info("This is my test message", category="app_logs", user_id="user123")

        # Verify message was inserted
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT message, user_id FROM app_logs WHERE log_uuid=?", (log_uuid,))
        row = cursor.fetchone()

        conn.close()

        assert row is not None
        assert row[0] == "This is my test message"
        assert row[1] == "user123"

    def test_message_not_inserted_when_not_in_schema(self, logger, test_db_path):
        """Test that message is not inserted when table doesn't have message field."""
        # user_actions table doesn't have a message field
        log_uuid = logger.info("Some message", category="user_actions",
                               user_id="user1", action="login")

        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        # Get columns
        cursor.execute("PRAGMA table_info(user_actions)")
        columns = [col[1] for col in cursor.fetchall()]

        # Get the row
        cursor.execute("SELECT * FROM user_actions WHERE log_uuid=?", (log_uuid,))
        row = cursor.fetchone()

        conn.close()

        # Verify message field doesn't exist
        assert 'message' not in columns
        # But the row should still exist
        assert row is not None


class TestDatabaseFileCreation:
    """Test database file creation and initialization."""

    def test_database_file_created(self, logger, test_db_path):
        """Test that database file is created."""
        assert test_db_path.exists()
        assert test_db_path.is_file()

    def test_database_file_is_valid_sqlite(self, logger, test_db_path):
        """Test that created file is a valid SQLite database."""
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        # Try a simple query
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        conn.close()

        # Should have at least one table
        assert len(tables) > 0

    def test_wal_mode_enabled(self, tmp_path):
        """Test that WAL mode is enabled when configured."""
        from mogger import Mogger

        config_path = tmp_path / "test_config.yaml"
        config_content = """
database:
  path: "test_wal.db"
  wal_mode: true

terminal:
  enabled: false

tables:
  - name: test_table
    fields:
      - name: field1
        type: string
"""
        config_path.write_text(config_content)

        db_path = tmp_path / "test_wal.db"
        logger = Mogger(str(config_path), db_path=str(db_path))

        # Check WAL mode
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        conn.close()

        assert mode.upper() == 'WAL'
