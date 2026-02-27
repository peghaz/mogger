"""
Mogger - A custom logging library with CSV persistence and terminal output.
"""

import uuid as uuid_lib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import ValidationError
from rich.console import Console

from .csv_writer import CSVWriter
from .models import MoggerConfig, FieldValidationError
from .loki import LokiConfig, LokiLogger


class Mogger:
    """
    Custom logger with CSV persistence and configurable terminal output.

    Features:
    - YAML-driven schema configuration
    - CSV file persistence
    - Colored terminal output
    - UUID tracking for all logs
    - Multiple log tables with custom fields
    - Strict field validation
    """

    # Log level constants
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        loki_config: Optional[LokiConfig] = None,
        log_to_csv: bool = True
    ):
        """
        Initialize Mogger with configuration file.

        Args:
            config_path: Path to YAML configuration file. If not provided, will search for
                        'mogger_config.yaml', 'mogger.config.yaml', or '.mogger.yaml' 
                        in the current working directory.
            loki_config: Optional LokiConfig for sending logs to Loki server
            log_to_csv: Whether to write logs to CSV files (default: True)
        """
        self.__config_path = self.__find_config_file(config_path)
        self.__config: Optional[MoggerConfig] = None
        self.__csv_writer: Optional[CSVWriter] = None
        self.__context_data: Dict[str, Any] = {}
        self.__console = Console()  # Rich console for colored output
        self.__loki_logger: Optional[LokiLogger] = None
        self.__log_to_csv = log_to_csv

        # Load and validate configuration
        self.__load_config()
        
        # Build allowed fields map for validation
        self.__allowed_fields: Dict[str, set] = {}
        for table in self.__config.tables:
            self.__allowed_fields[table.name] = {field.name for field in table.fields}

        # Initialize CSV writer if enabled
        if self.__log_to_csv:
            self.__csv_writer = CSVWriter(self.__config)

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

    def __validate_fields(self, category: str, kwargs: Dict[str, Any]) -> None:
        """
        Validate that all provided fields are defined in the table config.
        
        Args:
            category: Table/category name
            kwargs: Fields to validate
            
        Raises:
            FieldValidationError: If any field is not defined in config
        """
        if category not in self.__allowed_fields:
            raise FieldValidationError(f"Unknown category: {category}")
        
        allowed = self.__allowed_fields[category]
        provided = set(kwargs.keys())
        invalid = provided - allowed
        
        if invalid:
            raise FieldValidationError(
                f"Invalid fields for category '{category}': {', '.join(sorted(invalid))}. "
                f"Allowed fields are: {', '.join(sorted(allowed))}"
            )

    def __print_to_terminal(self, level: str, log_uuid: str, message: str, **kwargs) -> None:
        """Print log to terminal with formatting and colors."""
        if not self.__config.terminal.enabled:
            return

        timestamp = datetime.now().strftime(self.__config.terminal.timestamp_format)

        # Build message - use 'table' placeholder for backward compatibility
        formatted_msg = self.__config.terminal.format.format(
            timestamp=timestamp,
            level=level.center(8),
            table=kwargs.get("category", ""),
            uuid=log_uuid if self.__config.terminal.show_uuid else "",
            message=message
        )

        # Get color for level
        color = getattr(self.__config.terminal.colors, level, "white")

        # Print with color using rich
        self.__console.print(formatted_msg, style=color)

    def __write_log(self, level: str, category: str, message: str, log_to_csv: bool = True, **kwargs) -> str:
        """
        Write a log entry to CSV.

        Args:
            level: Log level
            category: Log category/table
            message: Log message
            log_to_csv: Whether to write to CSV
            **kwargs: Additional fields

        Returns:
            UUID of the created log entry
        """
        # Generate UUID and timestamp
        log_uuid = str(uuid_lib.uuid4())
        created_at = datetime.now()

        # Write to CSV if enabled
        if log_to_csv and self.__log_to_csv and self.__csv_writer is not None:
            self.__csv_writer.write_log(
                table_name=category,
                log_id=log_uuid,
                timestamp=created_at,
                level=level,
                message=message,
                **kwargs
            )

        return log_uuid

    def log(self, level: str, message: str, category: str, log_to_csv: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """
        Log a message with custom level.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            category: Target category/table name
            log_to_csv: Whether to write to CSV file (default: True)
            log_to_shell: Whether to log to terminal/shell (default: True)
            **kwargs: Additional fields matching table schema

        Returns:
            UUID of the log entry
        """
        # Merge context data with kwargs
        merged_kwargs = {**self.__context_data, **kwargs}
        
        # Validate fields if CSV logging is enabled
        if log_to_csv and self.__log_to_csv:
            self.__validate_fields(category, merged_kwargs)
        
        # Write to CSV
        log_uuid = self.__write_log(level, category, message, log_to_csv=log_to_csv, **merged_kwargs)

        # Print to terminal
        if log_to_shell:
            self.__print_to_terminal(level, log_uuid, message, category=category, **merged_kwargs)

        # Send to Loki if configured
        if self.__loki_logger is not None:
            extra_data = {
                "category": category,
                "uuid": log_uuid,
                **merged_kwargs
            }

            log_message = self.__make_total_loki_data(message, extra_data)

            level_lower = level.lower()
            if level_lower == "debug":
                self.__loki_logger.debug(log_message, extra={})
            elif level_lower == "info":
                self.__loki_logger.info(log_message, extra={})
            elif level_lower == "warning":
                self.__loki_logger.warning(log_message, extra={})
            elif level_lower == "error":
                self.__loki_logger.error(log_message, extra={})
            elif level_lower == "critical":
                self.__loki_logger.critical(log_message, extra={})

        return log_uuid

    def __make_total_loki_data(self, message: str, extra_data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to prepare data for Loki logging."""
        return {
            "message": message,
            **extra_data
        }

    def debug(self, message: str, category: str, log_to_csv: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """Log a DEBUG message."""
        return self.log(self.DEBUG, message, category, log_to_csv=log_to_csv, log_to_shell=log_to_shell, **kwargs)

    def info(self, message: str, category: str, log_to_csv: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """Log an INFO message."""
        return self.log(self.INFO, message, category, log_to_csv=log_to_csv, log_to_shell=log_to_shell, **kwargs)

    def warning(self, message: str, category: str, log_to_csv: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """Log a WARNING message."""
        return self.log(self.WARNING, message, category, log_to_csv=log_to_csv, log_to_shell=log_to_shell, **kwargs)

    def error(self, message: str, category: str, log_to_csv: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """Log an ERROR message."""
        return self.log(self.ERROR, message, category, log_to_csv=log_to_csv, log_to_shell=log_to_shell, **kwargs)

    def critical(self, message: str, category: str, log_to_csv: bool = True, log_to_shell: bool = True, **kwargs) -> str:
        """Log a CRITICAL message."""
        return self.log(self.CRITICAL, message, category, log_to_csv=log_to_csv, log_to_shell=log_to_shell, **kwargs)

    def set_terminal(self, enabled: bool) -> None:
        """Enable or disable terminal output."""
        self.__config.terminal.enabled = enabled

    def set_context(self, **kwargs) -> None:
        """Set context data to be included in all subsequent logs."""
        self.__context_data.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context data."""
        self.__context_data.clear()

    def get_tables(self) -> List[str]:
        """Get list of all available log tables."""
        return [table.name for table in self.__config.tables]

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
