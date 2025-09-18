# Tests Directory

This directory contains unit tests for the MCP Sales Server.

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_server.py

# Run with coverage
python -m pytest tests/ --cov=.
```

## Test Structure

- `conftest.py` - Pytest configuration and fixtures
- `test_config.py` - Configuration system tests  
- `test_server.py` - MCP server functionality tests
- `test_tools/` - Individual tool tests

## Adding New Tests

1. Create test files following the `test_*.py` pattern
2. Use existing fixtures from `conftest.py`
3. Follow the existing test patterns for consistency

For integration testing, see the main README.md for verification scripts.
