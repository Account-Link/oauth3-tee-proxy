# Testing Framework for OAuth3 TEE Proxy

This directory contains tests for the OAuth3 TEE Proxy, using pytest as the testing framework.

## Test Structure

Tests are organized in the following directories:

- `unit/`: Unit tests that test individual components in isolation
- `integration/`: Integration tests that test multiple components together

## Running Tests

### Running All Tests

```bash
pytest
```

### Running Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run tests for specific components
pytest -m cookie_auth
pytest -m oauth_auth
```

### Running Specific Test Files

```bash
# Run a specific test file
pytest tests/unit/plugins/twitter/auth/test_cookie_auth.py

# Run a specific test function
pytest tests/unit/plugins/twitter/auth/test_cookie_auth.py::TestTwitterCookieAuthorizationPlugin::test_credentials_from_string
```

## Test Fixtures

The tests use fixtures defined in `conftest.py` to set up common test resources:

- `test_db`: In-memory SQLite database for testing
- `app`: FastAPI app with test database dependency override
- `client`: Test client for the app
- `test_user`: Test user in the database
- `test_twitter_account`: Test Twitter account in the database
- `test_twitter_cookie_credentials`: Test Twitter cookie credentials
- `test_twitter_oauth_credentials`: Test Twitter OAuth credentials
- `mock_twitter_cookie_auth_plugin`: Mock for the Twitter cookie auth plugin
- `mock_twitter_oauth_auth_plugin`: Mock for the Twitter OAuth auth plugin
- `mock_twitter_resource_plugin`: Mock for the Twitter resource plugin

## Writing Tests

### Unit Tests

Unit tests should test individual components in isolation, mocking any dependencies:

```python
@pytest.mark.unit
@pytest.mark.cookie_auth
def test_some_function():
    # Test a function in isolation
    ...
```

### Integration Tests

Integration tests should test multiple components together:

```python
@pytest.mark.integration
@pytest.mark.oauth_auth
def test_some_integration():
    # Test multiple components together
    ...
```