"""
Mogger - A custom logging library with SQLite persistence and terminal output.
"""

import uuid as uuid_lib
import shutil
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

    def __init__(self, config_path: Optional[Union[str, Path]] = None, db_path: Optional[str] = None, loki_config: Optional[LokiConfig] = None, use_local_db: bool = True):
        """
        Initialize Mogger with configuration file.

        Args:
            config_path: Path to YAML configuration file. If not provided, will search for
                        'mogger_config.yaml', 'mogger.config.yaml', or '.mogger.yaml' 
                        in the current working directory.
            db_path: Optional override for database path
            loki_config: Optional LokiConfig for sending logs to Loki server
            use_local_db: Whether to initialize and use local database (default: True)
        """
        self.__config_path = self.__find_config_file(config_path)
        self.__config: Optional[MoggerConfig] = None
        self.__db_manager: Optional[DatabaseManager] = None
        self.__context_data: Dict[str, Any] = {}
        self.__console = Console()  # Rich console for colored output
        self.__loki_logger: Optional[LokiLogger] = None
        self.__use_local_db = use_local_db

        # Load and validate configuration
        self.__load_config()

        # Override db path if provided
        if db_path:
            self.__config.database.path = db_path

        # Initialize database manager only if use_local_db is True
        if self.__use_local_db:
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
    
    def __insert_log(self, level: str, category: str, use_local_db: bool = True, **kwargs) -> str:
        """
        Insert a log entry into the database.

        Args:
            level: Log level
            category: Log category/table
            use_local_db: Whether to insert into local database
            **kwargs: Additional fields

        Returns:
            UUID of the created log entry
        """
        # Generate UUID and timestamp
        log_uuid = str(uuid_lib.uuid4())
        created_at = datetime.now()
        
        # Use database manager to insert log only if enabled
        if use_local_db and self.__use_local_db and self.__db_manager is not None:
            self.__db_manager.insert_log(
                log_uuid=log_uuid,
                level=level,
                table=category,
                created_at=created_at,
                context_data=self.__context_data,
                **kwargs
            )

        return log_uuid

    def log(self, level: str, message: str, category: str, use_local_db: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """
        Log a message with custom level.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            category: Target category/table name
            use_local_db: Whether to log to local database (default: True)
            log_to_shell: Whether to log to terminal/shell (default: True)
            **kwargs: Additional fields matching table schema

        Returns:
            UUID of the log entry
        """
        # Insert into database
        log_uuid = self.__insert_log(level, category, use_local_db=use_local_db, **kwargs)

        # Print to terminal
        if log_to_shell:
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

    def debug(self, message: str, category: str, use_local_db: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """Log a DEBUG message."""
        return self.log(self.DEBUG, message, category, use_local_db=use_local_db, log_to_shell=log_to_shell, **kwargs)

    def info(self, message: str, category: str, use_local_db: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """Log an INFO message."""
        return self.log(self.INFO, message, category, use_local_db=use_local_db, log_to_shell=log_to_shell, **kwargs)

    def warning(self, message: str, category: str, use_local_db: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """Log a WARNING message."""
        return self.log(self.WARNING, message, category, use_local_db=use_local_db, log_to_shell=log_to_shell, **kwargs)

    def error(self, message: str, category: str, use_local_db: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """Log an ERROR message."""
        return self.log(self.ERROR, message, category, use_local_db=use_local_db, log_to_shell=log_to_shell, **kwargs)

    def critical(self, message: str, category: str, use_local_db: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """Log a CRITICAL message."""
        return self.log(self.CRITICAL, message, category, use_local_db=use_local_db, log_to_shell=log_to_shell, **kwargs)

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
        if not self.__use_local_db or self.__db_manager is None:
            raise RuntimeError("Local database is not enabled. Initialize Mogger with use_local_db=True")
        return self.__db_manager.query(table=category, limit=limit, **filters)
    
    def query_latest(self, category: str, limit: int = 10, **filters) -> List[Dict[str, Any]]:
        """
        Query the most recent logs from a specific category.
        
        Args:
            category: Category name to query (can be 'logs_master' or any configured table)
            limit: Maximum number of results (default: 10)
            **filters: Field filters (e.g., log_level="ERROR")
        
        Returns:
            List of log entries as dictionaries, ordered by most recent first
            
        Example:
            >>> logger.query_latest("user_actions", limit=5)
            >>> logger.query_latest("logs_master", limit=10, log_level="ERROR")
        """
        if not self.__use_local_db or self.__db_manager is None:
            raise RuntimeError("Local database is not enabled. Initialize Mogger with use_local_db=True")
        return self.__db_manager.query_latest(table=category, limit=limit, **filters)
    
    def query_oldest(self, category: str, limit: int = 10, **filters) -> List[Dict[str, Any]]:
        """
        Query the oldest logs from a specific category.
        
        Args:
            category: Category name to query (can be 'logs_master' or any configured table)
            limit: Maximum number of results (default: 10)
            **filters: Field filters (e.g., log_level="ERROR")
        
        Returns:
            List of log entries as dictionaries, ordered by oldest first
            
        Example:
            >>> logger.query_oldest("errors", limit=5)
            >>> logger.query_oldest("logs_master", limit=10, table_name="user_actions")
        """
        if not self.__use_local_db or self.__db_manager is None:
            raise RuntimeError("Local database is not enabled. Initialize Mogger with use_local_db=True")
        return self.__db_manager.query_oldest(table=category, limit=limit, **filters)
    
    def query_between_timestamps(self, category: str, start_time: datetime, 
                                 end_time: datetime, limit: Optional[int] = None,
                                 **filters) -> List[Dict[str, Any]]:
        """
        Query logs between two timestamps.
        
        Args:
            category: Category name to query (can be 'logs_master' or any configured table)
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            limit: Maximum number of results (optional)
            **filters: Field filters (e.g., log_level="ERROR")
        
        Returns:
            List of log entries as dictionaries, ordered by most recent first
            
        Example:
            >>> from datetime import datetime, timedelta
            >>> start = datetime.now() - timedelta(hours=1)
            >>> end = datetime.now()
            >>> logger.query_between_timestamps("user_actions", start, end)
            >>> logger.query_between_timestamps("logs_master", start, end, limit=50, log_level="WARNING")
        """
        if not self.__use_local_db or self.__db_manager is None:
            raise RuntimeError("Local database is not enabled. Initialize Mogger with use_local_db=True")
        return self.__db_manager.query_between_timestamps(
            table=category, start_time=start_time, end_time=end_time, 
            limit=limit, **filters
        )
    
    def search_keyword(self, category: str, keyword: str, fields: Optional[List[str]] = None,
                      limit: Optional[int] = None, **filters) -> List[Dict[str, Any]]:
        """
        Search for logs containing a keyword in specified fields.
        
        Args:
            category: Category name to query (cannot be 'logs_master')
            keyword: Keyword to search for (case-insensitive)
            fields: List of field names to search in. If None, searches all string/text fields
            limit: Maximum number of results (optional)
            **filters: Additional field filters (e.g., log_level="ERROR")
        
        Returns:
            List of log entries as dictionaries where at least one field contains the keyword
            
        Example:
            >>> logger.search_keyword("errors", "database", fields=["error_message"])
            >>> logger.search_keyword("user_actions", "login")
            >>> logger.search_keyword("system_events", "failure", limit=20)
        """
        if not self.__use_local_db or self.__db_manager is None:
            raise RuntimeError("Local database is not enabled. Initialize Mogger with use_local_db=True")
        return self.__db_manager.search_keyword(
            table=category, keyword=keyword, fields=fields, limit=limit, **filters
        )

    def get_tables(self) -> List[str]:
        """Get list of all available log tables."""
        return self.__db_manager.get_tables()

    def generate_loki_config(self, destination: Optional[Union[str, Path]] = None) -> Path:
        """
        Generate Loki configuration directory with Docker Compose setup.
        
        This creates a complete Loki + Grafana + Alloy setup that can be deployed
        using Docker Compose for centralized logging.
        
        Args:
            destination: Target directory path. If None, creates 'loki-config' in 
                        current working directory. Creates parent directories if needed.
        
        Returns:
            Path to the created configuration directory
            
        Raises:
            FileExistsError: If destination directory already exists
            RuntimeError: If copying configuration fails
            
        Example:
            >>> logger = Mogger("config.yaml")
            >>> config_path = logger.generate_loki_config()
            >>> print(f"Loki config created at: {config_path}")
            >>> # Deploy with: cd loki-config && docker-compose up -d
        """
        # Determine destination path
        if destination is None:
            dest_path = Path.cwd() / "loki-config"
        else:
            dest_path = Path(destination)
        
        # Check if destination already exists
        if dest_path.exists():
            raise FileExistsError(
                f"Directory already exists: {dest_path}\n"
                f"Please remove it first or choose a different destination."
            )
        
        # Get source loki_config directory from package
        source_path = Path(__file__).parent / "loki_config"
        
        if not source_path.exists():
            raise RuntimeError(
                f"Loki configuration template not found at: {source_path}\n"
                f"Please reinstall the package."
            )
        
        try:
            # Create destination directory and copy contents
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_path, dest_path)
            
            # Print success message
            self.__console.print(
                f"✅ Loki configuration created at: {dest_path}",
                style="green bold"
            )
            self.__console.print(
                f"\n📦 To deploy Loki + Grafana:",
                style="cyan"
            )
            self.__console.print(
                f"   cd {dest_path}\n"
                f"   docker-compose up -d",
                style="white"
            )
            self.__console.print(
                f"\n🌐 Access Grafana at: http://localhost:3000",
                style="cyan"
            )
            
            return dest_path
            
        except Exception as e:
            # Clean up partial copy if something went wrong
            if dest_path.exists():
                shutil.rmtree(dest_path)
            raise RuntimeError(f"Failed to generate Loki configuration: {e}")

    def close(self) -> None:
        """Close database connections."""
        if self.__db_manager:
            self.__db_manager.close()
