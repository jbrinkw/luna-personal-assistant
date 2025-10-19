"""File utilities for testing"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


def file_exists(path: str) -> bool:
    """Check if file exists"""
    return Path(path).exists()


def read_json(path: str) -> Optional[Dict[Any, Any]]:
    """Read JSON file"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return None


def write_json(path: str, data: Dict[Any, Any]):
    """Write JSON file"""
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def is_valid_json(path: str) -> bool:
    """Check if file contains valid JSON"""
    return read_json(path) is not None


def has_keys(data: Dict[Any, Any], keys: list) -> bool:
    """Check if dict has all specified keys"""
    return all(key in data for key in keys)

