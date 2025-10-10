@echo off
REM Run database tests without waiting for services
set SKIP_SERVICE_CHECK=1
pytest tests/test_database.py -v --tb=short
pause




