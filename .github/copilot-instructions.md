# Copilot Instructions for Sunsynk API Client

## Project Overview
This is an async Python library for interfacing with Sunsynk solar inverter APIs. The codebase follows a client-resource pattern where `SunsynkClient` handles authentication and HTTP requests, while data models (`Battery`, `Grid`, `Input`, `Output`, etc.) inherit from a base `Resource` class.

## Architecture Patterns

### Core Client Pattern
- `SunsynkClient` uses aiohttp for async HTTP requests with OAuth2 bearer token auth
- Implements automatic token refresh on 401 responses (see `__get` method retry logic)
- Uses async context manager pattern (`__aenter__`/`__aexit__`) for proper session cleanup
- All API endpoints follow `/api/v1/` prefix convention

### Resource Model Pattern
All data models inherit from `Resource` base class which provides consistent `__repr__` formatting:
```python
class MyModel(Resource):
    def __init__(self, data):
        self.field = data.get('field')  # Always use .get() for optional fields
        self.required_field = data['required_field']  # Direct access for required fields
```

### Power/Electrical Data Convention
Models representing electrical measurements (`Battery`, `Grid`, `Input`) implement these methods:
- `get_power()` → float (in kW)
- `get_voltage()` → float (in V) 
- `get_current()` → float (in A)

## Development Workflow

### Environment Setup
```bash
./setup.sh  # Creates venv and installs deps
```

### Testing & Quality
- Tests use pytest with async support and aiohttp_client fixture
- Mock API server pattern in `tests/mock_api_server.py` - extend this for new endpoints
- Run tests: `./run-tests.sh` (uses pytest with coverage)
- Linting: `./run-pylint.sh` (pylint only, no other formatters)

### Version Management
- Git tag-based versioning via `sunsynk/version_info.py`
- `Version.generate()` creates `version.py` from git describe
- Called automatically during setup.py execution

## Key Files & Dependencies

### Critical Components
- `sunsynk/client.py` - Main API client with auth handling
- `sunsynk/resource.py` - Base class for all data models
- `tests/mock_api_server.py` - Extensible mock for testing
- `magic.py` - Example usage script for local testing

### External Dependencies
- `aiohttp` - HTTP client (not requests)
- `pytest-aiohttp` - Required for async HTTP testing
- `vcrpy` - HTTP interaction recording (though not actively used in current tests)

## Testing Conventions

### Mock API Extensions
When adding new endpoints, extend `MockApiServer`:
1. Add route in `__init__`: `self.app.router.add_get('/api/v1/new-endpoint', self.handler)`
2. Implement handler method returning JSON with proper structure
3. Use hardcoded test data following existing patterns (e.g., inverter SN: '1029384756')

### Async Test Pattern
```python
@pytest.mark.asyncio
async def test_new_feature(aiohttp_client, event_loop):
    mock_api_server = MockApiServer(aiohttp_client)
    client = await mock_api_server.client()
    # Test implementation
```

## Common Gotchas
- Always use `async with SunsynkClient()` pattern for proper cleanup
- API responses are nested under `data` key: `body['data']`
- Authentication failures raise `InvalidCredentialsException`
- Model constructors expect raw API response data, not pre-processed
- Tests run against Python 3.10.13 and 3.11.6 in CI