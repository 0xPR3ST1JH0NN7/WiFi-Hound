"""Geolocation enrichment hooks.

airodump CSV carries no coordinates, so this is a deliberately small, offline
placeholder that other sources (GPS-tagged Kismet captures, WiGLE exports, a
local lookup service) can plug into later. It never performs network calls on
its own — wire a provider in via :func:`set_provider`.
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple

# A provider takes a BSSID and returns (lat, lon) or None.
_provider: Optional[Callable[[str], Optional[Tuple[float, float]]]] = None


def set_provider(fn: Callable[[str], Optional[Tuple[float, float]]]) -> None:
    """Register a geolocation provider (e.g. a local WiGLE-style lookup)."""
    global _provider
    _provider = fn


def locate(bssid: str) -> Optional[Tuple[float, float]]:
    if _provider is None:
        return None
    try:
        return _provider(bssid)
    except Exception:
        return None


def enrich_scan(scan) -> int:
    """Populate lat/lon on APs using the registered provider. Returns count."""
    if _provider is None:
        return 0
    located = 0
    for ap in scan.access_points:
        coords = locate(ap.bssid)
        if coords:
            ap.lat, ap.lon = coords
            located += 1
    return located
