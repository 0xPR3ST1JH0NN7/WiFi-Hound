"""Offensive-operation framework with hard guardrails.

These operations interact with *real* radio hardware and other people's
networks. They are therefore:

  * disabled unless the server is started with ``--enable-offensive`` (or the
    ``WIFIHOUND_OFFENSIVE=1`` env var) **and** the process runs as root;
  * gated behind an explicit per-request authorization acknowledgement;
  * dependency-checked (the required external tools must exist);
  * logged.

Only use them on networks you own or are explicitly authorized in writing to
test. Unauthorized deauthentication / interception is illegal in most
jurisdictions.
"""

from __future__ import annotations

import logging
import os
import shutil

logger = logging.getLogger("wifihound.operations")


class OperationError(RuntimeError):
    """Raised when an operation is refused or fails."""


class OperationNotAuthorized(OperationError):
    """Raised when the offensive subsystem or per-request gate blocks a call."""


def offensive_enabled() -> bool:
    """Whether the offensive subsystem is switched on for this process."""
    return os.environ.get("WIFIHOUND_OFFENSIVE") == "1"


def set_offensive_enabled(enabled: bool) -> None:
    os.environ["WIFIHOUND_OFFENSIVE"] = "1" if enabled else "0"


def _is_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def require_authorization(acknowledged: bool) -> None:
    """Enforce every guardrail before an offensive operation may run."""
    if not offensive_enabled():
        raise OperationNotAuthorized(
            "Offensive operations are disabled. Restart the server with "
            "--enable-offensive (authorized testing only)."
        )
    if not _is_root():
        raise OperationNotAuthorized(
            "Offensive operations require root privileges (radio access)."
        )
    if not acknowledged:
        raise OperationNotAuthorized(
            "Authorization not acknowledged for this action."
        )


def require_tools(*tools: str) -> None:
    missing = [t for t in tools if shutil.which(t) is None]
    if missing:
        raise OperationError(
            f"Required tool(s) not found on PATH: {', '.join(missing)}. "
            "Install the aircrack-ng suite."
        )
