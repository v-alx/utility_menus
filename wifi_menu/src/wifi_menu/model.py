from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WifiNetwork:
    ssid: str
    security: str
    signal: int
    in_use: bool


@dataclass(frozen=True, slots=True)
class NetworkState:
    wifi_enabled: bool
    networks: list[WifiNetwork]
