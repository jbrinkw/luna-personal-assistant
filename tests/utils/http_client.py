"""HTTP client utilities for testing"""
import requests
from typing import Optional, Dict, Any


def get(url: str, timeout: int = 5) -> tuple[int, Optional[Dict[Any, Any]]]:
    """
    Perform GET request
    Returns: (status_code, json_data or None)
    """
    try:
        response = requests.get(url, timeout=timeout)
        try:
            return response.status_code, response.json()
        except:
            return response.status_code, None
    except Exception as e:
        return 0, None


def post(url: str, data: Dict[Any, Any], timeout: int = 5) -> tuple[int, Optional[Dict[Any, Any]]]:
    """
    Perform POST request
    Returns: (status_code, json_data or None)
    """
    try:
        response = requests.post(url, json=data, timeout=timeout)
        try:
            return response.status_code, response.json()
        except:
            return response.status_code, None
    except Exception as e:
        return 0, None


def put(url: str, data: Dict[Any, Any], timeout: int = 5) -> tuple[int, Optional[Dict[Any, Any]]]:
    """
    Perform PUT request
    Returns: (status_code, json_data or None)
    """
    try:
        response = requests.put(url, json=data, timeout=timeout)
        try:
            return response.status_code, response.json()
        except:
            return response.status_code, None
    except Exception as e:
        return 0, None


def patch(url: str, data: Dict[Any, Any], timeout: int = 5) -> tuple[int, Optional[Dict[Any, Any]]]:
    """
    Perform PATCH request
    Returns: (status_code, json_data or None)
    """
    try:
        response = requests.patch(url, json=data, timeout=timeout)
        try:
            return response.status_code, response.json()
        except:
            return response.status_code, None
    except Exception as e:
        return 0, None


def delete(url: str, timeout: int = 5) -> tuple[int, Optional[Dict[Any, Any]]]:
    """
    Perform DELETE request
    Returns: (status_code, json_data or None)
    """
    try:
        response = requests.delete(url, timeout=timeout)
        try:
            return response.status_code, response.json()
        except:
            return response.status_code, None
    except Exception as e:
        return 0, None

