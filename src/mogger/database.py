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
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.orm import sessionmaker

from .models import MoggerConfig, TableConfig


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
    
    def close(self) -> None:
        """Close database connections and dispose of engine."""
        if self.__engine:
            self.__engine.dispose()
