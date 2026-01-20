"""
Database management for Mogger logging library.
Handles SQLite connections, table creation, and data persistence.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    or_,
    desc,
    asc,
)
from sqlalchemy.orm import sessionmaker

from .models import MoggerConfig


class DatabaseManager:
    """
    Manages SQLite database connections and operations for Mogger.

    Handles:
    - Database initialization and connection management
    - Dynamic table creation from YAML configuration
    - Master table for UUID tracking
    - Log insertion and querying
    - Type serialization for different field types
    """

    def __init__(self, config: MoggerConfig):
        """
        Initialize the database manager.

        Args:
            config: Validated MoggerConfig instance
        """
        self.__config = config
        self.__engine = None
        self.__session_factory = None
        self.__metadata = MetaData()
        self.__tables: Dict[str, Any] = {}
        self.__master_table = None

        self.__initialize_database()

    def __initialize_database(self) -> None:
        """Initialize SQLite database and create tables."""
        db_path = Path(self.__config.database.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine
        db_url = f"sqlite:///{db_path}"
        self.__engine = create_engine(db_url, echo=False)

        # Enable WAL mode if configured
        if self.__config.database.wal_mode:
            from sqlalchemy import text
            with self.__engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.commit()

        # Create master table for UUID tracking
        self.__create_master_table()

        # Create dynamic tables from config
        self.__create_dynamic_tables()

        # Create all tables
        self.__metadata.create_all(self.__engine)

        # Create session factory
        self.__session_factory = sessionmaker(bind=self.__engine)

    def __create_master_table(self) -> None:
        """Create the master table that tracks all log UUIDs."""
        self.__master_table = Table(
            'logs_master',
            self.__metadata,
            Column('uuid', String(36), primary_key=True),
            Column('created_at', DateTime, nullable=False, index=True),
            Column('log_level', String(20), nullable=False, index=True),
            Column('table_name', String(100), nullable=False, index=True),
        )

    def __create_dynamic_tables(self) -> None:
        """Create dynamic tables based on YAML configuration."""
        type_mapping = self.__get_type_mapping()

        for table_config in self.__config.tables:
            columns = [
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('log_uuid', String(36), nullable=False, index=True),
            ]

            for field in table_config.fields:
                field_type = type_mapping.get(field.type)
                if field_type is None:
                    raise ValueError(f"Unsupported field type: {field.type}")

                column = Column(
                    field.name,
                    field_type,
                    nullable=field.nullable,
                    index=field.indexed  # Add index directly to column
                )
                columns.append(column)

            table = Table(table_config.name, self.__metadata, *columns)

            self.__tables[table_config.name] = {
                'table': table,
                'config': table_config
            }

    def __get_type_mapping(self) -> Dict[str, Any]:
        """Get mapping between YAML types and SQLAlchemy types."""
        return {
            'string': String(255),
            'text': Text,
            'integer': Integer,
            'float': Float,
            'boolean': Boolean,
            'json': Text,
            'datetime': DateTime,
        }

    def __serialize_value(self, value: Any, field_type: str) -> Any:
        """Serialize value based on field type."""
        if field_type == 'json':
            return json.dumps(value) if value is not None else None
        elif field_type == 'datetime' and isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    def insert_log(self, log_uuid: str, level: str, table: str, created_at: datetime,
                   context_data: Dict[str, Any], **kwargs) -> None:
        """
        Insert a log entry into the database.

        Args:
            log_uuid: UUID for the log entry
            level: Log level (DEBUG, INFO, etc.)
            table: Target table name
            created_at: Timestamp of log creation
            context_data: Additional context data to include
            **kwargs: Field values for the log entry

        Raises:
            ValueError: If table not found or required fields missing
            RuntimeError: If database insertion fails
        """
        if table not in self.__tables:
            raise ValueError(f"Table '{table}' not found in configuration")

        session = self.__session_factory()

        try:
            # Insert into master table
            master_insert = self.__master_table.insert().values(
                uuid=log_uuid,
                created_at=created_at,
                log_level=level,
                table_name=table
            )
            session.execute(master_insert)

            # Prepare data for dynamic table
            table_info = self.__tables[table]
            table_obj = table_info['table']
            table_config = table_info['config']

            # Build insert data
            insert_data = {'log_uuid': log_uuid}

            # Get field names for validation
            field_names = {field.name for field in table_config.fields}

            for field in table_config.fields:
                if field.name in kwargs:
                    value = self.__serialize_value(kwargs[field.name], field.type)
                    insert_data[field.name] = value
                elif not field.nullable:
                    raise ValueError(f"Required field '{field.name}' not provided")

            # Add context data only if fields exist in table schema
            for key, value in context_data.items():
                if key in field_names and key not in insert_data:
                    # Find field config for type serialization
                    field_config = next((f for f in table_config.fields if f.name == key), None)
                    if field_config:
                        insert_data[key] = self.__serialize_value(value, field_config.type)

            # Insert into dynamic table
            dynamic_insert = table_obj.insert().values(**insert_data)
            session.execute(dynamic_insert)

            session.commit()

        except ValueError:
            # Re-raise ValueError as-is (for required field validation)
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise RuntimeError(f"Failed to insert log: {e}")
        finally:
            session.close()

    def query(self, table: str, limit: Optional[int] = None, **filters) -> List[Dict[str, Any]]:
        """
        Query logs from a specific table.

        Args:
            table: Table name to query
            limit: Maximum number of results
            **filters: Field filters (e.g., log_level="ERROR")

        Returns:
            List of log entries as dictionaries

        Raises:
            ValueError: If table not found
        """
        if table == 'logs_master':
            table_obj = self.__master_table
        elif table in self.__tables:
            table_obj = self.__tables[table]['table']
        else:
            raise ValueError(f"Table '{table}' not found")

        session = self.__session_factory()

        try:
            query = session.query(table_obj)

            # Apply filters
            for field, value in filters.items():
                if hasattr(table_obj.c, field):
                    query = query.filter(getattr(table_obj.c, field) == value)

            # Apply limit
            if limit:
                query = query.limit(limit)

            results = query.all()

            # Convert to dictionaries
            return [dict(row._mapping) for row in results]

        finally:
            session.close()

    def get_tables(self) -> List[str]:
        """Get list of all available log tables."""
        return list(self.__tables.keys())

    def table_exists(self, table: str) -> bool:
        """Check if a table exists in the configuration."""
        return table in self.__tables

    def query_latest(self, table: str, limit: int = 10, **filters) -> List[Dict[str, Any]]:
        """
        Query the most recent logs from a specific table.

        Args:
            table: Table name to query (can be 'logs_master' or any configured table)
            limit: Maximum number of results (default: 10)
            **filters: Field filters (e.g., log_level="ERROR")

        Returns:
            List of log entries as dictionaries, ordered by most recent first

        Raises:
            ValueError: If table not found
        """
        if table == 'logs_master':
            table_obj = self.__master_table
            order_column = self.__master_table.c.created_at
        elif table in self.__tables:
            # For custom tables, we'll join with master table to get created_at
            return self.__query_with_order(table, order_column='created_at',
                                           ascending=False, limit=limit, **filters)
        else:
            raise ValueError(f"Table '{table}' not found")

        session = self.__session_factory()

        try:
            query = session.query(table_obj)

            # Apply filters
            for field, value in filters.items():
                if hasattr(table_obj.c, field):
                    query = query.filter(getattr(table_obj.c, field) == value)

            # Order by created_at descending (most recent first)
            query = query.order_by(desc(order_column)).limit(limit)

            results = query.all()
            return [dict(row._mapping) for row in results]

        finally:
            session.close()

    def query_oldest(self, table: str, limit: int = 10, **filters) -> List[Dict[str, Any]]:
        """
        Query the oldest logs from a specific table.

        Args:
            table: Table name to query (can be 'logs_master' or any configured table)
            limit: Maximum number of results (default: 10)
            **filters: Field filters (e.g., log_level="ERROR")

        Returns:
            List of log entries as dictionaries, ordered by oldest first

        Raises:
            ValueError: If table not found
        """
        if table == 'logs_master':
            table_obj = self.__master_table
            order_column = self.__master_table.c.created_at
        elif table in self.__tables:
            # For custom tables, we'll join with master table to get created_at
            return self.__query_with_order(table, order_column='created_at',
                                           ascending=True, limit=limit, **filters)
        else:
            raise ValueError(f"Table '{table}' not found")

        session = self.__session_factory()

        try:
            query = session.query(table_obj)

            # Apply filters
            for field, value in filters.items():
                if hasattr(table_obj.c, field):
                    query = query.filter(getattr(table_obj.c, field) == value)

            # Order by created_at ascending (oldest first)
            query = query.order_by(asc(order_column)).limit(limit)

            results = query.all()
            return [dict(row._mapping) for row in results]

        finally:
            session.close()

    def query_between_timestamps(self, table: str, start_time: datetime,
                                 end_time: datetime, limit: Optional[int] = None,
                                 **filters) -> List[Dict[str, Any]]:
        """
        Query logs between two timestamps.

        Args:
            table: Table name to query (can be 'logs_master' or any configured table)
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            limit: Maximum number of results (optional)
            **filters: Field filters (e.g., log_level="ERROR")

        Returns:
            List of log entries as dictionaries, ordered by most recent first

        Raises:
            ValueError: If table not found or start_time > end_time
        """
        if start_time > end_time:
            raise ValueError("start_time must be before or equal to end_time")

        if table == 'logs_master':
            table_obj = self.__master_table
            time_column = self.__master_table.c.created_at
        elif table in self.__tables:
            # For custom tables, join with master to get created_at
            return self.__query_with_time_range(table, start_time, end_time, limit, **filters)
        else:
            raise ValueError(f"Table '{table}' not found")

        session = self.__session_factory()

        try:
            query = session.query(table_obj)

            # Apply time range filter
            query = query.filter(time_column >= start_time, time_column <= end_time)

            # Apply additional filters
            for field, value in filters.items():
                if hasattr(table_obj.c, field):
                    query = query.filter(getattr(table_obj.c, field) == value)

            # Order by created_at descending (most recent first)
            query = query.order_by(desc(time_column))

            if limit:
                query = query.limit(limit)

            results = query.all()
            return [dict(row._mapping) for row in results]

        finally:
            session.close()

    def search_keyword(self, table: str, keyword: str, fields: Optional[List[str]] = None,
                       limit: Optional[int] = None, **filters) -> List[Dict[str, Any]]:
        """
        Search for logs containing a keyword in specified fields.

        Args:
            table: Table name to query (cannot be 'logs_master' as it has no text fields)
            keyword: Keyword to search for (case-insensitive)
            fields: List of field names to search in. If None, searches all string/text fields
            limit: Maximum number of results (optional)
            **filters: Additional field filters (e.g., log_level="ERROR")

        Returns:
            List of log entries as dictionaries where at least one field contains the keyword

        Raises:
            ValueError: If table not found or is logs_master
        """
        if table == 'logs_master':
            raise ValueError("Keyword search is not supported on logs_master table")

        if table not in self.__tables:
            raise ValueError(f"Table '{table}' not found")

        table_obj = self.__tables[table]['table']
        table_config = self.__tables[table]['config']

        # Determine which fields to search
        if fields is None:
            # Search all string and text fields
            search_fields = [
                field.name for field in table_config.fields
                if field.type in ['string', 'text']
            ]
        else:
            # Validate provided fields exist
            available_fields = {field.name for field in table_config.fields}
            search_fields = []
            for field in fields:
                if field not in available_fields:
                    raise ValueError(f"Field '{field}' not found in table '{table}'")
                search_fields.append(field)

        if not search_fields:
            raise ValueError(f"No searchable text fields found in table '{table}'")

        session = self.__session_factory()

        try:
            query = session.query(table_obj)

            # Build OR condition for keyword search across fields
            or_conditions = []
            for field_name in search_fields:
                if hasattr(table_obj.c, field_name):
                    column = getattr(table_obj.c, field_name)
                    # Case-insensitive search using LIKE
                    or_conditions.append(column.ilike(f"%{keyword}%"))

            if or_conditions:
                query = query.filter(or_(*or_conditions))

            # Apply additional filters
            for field, value in filters.items():
                if hasattr(table_obj.c, field):
                    query = query.filter(getattr(table_obj.c, field) == value)

            # Apply limit
            if limit:
                query = query.limit(limit)

            results = query.all()
            return [dict(row._mapping) for row in results]

        finally:
            session.close()

    def __query_with_order(self, table: str, order_column: str, ascending: bool = True,
                           limit: Optional[int] = None, **filters) -> List[Dict[str, Any]]:
        """
        Helper method to query custom tables with ordering by joining with master table.
        """
        table_obj = self.__tables[table]['table']
        session = self.__session_factory()

        try:
            # Join custom table with master table on log_uuid
            query = session.query(table_obj).join(
                self.__master_table,
                table_obj.c.log_uuid == self.__master_table.c.uuid
            )

            # Apply filters on custom table columns
            for field, value in filters.items():
                if hasattr(table_obj.c, field):
                    query = query.filter(getattr(table_obj.c, field) == value)

            # Order by master table's created_at
            if ascending:
                query = query.order_by(asc(self.__master_table.c.created_at))
            else:
                query = query.order_by(desc(self.__master_table.c.created_at))

            if limit:
                query = query.limit(limit)

            results = query.all()
            return [dict(row._mapping) for row in results]

        finally:
            session.close()

    def __query_with_time_range(self, table: str, start_time: datetime,
                                end_time: datetime, limit: Optional[int] = None,
                                **filters) -> List[Dict[str, Any]]:
        """
        Helper method to query custom tables with time range by joining with master table.
        """
        table_obj = self.__tables[table]['table']
        session = self.__session_factory()

        try:
            # Join custom table with master table on log_uuid
            query = session.query(table_obj).join(
                self.__master_table,
                table_obj.c.log_uuid == self.__master_table.c.uuid
            )

            # Apply time range filter on master table
            query = query.filter(
                self.__master_table.c.created_at >= start_time,
                self.__master_table.c.created_at <= end_time
            )

            # Apply additional filters on custom table columns
            for field, value in filters.items():
                if hasattr(table_obj.c, field):
                    query = query.filter(getattr(table_obj.c, field) == value)

            # Order by created_at descending (most recent first)
            query = query.order_by(desc(self.__master_table.c.created_at))

            if limit:
                query = query.limit(limit)

            results = query.all()
            return [dict(row._mapping) for row in results]

        finally:
            session.close()

    def close(self) -> None:
        """Close database connections and dispose of engine."""
        if self.__engine:
            self.__engine.dispose()
