# Mogger Tests

Comprehensive pytest test suite for the Mogger logging library.

## Test Structure

### `conftest.py`
Pytest configuration and fixtures:
- `test_config_path`: Path to test configuration
- `test_db_path`: Path to test database file
- `clean_test_db`: Fixture that cleans up test database before/after tests
- `logger`: Standard logger instance for testing
- `logger_with_terminal`: Logger with terminal output enabled

### Test Files

#### `test_initialization.py`
Tests for logger initialization and configuration:
- Logger initialization
- Database file creation
- Configuration validation
- Table discovery
- Terminal configuration

#### `test_logging.py`
Tests for logging operations:
- Basic logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Complex logging with various data types
- JSON field handling
- Error handling (missing fields, invalid tables)
- Bulk logging operations
- Mixed log levels

#### `test_querying.py`
Tests for querying logs from database:
- Basic queries (empty tables, master table, specific tables)
- Filtered queries (by log level, table name, custom fields)
- Query limits
- Complex queries with multiple filters
- Large result sets
- Indexed vs non-indexed field queries

#### `test_advanced.py`
Tests for advanced features:
- Context management (set, clear, update, persist)
- Logger state management
- Multiple logger instances
- Edge cases (empty strings, long text, special characters, Unicode)
- Zero and negative numbers
- Complex JSON structures
- Concurrent access scenarios

#### `test_integration.py`
Integration tests for complete workflows:
- User session workflow (login, actions, logout)
- API monitoring workflow
- Error tracking and debugging workflow
- Mixed logging with context
- Daily operations simulation
- Data integrity tests (UUID uniqueness, referential integrity, timestamps)

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run with verbose output:
```bash
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_logging.py -v
```

### Run specific test class:
```bash
pytest tests/test_logging.py::TestComplexLogging -v
```

### Run specific test:
```bash
pytest tests/test_logging.py::TestComplexLogging::test_json_field_logging -v
```

### Run with coverage:
```bash
pytest tests/ --cov=mogger --cov-report=html
```

### Run with output capture disabled (see print statements):
```bash
pytest tests/ -s
```

## Test Database

Tests use a separate database file: `mogger_test_logs.db`
- Created fresh for each test
- Automatically cleaned up after tests
- Located in project root directory

## Test Configuration

Tests use `tests/test_config.yaml` with:
- 4 tables: user_actions, errors, system_events, api_requests
- Terminal output disabled by default (to avoid cluttering test output)
- WAL mode enabled

## Coverage

The test suite covers:
- ✅ Initialization and configuration
- ✅ All log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ✅ All field types (string, text, integer, float, boolean, json, datetime)
- ✅ Required and nullable fields
- ✅ Indexed and non-indexed fields
- ✅ Query operations with filters
- ✅ Context management
- ✅ Error handling
- ✅ Edge cases and boundary conditions
- ✅ Data integrity
- ✅ Complete workflow scenarios

## Expected Results

All tests should pass with the test database created at:
`./mogger_test_logs.db`

Total test count: **60+ tests** across 5 test files
