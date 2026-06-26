"""Offensive operations (guardrailed, authorized testing only)."""

from wifihound.operations.base import (  # noqa: F401
    OperationError,
    OperationNotAuthorized,
    offensive_enabled,
    set_offensive_enabled,
)

__all__ = [
    "OperationError",
    "OperationNotAuthorized",
    "offensive_enabled",
    "set_offensive_enabled",
]
