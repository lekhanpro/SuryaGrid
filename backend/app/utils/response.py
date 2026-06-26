"""Standard API response format for Suryagrid AI."""

from datetime import UTC, datetime
from typing import Any


def success_response(data: Any = None, message: str = "OK") -> dict:
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def error_response(error_code: str, message: str, details: Any = None) -> dict:
    return {
        "success": False,
        "error_code": error_code,
        "message": message,
        "details": details,
        "timestamp": datetime.now(UTC).isoformat(),
    }
