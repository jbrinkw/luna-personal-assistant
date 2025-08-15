"""
DEPRECATED: Use root-level `db_config.py` instead.

This module proxies to the unified config to avoid breaking imports.
"""

from typing import Dict
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from db_config import (
    get_db_config as _root_get_db_config,
    print_config as _root_print_config,
    get_connection as _root_get_connection,
)


def get_db_config() -> Dict[str, str]:
    return _root_get_db_config()


def print_config():
    _root_print_config()


def get_connection(autocommit: bool = False):
    return _root_get_connection(autocommit=autocommit)


if __name__ == "__main__":
    print_config()