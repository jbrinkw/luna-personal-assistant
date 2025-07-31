"""
Database Configuration Helper

This module automatically loads environment variables from a .env file if present.
You can either:
1. Create a .env file in the project root (recommended)
2. Set environment variables manually

Example .env file:
DB_HOST=192.168.1.93
DB_PORT=5432
DB_NAME=workout_tracker
DB_USER=postgres
DB_PASSWORD=your_password_here
"""

import os
from typing import Dict
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def get_db_config() -> Dict[str, str]:
    """Get database configuration from environment variables"""
    return {
        "host": os.environ.get("DB_HOST", "192.168.1.93"),
        "port": os.environ.get("DB_PORT", "5432"),
        "database": os.environ.get("DB_NAME", "workout_tracker"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
    }

def print_config():
    """Print current database configuration (without password)"""
    config = get_db_config()
    print("PostgreSQL Configuration:")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user']}")
    print(f"  Password: {'*' * len(config['password']) if config['password'] else '(not set)'}")

if __name__ == "__main__":
    print_config() 