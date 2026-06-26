"""Offensive operations (guardrailed, authorized testing only)."""

from wifihound.operations.base import (  # noqa: F401
    OperationError,
    OperationNotAuthorized,
    offensive_available,
)

__all__ = [
    "OperationError",
    "OperationNotAuthorized",
    "offensive_available",
]
