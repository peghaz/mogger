# Mogger

A custom logging library with SQLite persistence and colored terminal output.

## Features

- **YAML-driven schema configuration** - Define your log tables and fields in a YAML file
- **SQLite database with relational design** - All logs stored in a persistent database
- **Colored terminal output** - Beautiful colored logs using Rich library
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

### Disable Terminal Output

```python
logger.set_terminal(False)  # Logs only to database
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
