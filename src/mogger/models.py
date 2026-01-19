# Pydantic models for config validation
from pydantic import BaseModel, Field, ValidationError
from typing import Any, Dict, List, Optional, Union


class FieldConfig(BaseModel):
    name: str
    type: str
    indexed: bool = False
    nullable: bool = False


class TableConfig(BaseModel):
    name: str
    fields: List[FieldConfig]


class DatabaseConfig(BaseModel):
    path: str
    wal_mode: bool = True


class TerminalColorsConfig(BaseModel):
    DEBUG: str = "cyan"
    INFO: str = "green"
    WARNING: str = "yellow"
    ERROR: str = "red"
    CRITICAL: str = "magenta"


class TerminalConfig(BaseModel):
    enabled: bool = True
    format: str = "{timestamp} [{level}] [{table}] {message}"
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"
    colors: TerminalColorsConfig = Field(default_factory=TerminalColorsConfig)
    show_uuid: bool = False


class MoggerConfig(BaseModel):
    database: DatabaseConfig
    tables: List[TableConfig]
    terminal: TerminalConfig = Field(default_factory=TerminalConfig)
