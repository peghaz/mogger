"""
Mogger - A custom logging library with SQLite persistence and terminal output.
"""

import uuid as uuid_lib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import ValidationError
from rich.console import Console

from .database import DatabaseManager
from .models import MoggerConfig
from .loki import LokiConfig, LokiLogger


class Mogger:
    """
    Custom logger with SQLite persistence and configurable terminal output.

    Features:
    - YAML-driven schema configuration
    - SQLite database with relational design
    - Colored terminal output
    - UUID tracking for all logs
    - Multiple log tables with custom fields
    """

    # Log level constants
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def __init__(self, config_path: Optional[Union[str, Path]] = None, db_path: Optional[str] = None, loki_config: Optional[LokiConfig] = None):
        """
        Initialize Mogger with configuration file.

        Args:
            config_path: Path to YAML configuration file. If not provided, will search for
                        'mogger_config.yaml', 'mogger.config.yaml', or '.mogger.yaml' 
                        in the current working directory.
            db_path: Optional override for database path
            loki_config: Optional LokiConfig for sending logs to Loki server
        """
        self.__config_path = self.__find_config_file(config_path)
        self.__config: Optional[MoggerConfig] = None
        self.__db_manager: Optional[DatabaseManager] = None
        self.__context_data: Dict[str, Any] = {}
        self.__console = Console()  # Rich console for colored output
        self.__loki_logger: Optional[LokiLogger] = None

        # Load and validate configuration
        self.__load_config()

        # Override db path if provided
        if db_path:
            self.__config.database.path = db_path

        # Initialize database manager
        self.__db_manager = DatabaseManager(self.__config)
        
        # Initialize Loki logger if config provided
        if loki_config is not None:
            self.__loki_logger = LokiLogger(loki_config)
    
    def __find_config_file(self, config_path: Optional[Union[str, Path]]) -> Path:
        """
        Find the configuration file path.
        
        Args:
            config_path: User-provided config path or None
            
        Returns:
            Path to configuration file
            
        Raises:
            FileNotFoundError: If no config file is found
        """
        if config_path is not None:
            return Path(config_path)
        
        # Search for config files in current working directory
        cwd = Path.cwd()
        config_names = [
            "mogger_config.yaml",
            "mogger.config.yaml",
            ".mogger.yaml",
            "mogger_config.yml",
            "mogger.config.yml",
            ".mogger.yml"
        ]
        
        for config_name in config_names:
            config_file = cwd / config_name
            if config_file.exists():
                return config_file
        
        # If no config file found, raise error with helpful message
        raise FileNotFoundError(
            f"No Mogger configuration file found in {cwd}. "
            f"Please create one of the following files: {', '.join(config_names[:3])} "
            f"or provide a config_path explicitly."
        )

    def __load_config(self) -> None:
        """Load and validate YAML configuration."""
        if not self.__config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.__config_path}")

        try:
            with open(self.__config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            self.__config = MoggerConfig(**config_data)
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")

    def __print_to_terminal(self, level: str, category: str, log_uuid: str, message: str, **kwargs) -> None:
        """Print log to terminal with formatting and colors."""
        if not self.__config.terminal.enabled:
            return

        timestamp = datetime.now().strftime(self.__config.terminal.timestamp_format)

        # Build message
        formatted_msg = self.__config.terminal.format.format(
            timestamp=timestamp,
            level=level,
            table=category,
            uuid=log_uuid if self.__config.terminal.show_uuid else "",
            message=message
        )

        # Add extra fields if any
        if kwargs:
            extra_fields = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            formatted_msg += f" | {extra_fields}"

        # Get color for level
        color = getattr(self.__config.terminal.colors, level, "white")
        
        # Print with color using rich
        self.__console.print(formatted_msg, style=color)
    
    def __insert_log(self, level: str, category: str, **kwargs) -> str:
        """
        Insert a log entry into the database.

        Returns:
            UUID of the created log entry
        """
        # Generate UUID and timestamp
        log_uuid = str(uuid_lib.uuid4())
        created_at = datetime.now()
        
        # Use database manager to insert log
        self.__db_manager.insert_log(
            log_uuid=log_uuid,
            level=level,
            table=category,
            created_at=created_at,
            context_data=self.__context_data,
            **kwargs
        )

        return log_uuid

    def log(self, level: str, message: str, category: str, **kwargs) -> str:
        """
        Log a message with custom level.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            category: Target category/table name
            **kwargs: Additional fields matching table schema

        Returns:
            UUID of the log entry
        """
        # Insert into database
        log_uuid = self.__insert_log(level, category, **kwargs)

        # Print to terminal
        self.__print_to_terminal(level, category, log_uuid, message, **kwargs)
        
        # Send to Loki if configured
        if self.__loki_logger is not None:
            extra_data = {
                "category": category,
                "uuid": log_uuid,
                **self.__context_data,
                **kwargs
            }
            
            level_lower = level.lower()
            if level_lower == "debug":
                self.__loki_logger.debug(message, extra=extra_data)
            elif level_lower == "info":
                self.__loki_logger.info(message, extra=extra_data)
            elif level_lower == "warning":
                self.__loki_logger.warning(message, extra=extra_data)
            elif level_lower == "error":
                self.__loki_logger.error(message, extra=extra_data)
            elif level_lower == "critical":
                self.__loki_logger.critical(message, extra=extra_data)

        return log_uuid

    def debug(self, message: str, category: str, **kwargs) -> str:
        """Log a DEBUG message."""
        return self.log(self.DEBUG, message, category, **kwargs)

    def info(self, message: str, category: str, **kwargs) -> str:
        """Log an INFO message."""
        return self.log(self.INFO, message, category, **kwargs)

    def warning(self, message: str, category: str, **kwargs) -> str:
        """Log a WARNING message."""
        return self.log(self.WARNING, message, category, **kwargs)

    def error(self, message: str, category: str, **kwargs) -> str:
        """Log an ERROR message."""
        return self.log(self.ERROR, message, category, **kwargs)

    def critical(self, message: str, category: str, **kwargs) -> str:
        """Log a CRITICAL message."""
        return self.log(self.CRITICAL, message, category, **kwargs)

    def set_terminal(self, enabled: bool) -> None:
        """Enable or disable terminal output."""
        self.__config.terminal.enabled = enabled

    def set_context(self, **kwargs) -> None:
        """Set context data to be included in all subsequent logs."""
        self.__context_data.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context data."""
        self.__context_data.clear()

    def query(self, category: str, limit: Optional[int] = None, **filters) -> List[Dict[str, Any]]:
        """
        Query logs from a specific category.

        Args:
            category: Category name to query
            limit: Maximum number of results
            **filters: Field filters (e.g., log_level="ERROR")

        Returns:
            List of log entries as dictionaries
        """
        return self.__db_manager.query(table=category, limit=limit, **filters)

    def get_tables(self) -> List[str]:
        """Get list of all available log tables."""
        return self.__db_manager.get_tables()

    def close(self) -> None:
        """Close database connections."""
        if self.__db_manager:
            self.__db_manager.close()
