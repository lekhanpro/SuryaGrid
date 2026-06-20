"""Standard API response format for Suryagrid AI."""

from typing import Any
from datetime import datetime, timezone


def success_response(data: Any = None, message: str = "OK") -> dict:
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def error_response(error_code: str, message: str, details: Any = None) -> dict:
    return {
        "success": False,
        "error_code": error_code,
        "message": message,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
