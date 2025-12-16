from __future__ import annotations
import os
import subprocess
from dataclasses import dataclass
from typing import Optional

from .model import NetworkState, WifiNetwork
from .parse import parse_connection_profile


@dataclass(frozen=True, slots=True)
class NmResult:
    ok: bool
    message: str = ""


class NmcliService:
    def __init__(self) -> None:
        # this worked for me - disabling the NM GUI prompt
        # so this app can do the prompting
        self._env_no_agent = os.environ.copy()
        self._env_no_agent["NM_CLI_AGENT"] = "0"

    def _run(
        self, args: list[str], *, check: bool = False, env: dict | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["nmcli", *args], text=True, capture_output=True, check=check, env=env
        )

    def get_state(self) -> NetworkState:
        wifi_status = self._run(["radio", "wifi"], check=True).stdout.strip()
        wifi_enabled = wifi_status == "enabled"

        networks: list[WifiNetwork] = []
        if wifi_enabled:
            result = self._run(
                [
                    "-t",
                    "-e",
                    "yes",
                    "-f",
                    "IN-USE,SSID,SECURITY,SIGNAL",
                    "device",
                    "wifi",
                    "list",
                ],
                check=True,
            )

            for line in result.stdout.splitlines():
                if not line:
                    continue
                in_use_flag, ssid, security, signal = parse_connection_profile(line, 3)
                network = WifiNetwork(
                    ssid=ssid,
                    security=security,
                    signal=int(signal or 0),
                    in_use=(in_use_flag == "*"),
                )
                networks.append(network)

        return NetworkState(wifi_enabled=wifi_enabled, networks=networks)

    def toggle_wifi(self, enabled: bool) -> NmResult:
        result = self._run(["radio", "wifi", "on" if enabled else "off"])
        msg = result.stderr.strip() or result.stdout.strip()
        return NmResult(ok=(result.returncode == 0), message=msg)

    def disconnect_wifi(self) -> NmResult:
        result = self._run(["-t", "-f", "DEVICE,TYPE,STATE", "device"], check=True)
        for line in result.stdout.splitlines():
            parts = parse_connection_profile(line)
            if len(parts) >= 3 and parts[1] == "wifi" and parts[2] == "connected":
                result2 = self._run(["device", "disconnect", parts[0]])
                msg = result2.stderr.strip() or result.stdout.strip()
                return NmResult(ok=(result2.returncode == 0), message=msg)
        return NmResult(ok=True, message="No connected Wi-Fi device found")

    def connect(
        self, ssid: str, *, password: Optional[str], security_hint: str | None = None
    ) -> NmResult:
        security = (security_hint or "").strip()
        is_open = security == "" or security == "--"

        self._run(["connection", "delete", ssid], env=self._env_no_agent)

        if is_open:
            result = self._run(
                ["device", "wifi", "connect", ssid], env=self._env_no_agent
            )
            msg = result.stderr.strip() or result.stdout.strip()
            return NmResult(ok=(result.returncode == 0), message=msg)

        if not password:
            return NmResult(ok=False, message="Password required")

        result = self._run(
            ["device", "wifi", "connect", ssid, "password", password],
            env=self._env_no_agent,
        )
        msg = result.stderr.strip() or result.stdout.strip()
        return NmResult(ok=(result.returncode == 0), message=msg)
