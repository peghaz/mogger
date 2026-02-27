# Pydantic models for config validation
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional, Union


# Allowed field types for strict validation
ALLOWED_FIELD_TYPES = {"str", "int", "float", "bool", "json", "text"}


class FieldValidationError(Exception):
    """Raised when a field validation fails."""
    pass


class FieldConfig(BaseModel):
    """
    Represents the configuration for a field in a data model.

    Attributes:
        name (str): The name of the field.
        type (str): The data type of the field.
        indexed (bool): Indicates whether the field is indexed. Defaults to False.
        nullable (bool): Indicates whether the field can be null. Defaults to False.
    """
    name: str
    type: str
    indexed: bool = False
    nullable: bool = False

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that field type is one of the allowed types."""
        if v not in ALLOWED_FIELD_TYPES:
            raise ValueError(
                f"Invalid field type '{v}'. Allowed types are: {', '.join(sorted(ALLOWED_FIELD_TYPES))}"
            )
        return v


class TableConfig(BaseModel):
    """
    Represents the configuration for a table.

    Attributes:
        name (str): The name of the table.
        fields (List[FieldConfig]): A list of field configurations for the table.
    """
    name: str
    fields: List[FieldConfig]


class DirectoryConfig(BaseModel):
    """Configuration for the logs directory."""
    path: str = ".mogger.logs"


class TerminalColorsConfig(BaseModel):
    """
    Configuration model for terminal colors.

    This class defines the default color codes for different logging levels
    used in terminal output. Each attribute represents a logging level and
    its associated color.

    Attributes:
        DEBUG (str): Color for debug messages. Default is "cyan".
        INFO (str): Color for informational messages. Default is "green".
        WARNING (str): Color for warning messages. Default is "yellow".
        ERROR (str): Color for error messages. Default is "red".
        CRITICAL (str): Color for critical messages. Default is "magenta".
    """
    DEBUG: str = "cyan"
    INFO: str = "green"
    WARNING: str = "yellow"
    ERROR: str = "red"
    CRITICAL: str = "magenta"


class TerminalConfig(BaseModel):
    enabled: bool = True
    format: str = "{timestamp} [{level}] {message}"
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"
    colors: TerminalColorsConfig = Field(default_factory=TerminalColorsConfig)
    show_uuid: bool = False


class MoggerConfig(BaseModel):
    directory: DirectoryConfig = Field(default_factory=DirectoryConfig)
    tables: List[TableConfig]
    terminal: TerminalConfig = Field(default_factory=TerminalConfig)
