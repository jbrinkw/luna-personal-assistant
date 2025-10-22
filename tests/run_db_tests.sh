#!/bin/bash
# Run database tests without waiting for services
export SKIP_SERVICE_CHECK=1
pytest tests/test_database.py -v --tb=short




