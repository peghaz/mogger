# Mogger

A custom logging library with SQLite persistence, colored terminal output, and Loki integration.

## Features

- **YAML-driven schema configuration** - Define your log tables and fields in a YAML file
- **SQLite database with relational design** - All logs stored in a persistent database
- **Colored terminal output** - Beautiful colored logs using Rich library
- **Loki integration** - Send logs to Grafana Loki for centralized logging
- **Flexible logging control** - Enable/disable database and terminal output per log
- **UUID tracking** - Every log entry has a unique identifier
- **Multiple log tables** - Create custom tables for different types of logs
- **Context management** - Add context data to all logs in a scope
- **Query API** - Retrieve and analyze logs from the database
- **Automatic config detection** - No need to specify config path if file is in project root

## Installation

```bash
pip install mogger
```

## Quick Start

### 1. Create a configuration file

Create `mogger_config.yaml` in your project root:

```yaml
database:
  path: "./logs.db"
  wal_mode: true

tables:
  - name: "user_actions"
    fields:
      - name: "user_id"
        type: "string"
        indexed: true
      - name: "action"
        type: "string"

terminal:
  enabled: true
  colors:
    INFO: "green"
    ERROR: "red"
    WARNING: "yellow"
```

### 2. Use Mogger in your code

```python
from mogger import Mogger

# Automatic config detection - looks for mogger_config.yaml in current directory
logger = Mogger()

# Or specify config explicitly
# logger = Mogger("path/to/config.yaml")

# Log messages
logger.info("User logged in", category="user_actions", user_id="123", action="login")
logger.error("Something failed", category="errors", error_code=500, error_message="Server error")

# Query logs
recent_errors = logger.query(category="errors", limit=10)
user_logs = logger.query(category="user_actions", user_id="123")

# Close when done
logger.close()
```

## Initialization Options

### Basic Initialization

```python
from mogger import Mogger

# Default: local database and terminal output enabled
logger = Mogger("mogger_config.yaml")

# Disable local database (Loki-only or terminal-only logging)
logger = Mogger("mogger_config.yaml", use_local_db=False)

# Custom database path
logger = Mogger("mogger_config.yaml", db_path="./custom_logs.db")
```

### Loki Integration

```python
from mogger import Mogger, LokiConfig

# Configure Loki
loki_config = LokiConfig(
    url="http://localhost:3100/loki/api/v1/push",
    tags={"application": "my-app", "environment": "production"},
    username="loki",  # Optional
    password="password"  # Optional
)

# Initialize with Loki support
logger = Mogger("mogger_config.yaml", loki_config=loki_config)

# Loki-only logging (no local database)
logger = Mogger("mogger_config.yaml", loki_config=loki_config, use_local_db=False)
```

### Generate Loki Deployment Configuration

Mogger can generate a complete Docker Compose setup for Loki + Grafana + Alloy:

```python
from mogger import Mogger

logger = Mogger("mogger_config.yaml")

# Generate Loki config in current directory (creates 'loki-config' folder)
config_path = logger.generate_loki_config()

# Or specify custom location
config_path = logger.generate_loki_config(destination="./my-monitoring")

# Deploy the stack
# cd loki-config
# docker-compose up -d
# Access Grafana at http://localhost:3000
```

The generated configuration includes:
- Loki for log aggregation
- Grafana for visualization
- Alloy for log collection
- Pre-configured dashboards
- Docker Compose setup for easy deployment

## Logging Control Parameters

All logging methods (`debug`, `info`, `warning`, `error`, `critical`) support these parameters:

### `use_local_db` (default: `True`)

Control whether logs are written to the local SQLite database.

```python
# Skip database for this specific log
logger.info("Temporary message", category="user_actions", 
            user_id="123", action="click", use_local_db=False)

# Log only to Loki and terminal, not database
logger.error("Remote error", category="errors", 
             error_code=500, use_local_db=False)
```

### `log_to_shell` (default: `True`)

Control whether logs are printed to the terminal.

```python
# Silent logging (database and Loki only)
logger.info("Background task", category="system_events", 
            event_type="cron", log_to_shell=False)

# Quiet error logging
logger.error("Internal error", category="errors", 
             error_code=500, log_to_shell=False)
```

### Combining Parameters

```python
# Terminal only (no database, no Loki)
logger.info("Debug info", category="user_actions", 
            user_id="123", use_local_db=False, log_to_shell=True)

# Completely silent (Loki only if configured)
logger.info("Silent audit", category="audit", 
            action="access", use_local_db=False, log_to_shell=False)

# Database only (silent logging)
logger.info("Background event", category="system_events", 
            event_type="backup", log_to_shell=False)
```

## Configuration

### Config File Naming

Mogger automatically searches for these config files in your project root:
- `mogger_config.yaml` (recommended)
- `mogger.config.yaml`
- `.mogger.yaml`
- `mogger_config.yml`
- `mogger.config.yml`
- `.mogger.yml`

### Supported Field Types

- `string` - Variable-length string
- `text` - Long text
- `integer` - Integer number
- `float` - Floating point number
- `boolean` - True/False
- `json` - JSON data (automatically serialized/deserialized)
- `datetime` - Date and time

### Terminal Colors

Available colors: `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`

## Advanced Usage

### Context Management

```python
# Set context that applies to all subsequent logs
logger.set_context(request_id="req_123", user_id="user_456")

logger.info("Action 1", category="user_actions", action="click")
logger.info("Action 2", category="user_actions", action="scroll")

# Clear context
logger.clear_context()
```

### Disable Terminal Output Globally

```python
logger.set_terminal(False)  # Logs only to database (and Loki if configured)
```

### Query Logs

```python
# Get all logs from a table
all_logs = logger.query(category="user_actions")

# Filter logs
errors = logger.query(category="logs_master", log_level="ERROR")
user_errors = logger.query(category="errors", user_id="123")

# Limit results
recent = logger.query(category="user_actions", limit=50)
```

### Advanced Search

#### Query Latest Logs

```python
# Get the 10 most recent logs
latest = logger.get_latest_logs("logs_master", limit=10)

# Get latest logs with filters
latest_errors = logger.get_latest_logs("logs_master", limit=5, log_level="ERROR")
latest_user_actions = logger.get_latest_logs("user_actions", limit=20, user_id="123")
```

#### Query Oldest Logs

```python
# Get the 10 oldest logs
oldest = logger.get_oldest_logs("logs_master", limit=10)

# Get oldest logs with filters
first_errors = logger.get_oldest_logs("errors", limit=5, severity="critical")
```

#### Query by Time Range

```python
from datetime import datetime, timedelta

# Get logs from the last hour
end_time = datetime.now()
start_time = end_time - timedelta(hours=1)
recent_logs = logger.get_logs_between(
    "logs_master", 
    start_time, 
    end_time
)

# Get logs from specific time range with filters
errors_in_range = logger.get_logs_between(
    "logs_master",
    start_time,
    end_time,
    limit=100,
    log_level="ERROR"
)

# Query custom table in time range
user_actions = logger.get_logs_between(
    "user_actions",
    start_time,
    end_time,
    user_id="123"
)
```

#### Search by Keyword

```python
# Search for logs containing a keyword in any text field
results = logger.search_logs("errors", "database")

# Search in specific fields
results = logger.search_logs(
    "errors", 
    "connection", 
    fields=["error_message"]
)

# Search with additional filters
results = logger.search_logs(
    "errors",
    "timeout",
    fields=["error_message", "error_details"],
    severity="high",
    limit=50
)

# Search is case-insensitive and matches partial strings
results = logger.search_logs("user_actions", "admin")  # Matches "admin", "Admin", "administrator"
```

**Note:** All advanced search methods require `use_local_db=True` (default) at initialization.

## Use Cases

### Scenario 1: Production with Loki + Local Database

```python
from mogger import Mogger, LokiConfig

loki_config = LokiConfig(
    url="https://loki.example.com/loki/api/v1/push",
    tags={"application": "web-api", "environment": "production"}
)

logger = Mogger("mogger_config.yaml", loki_config=loki_config)

# All logs go to local DB, Loki, and terminal
logger.info("Request processed", category="api_requests", 
            endpoint="/api/users", response_time=0.15)
```

### Scenario 2: Development with Terminal Only

```python
# No database, just terminal output
logger = Mogger("mogger_config.yaml", use_local_db=False)

logger.info("Debug message", category="user_actions", 
            user_id="dev", action="test")
```

### Scenario 3: Loki-Only Logging (No Local Storage)

```python
from mogger import Mogger, LokiConfig

loki_config = LokiConfig(
    url="http://localhost:3100/loki/api/v1/push",
    tags={"application": "microservice"}
)

logger = Mogger("mogger_config.yaml", loki_config=loki_config, use_local_db=False)

# All logs go only to Loki
logger.info("Service started", category="system_events", 
            event_type="startup")
```

### Scenario 4: Mixed Logging Patterns

```python
logger = Mogger("mogger_config.yaml", loki_config=loki_config)

# Important logs: all destinations
logger.error("Critical failure", category="errors", 
             error_code=500, severity="critical")

# Debug logs: terminal only
logger.debug("Variable value", category="debug", 
             value=42, use_local_db=False)

# Audit logs: database and Loki only (silent)
logger.info("User action", category="audit", 
            user_id="123", action="delete", log_to_shell=False)

# Temporary logs: terminal only (not persisted)
logger.info("Processing...", category="status", 
            progress=50, use_local_db=False)
```

## Development

### Running Tests

```bash
pytest tests/
```

### Building

```bash
python -m build
```

## License

MIT