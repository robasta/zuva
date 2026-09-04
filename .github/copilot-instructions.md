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
- `get_power()` → float (in W, as reported by the inverter)
- `get_voltage()` → float (in V)
- `get_current()` → float (in A)

`Grid` reads these from `vip[0]`, not from `pac`, and returns `None` when `vip` is empty.

## Development Workflow

### Environment Setup
```bash
./scripts/setup.sh  # Creates venv and installs deps
```

### Testing & Quality
- pytest with `pytest-asyncio` in strict mode; `pytest.ini` supplies `pythonpath = .`
- `tests/mock_api_server.py` is an in-process stand-in for the aiohttp session, not a server - extend this for new endpoints
- Run tests: `./run-tests.sh` (coverage over all three packages, 85% gate). Extra args go to pytest: `./run-tests.sh -k grid_outage`
- Linting: `./scripts/run-pylint.sh` (pylint 3.x over `sunsynk zuva zuva_api`; it fails the build on findings)

### Version Management
- Git tag-based versioning via `sunsynk/version_info.py`
- `Version.generate()` creates `version.py` from git describe, falling back to the `SUNSYNK_API_CLIENT_VERSION` env var when git or the history is absent (the container builds rely on that fallback)
- Called automatically during setup.py execution

## Key Files & Dependencies

### Critical Components
- `sunsynk/client.py` - Main API client with auth handling
- `sunsynk/resource.py` - Base class for all data models
- `tests/mock_api_server.py` - Extensible mock for testing
- `scripts/manual/check_sunsynk_login.py` - Live login check against the real API

The repo also ships two services that consume the library: `zuva/collector/`
(polling and alert evaluation) and `zuva_api/` (FastAPI notification service).
See CLAUDE.md for how those fit together.

### External Dependencies
- `aiohttp` - HTTP client (not requests)
- `cryptography` - RSA password encryption during login
- `pytest-asyncio` - async test support

## Testing Conventions

### Mock API Extensions
When adding new endpoints, extend `tests/mock_api_server.py`:
1. Add the path and its response body to `default_routes()`
2. Use hardcoded test data following existing patterns (e.g., inverter SN: '1029384756'), with readings as strings - the real API returns them that way
3. Per-test overrides go through `api.set_body(...)` / `api.set_status(...)`; `api.paths()` and `api.last()` assert on what was requested

### Async Test Pattern
No socket is opened: the mock replaces the client's session directly.
```python
@pytest_asyncio.fixture
async def client(api):
    client = SunsynkClient("user", "pass", BASE_URL)
    client.session = api
    await client.login()
    return client
```

## Common Gotchas
- Always use `async with SunsynkClient()` pattern for proper cleanup
- API responses are nested under `data` key: `body['data']`
- Authentication failures raise `InvalidCredentialsException`
- Model constructors expect raw API response data, not pre-processed
- The session is created lazily on the first request, so a constructed client holds no socket
- `login()` self-throttles; the internal 401 refresh uses `login(force=True)` to bypass it
- Tests run against Python 3.10 and 3.11 in CI