"""
CSV Writer for Mogger - Handles writing logs to CSV files.
"""

import csv
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import MoggerConfig, TableConfig


class CSVWriter:
    """
    Manages writing log entries to CSV files.
    
    Each table gets its own CSV file in the format: <table_name>.logs.csv
    Files are stored in the configured directory under .mogger.logs/<instance_name>/
    """
    
    def __init__(self, config: MoggerConfig):
        """
        Initialize CSVWriter with configuration.
        
        Args:
            config: MoggerConfig with directory and table definitions
        """
        self._config = config
        self._base_dir = Path(config.directory.path).resolve()
        self._locks: Dict[str, threading.Lock] = {}
        self._table_configs: Dict[str, TableConfig] = {
            table.name: table for table in config.tables
        }
        
        # Create base directory
        self._base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize locks for each table
        for table in config.tables:
            self._locks[table.name] = threading.Lock()
            # Ensure CSV file exists with headers
            self._ensure_csv_file(table)
    
    def _get_csv_path(self, table_name: str) -> Path:
        """Get the path to a table's CSV file."""
        return self._base_dir / f"{table_name}.logs.csv"
    
    def _get_field_names(self, table: TableConfig) -> List[str]:
        """Get all field names for a table including system fields."""
        # System fields come first
        system_fields = ["id", "timestamp", "level", "message"]
        # Then user-defined fields
        user_fields = [field.name for field in table.fields]
        return system_fields + user_fields
    
    def _ensure_csv_file(self, table: TableConfig) -> None:
        """Ensure CSV file exists with proper headers."""
        csv_path = self._get_csv_path(table.name)
        
        if not csv_path.exists():
            field_names = self._get_field_names(table)
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(field_names)
    
    def _serialize_value(self, value: Any, field_type: str) -> str:
        """Serialize a value for CSV storage."""
        if value is None:
            return ""
        
        if field_type == "json":
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            return str(value)
        
        if field_type == "bool":
            return "true" if value else "false"
        
        return str(value)
    
    def write_log(
        self,
        table_name: str,
        log_id: str,
        timestamp: datetime,
        level: str,
        message: str,
        **kwargs: Any
    ) -> None:
        """
        Write a log entry to the appropriate CSV file.
        
        Args:
            table_name: Name of the table/category
            log_id: Unique ID for the log entry
            timestamp: Timestamp of the log
            level: Log level (DEBUG, INFO, etc.)
            message: Log message
            **kwargs: Additional fields defined in the table config
        """
        if table_name not in self._table_configs:
            raise ValueError(f"Unknown table: {table_name}")
        
        table = self._table_configs[table_name]
        csv_path = self._get_csv_path(table_name)
        
        # Build row data
        row = [
            log_id,
            timestamp.isoformat(),
            level,
            message
        ]
        
        # Add user-defined fields in order
        for field in table.fields:
            value = kwargs.get(field.name)
            serialized = self._serialize_value(value, field.type)
            row.append(serialized)
        
        # Write to CSV with lock for thread safety
        with self._locks[table_name]:
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
    
    def get_table_names(self) -> List[str]:
        """Get list of all table names."""
        return list(self._table_configs.keys())
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table is defined in config."""
        return table_name in self._table_configs
