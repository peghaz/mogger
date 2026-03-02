# Mogger

A custom logging library with CSV persistence, colored terminal output, and Loki integration.

## Features

- **YAML-driven schema configuration** - Define your log tables and fields in a simple YAML file
- **CSV file persistence** - Logs stored in human-readable CSV files (one per table)
- **Strict field validation** - Only fields defined in your schema are allowed
- **Colored terminal output** - Beautiful colored logs using Rich library
- **Loki integration** - Send logs to Grafana Loki for centralized logging
- **Flexible logging control** - Enable/disable CSV and terminal output per log
- **UUID tracking** - Every log entry has a unique identifier
- **Multiple log tables** - Create custom tables for different types of logs
- **Context management** - Add context data to all logs in a scope
- **Thread-safe** - Safe for concurrent logging from multiple threads
- **Automatic config detection** - No need to specify config path if file is in project root

## Installation

```bash
pip install mogger
```

## Quick Start

### 1. Create a configuration file

Create `mogger.config.yaml` in your project root:

```yaml
directory:
  path: "./.mogger.logs"

tables:
  - name: "user_actions"
    fields:
      - name: "user_id"
        type: "str"
        indexed: true
      - name: "action"
        type: "str"

  - name: "errors"
    fields:
      - name: "error_code"
        type: "int"
      - name: "error_message"
        type: "text"
      - name: "severity"
        type: "str"

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

# Automatic config detection - looks for mogger.config.yaml in current directory
logger = Mogger()

# Or specify config explicitly
# logger = Mogger("path/to/config.yaml")

# Log messages
logger.info("User logged in", category="user_actions", user_id="123", action="login")
logger.error("Something failed", category="errors", error_code=500, error_message="Server error", severity="high")

# Logs are written to:
# .mogger.logs/user_actions.logs.csv
# .mogger.logs/errors.logs.csv
```

## Initialization Options

### Basic Initialization

```python
from mogger import Mogger

# Default: CSV logging and terminal output enabled
logger = Mogger("mogger.config.yaml")

# Disable CSV logging (Loki-only or terminal-only logging)
logger = Mogger("mogger.config.yaml", log_to_csv=False)
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
logger = Mogger("mogger.config.yaml", loki_config=loki_config)

# Loki-only logging (no local CSV files)
logger = Mogger("mogger.config.yaml", loki_config=loki_config, log_to_csv=False)
```

### Generate Loki Deployment Configuration

Mogger can generate a complete Docker Compose setup for Loki + Grafana + Alloy:

```python
from mogger import Mogger

logger = Mogger("mogger.config.yaml")

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

### `log_to_csv` (default: `True`)

Control whether logs are written to CSV files.

```python
# Skip CSV for this specific log (useful for context fields not in schema)
logger.info("Temporary message", category="user_actions", 
            user_id="123", action="click", log_to_csv=False)

# Log only to Loki and terminal, not CSV
logger.error("Remote error", category="errors", 
             error_code=500, error_message="Error", severity="high", log_to_csv=False)
```

### `log_to_shell` (default: `True`)

Control whether logs are printed to the terminal.

```python
# Silent logging (CSV and Loki only)
logger.info("Background task", category="system_events", 
            event_type="cron", description="Running backup", log_to_shell=False)

# Quiet error logging
logger.error("Internal error", category="errors", 
             error_code=500, error_message="Error", severity="high", log_to_shell=False)
```

### Combining Parameters

```python
# Terminal only (no CSV, no Loki)
logger.info("Debug info", category="user_actions", 
            user_id="123", action="test", log_to_csv=False, log_to_shell=True)

# Completely silent (Loki only if configured)
logger.info("Silent audit", category="user_actions", 
            user_id="123", action="access", log_to_csv=False, log_to_shell=False)

# CSV only (silent logging)
logger.info("Background event", category="system_events", 
            event_type="backup", description="Backup started", log_to_shell=False)
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

| Type | Description |
|------|-------------|
| `str` | Variable-length string |
| `text` | Long text content |
| `int` | Integer number |
| `float` | Floating point number |
| `bool` | Boolean (True/False) |
| `json` | JSON data (automatically serialized) |

### Terminal Colors

Available colors: `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`

### Complete Configuration Example

```yaml
# Directory where CSV log files will be stored
directory:
  path: "./.mogger.logs"

# Define custom log tables with their fields
tables:
  - name: "user_actions"
    fields:
      - name: "user_id"
        type: "str"
        indexed: true
      - name: "action"
        type: "str"
      - name: "ip_address"
        type: "str"
        nullable: true
      - name: "metadata"
        type: "json"
        nullable: true

  - name: "errors"
    fields:
      - name: "error_code"
        type: "int"
      - name: "error_message"
        type: "text"
      - name: "stack_trace"
        type: "text"
        nullable: true
      - name: "severity"
        type: "str"

  - name: "system_events"
    fields:
      - name: "event_type"
        type: "str"
        indexed: true
      - name: "description"
        type: "text"
      - name: "duration_ms"
        type: "float"
        nullable: true

  - name: "api_requests"
    fields:
      - name: "endpoint"
        type: "str"
      - name: "method"
        type: "str"
      - name: "status_code"
        type: "int"
      - name: "response_time_ms"
        type: "float"
      - name: "request_body"
        type: "json"
        nullable: true
      - name: "response_body"
        type: "json"
        nullable: true

# Terminal output settings
terminal:
  enabled: true
  format: "{timestamp} [{level}] {message}"
  timestamp_format: "%Y-%m-%d %H:%M:%S"
  show_uuid: false
  colors:
    DEBUG: "cyan"
    INFO: "green"
    WARNING: "yellow"
    ERROR: "red"
    CRITICAL: "magenta"
```

## Strict Field Validation

Mogger enforces strict field validation. Only fields defined in your YAML schema are allowed:

```python
from mogger import Mogger, FieldValidationError

logger = Mogger("mogger.config.yaml")

# This works - all fields are defined in schema
logger.info("Login", category="user_actions", user_id="123", action="login")

# This raises FieldValidationError - 'unknown_field' is not in schema
try:
    logger.info("Login", category="user_actions", user_id="123", action="login", unknown_field="value")
except FieldValidationError as e:
    print(e)  # Invalid fields for category 'user_actions': unknown_field. Allowed fields are: action, ip_address, metadata, user_id

# This raises FieldValidationError - category doesn't exist
try:
    logger.info("Message", category="nonexistent_table", some_field="value")
except FieldValidationError as e:
    print(e)  # Unknown category: nonexistent_table
```

### Bypassing Validation with `log_to_csv=False`

When you need to log fields not in your schema (e.g., context data), use `log_to_csv=False`:

```python
# Context fields are not in schema, so disable CSV logging for this call
logger.set_context(request_id="req-123", session_id="sess-456")
logger.info("Action with context", category="user_actions", 
            user_id="123", action="view", log_to_csv=False)
logger.clear_context()
```

## Advanced Usage

### Context Management

Add context data that applies to all subsequent logs:

```python
# Set context that applies to all subsequent logs
logger.set_context(request_id="req_123", user_id="user_456")

# These logs will include context data (sent to Loki, not CSV)
# Use log_to_csv=False since context fields aren't in schema
logger.info("Action 1", category="user_actions", action="click", log_to_csv=False)
logger.info("Action 2", category="user_actions", action="scroll", log_to_csv=False)

# Clear context
logger.clear_context()
```

### Disable Terminal Output Globally

```python
logger.set_terminal(False)  # Logs only to CSV (and Loki if configured)
logger.set_terminal(True)   # Re-enable terminal output
```

### Get Available Tables

```python
tables = logger.get_tables()
print(tables)  # ['user_actions', 'errors', 'system_events', 'api_requests']
```

## CSV File Structure

Logs are stored in CSV files under the configured directory (default: `.mogger.logs/`):

```
.mogger.logs/
├── user_actions.logs.csv
├── errors.logs.csv
├── system_events.logs.csv
└── api_requests.logs.csv
```

Each CSV file contains:
- `uuid` - Unique identifier for the log entry
- `created_at` - Timestamp when the log was created
- `log_level` - DEBUG, INFO, WARNING, ERROR, or CRITICAL
- `message` - The log message
- All custom fields defined in your schema

Example `user_actions.logs.csv`:
```csv
uuid,created_at,log_level,message,user_id,action,ip_address,metadata
a1b2c3d4-...,2026-02-27 10:30:15,INFO,User logged in,user_123,login,192.168.1.1,
e5f6g7h8-...,2026-02-27 10:30:20,INFO,User clicked button,user_123,click,,{"button": "submit"}
```

## Use Cases

### Scenario 1: Production with Loki + Local CSV

```python
from mogger import Mogger, LokiConfig

loki_config = LokiConfig(
    url="https://loki.example.com/loki/api/v1/push",
    tags={"application": "web-api", "environment": "production"}
)

logger = Mogger("mogger.config.yaml", loki_config=loki_config)

# All logs go to local CSV, Loki, and terminal
logger.info("Request processed", category="api_requests", 
            endpoint="/api/users", method="GET", status_code=200, response_time_ms=0.15)
```

### Scenario 2: Development with Terminal Only

```python
# No CSV files, just terminal output for quick debugging
logger = Mogger("mogger.config.yaml", log_to_csv=False)

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

logger = Mogger("mogger.config.yaml", loki_config=loki_config, log_to_csv=False)

# All logs go only to Loki
logger.info("Service started", category="system_events", 
            event_type="startup", description="Service initialized")
```

### Scenario 4: Mixed Logging Patterns

```python
logger = Mogger("mogger.config.yaml", loki_config=loki_config)

# Important logs: all destinations
logger.error("Critical failure", category="errors", 
             error_code=500, error_message="Database connection failed", severity="critical")

# Debug logs: terminal only (not persisted)
logger.debug("Variable value", category="system_events", 
             event_type="debug", description="x=42", log_to_csv=False)

# Audit logs: CSV and Loki only (silent)
logger.info("User action", category="user_actions", 
            user_id="123", action="delete", log_to_shell=False)

# Context-aware logs: Loki and terminal only (context fields not in schema)
logger.set_context(trace_id="abc-123")
logger.info("Traced action", category="user_actions", 
            user_id="123", action="view", log_to_csv=False)
logger.clear_context()
```

### Scenario 5: API Request Logging

```python
import time

logger = Mogger("mogger.config.yaml")

# Log incoming request
start_time = time.time()

# ... process request ...

# Log completed request
elapsed_ms = (time.time() - start_time) * 1000
logger.info(
    "API request completed",
    category="api_requests",
    endpoint="/api/users/123",
    method="GET",
    status_code=200,
    response_time_ms=elapsed_ms,
    request_body=None,
    response_body={"id": 123, "name": "John"}
)
```

## Error Handling

```python
from mogger import Mogger, FieldValidationError

logger = Mogger("mogger.config.yaml")

try:
    # Attempt to log with invalid fields
    logger.info("Test", category="user_actions", invalid_field="value")
except FieldValidationError as e:
    print(f"Validation error: {e}")
    # Handle gracefully - maybe log without the invalid field
    logger.info("Test", category="user_actions", user_id="123", action="fallback")
```

## Thread Safety

Mogger is thread-safe and can be used from multiple threads simultaneously:

```python
import threading
from mogger import Mogger

logger = Mogger("mogger.config.yaml")

def worker(worker_id):
    for i in range(100):
        logger.info(f"Log from worker {worker_id}", 
                    category="system_events", 
                    event_type="worker", 
                    description=f"Task {i}")

# Create multiple threads
threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

# Start all threads
for t in threads:
    t.start()

# Wait for completion
for t in threads:
    t.join()
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

## Migration from v0.2.x (SQLite)

If you're migrating from the SQLite-based version:

| v0.2.x (SQLite) | v0.3.x (CSV) |
|-----------------|--------------|
| `database:` in YAML | `directory:` in YAML |
| `db_path` parameter | Removed (use `directory.path` in YAML) |
| `use_local_db` parameter | `log_to_csv` parameter |
| `logger.query(...)` | Removed (read CSV files directly) |
| `logger.get_latest_logs(...)` | Removed |
| `logger.get_oldest_logs(...)` | Removed |
| `logger.get_logs_between(...)` | Removed |
| `logger.search_logs(...)` | Removed |
| `logger.close()` | Removed (not needed) |
| Field types: `string`, `integer` | Field types: `str`, `int` |

### Config Migration Example

**Before (v0.2.x):**
```yaml
database:
  path: "./logs.db"
  wal_mode: true

tables:
  - name: "user_actions"
    fields:
      - name: "user_id"
        type: "string"
```

**After (v0.3.x):**
```yaml
directory:
  path: "./.mogger.logs"

tables:
  - name: "user_actions"
    fields:
      - name: "user_id"
        type: "str"
```

## License

MIT