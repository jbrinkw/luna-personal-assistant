# Luna Tests

Comprehensive integration and unit tests for the Luna platform.

## Running Tests

### Prerequisites

1. **Start all services**:
```bash
# Windows
core\scripts\start_all.bat

# Linux/Mac
./core/scripts/start_all.sh
```

2. **Install test dependencies**:
```bash
pip install pytest requests
```

### Run All Tests

```bash
# From project root
pytest tests/ -v

# Or run specific test file
pytest tests/test_services.py -v

# Run with more detail
pytest tests/ -v --tb=short
```

### Test Coverage

The test suite covers:

#### Core Services (`test_services.py`)
- ✅ Agent API health checks
- ✅ Agent API model listing
- ✅ CORS configuration
- ✅ Hub UI accessibility

#### Automation Memory Extension
- ✅ Backend health checks
- ✅ Agent discovery via backend
- ✅ Memories CRUD operations
- ✅ Task flows CRUD with agent selection
- ✅ Scheduled prompts CRUD with agent selection
- ✅ UI accessibility

#### Agent Discovery
- ✅ Local agent discovery from filesystem
- ✅ Agent discovery via API
- ✅ Verification of both agents (simple_agent, passthrough_agent)

#### Extension Discovery
- ✅ Extension structure validation
- ✅ Config file validation
- ✅ Tool discovery
- ✅ UI and backend presence

#### Health Check Scripts
- ✅ Health check script existence
- ✅ Stop scripts existence
- ✅ Cross-platform scripts (.sh, .bat)

## Test Categories

### Integration Tests
Located in `test_services.py`, these tests verify:
- Service-to-service communication
- API endpoints
- Database operations
- Extension integration

### Unit Tests (TODO)
- Individual agent logic
- Tool validation
- Extension discovery logic
- LLM selector functionality

## Continuous Testing

For development, you can use pytest-watch to run tests automatically:

```bash
pip install pytest-watch
ptw tests/ -- -v
```

## Expected Results

When all services are running correctly, you should see:
```
============ test session starts ============
collected 18 items

tests/test_services.py::TestCoreServices::test_agent_api_health PASSED     [  5%]
tests/test_services.py::TestCoreServices::test_agent_api_models_list PASSED [ 11%]
tests/test_services.py::TestCoreServices::test_agent_api_cors PASSED       [ 16%]
...
============ 18 passed in 5.23s ============
```

## Troubleshooting

### Services Not Running
If tests fail with connection errors:
1. Run `python core/scripts/health_check.py` to check service status
2. Ensure all services are running
3. Check that ports are not in use by other applications

### Database Errors
If you get database errors:
1. Ensure Postgres is running
2. Run the migration script: `psql -U postgres -f scripts/migrate_db.sql`
3. Check `.env` has correct database credentials

### Import Errors
If you get import errors:
1. Ensure you're running from project root
2. Install all requirements: `pip install -r requirements.txt`
3. Check Python path includes project root

