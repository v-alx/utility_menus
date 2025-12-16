import os
import subprocess
from dataclasses import dataclass
from typing import List
from enum import Enum, auto


@dataclass
class WifiNetwork:
    ssid: str
    security: str
    signal: int
    in_use: bool


@dataclass
class NetworkState:
    wifi_enabled: bool
    networks: List[WifiNetwork]


class Action(Enum):
    BACK = auto()
    DONE = auto()


def run_fuzzel(input: str | None, args: list[str] | None):
    cmd: list[str] = ["fuzzel", "--dmenu", "-a", "top-right"]
    if args is not None:
        cmd += list(args)

    result = subprocess.run(
        cmd,
        input=input,
        text=True,
        capture_output=True,
        check=True,
    )
    return result


def run_nmcli(args: list[str], *, check: bool = True, env: dict | None = None):
    result = subprocess.run(
        ["nmcli", *args],
        text=True,
        capture_output=True,
        check=check,
        env=env if env is not None else None,
    )
    return result


def split_nmcli_output(s, maxsplit=-1):
    parts = []
    cur = []

    splits = 0
    esc = "\\"
    sep = ":"

    n = len(s)
    i = 0
    while i < n:
        ch = s[i]

        if ch == esc and i + 1 < n:
            cur.append(s[i + 1])
            i += 2
            continue

        if ch == sep and (maxsplit < 0 or splits < maxsplit):
            parts.append("".join(cur))
            cur = []
            splits += 1
            i += 1
            continue

        cur.append(ch)
        i += 1

    parts.append("".join(cur))
    return parts


def get_network_state() -> NetworkState:
    wifi_status = run_nmcli(["radio", "wifi"]).stdout.strip()
    wifi_enabled = wifi_status == "enabled"

    networks: List[WifiNetwork] = []

    if wifi_enabled:
        cmd = [
            "-t",
            "-e",
            "yes",
            "-f",
            "IN-USE,SSID,SECURITY,SIGNAL",
            "device",
            "wifi",
            "list",
        ]
        output = run_nmcli(cmd)

        for line in output.stdout.splitlines():
            if not line:
                continue
            fields = split_nmcli_output(line, 3)
            in_use_flag, ssid, security, signal = fields
            networks.append(
                WifiNetwork(
                    ssid=ssid,
                    security=security,
                    signal=int(signal or 0),
                    in_use=(in_use_flag == "*"),
                )
            )

    return NetworkState(wifi_enabled=wifi_enabled, networks=networks)


def build_top_menu(state: NetworkState) -> list[str]:
    wifi_status = "on" if state.wifi_enabled else "off"
    items = [
        f"Toggle Wi-Fi (currently: {wifi_status})",
        "Available Networks...",
        "Disconnect",
        "Advanced",
    ]
    return items


def build_networks_menu(state: NetworkState) -> list[str]:
    items: list[str] = []
    for network in state.networks:
        prefix = "* " if network.in_use else "  "
        label = network.ssid or "<hidden>"
        items.append(f"{prefix}{label}  ({network.signal}%)")

    return items


def show_menu(items: list[str]) -> str | None:
    menu_text = "\n".join(items)
    rows_length = len(menu_text.splitlines())
    if rows_length > 30:
        rows_length = 30
    args = ["-l", f"{rows_length}"]

    result = run_fuzzel(menu_text, args)
    if result.returncode != 0:
        return None
    choice = result.stdout.strip()
    return choice or None


def find_network_by_ssid(ssid: str, state: NetworkState) -> WifiNetwork | None:
    return next((n for n in state.networks if n.ssid == ssid), None)


def choice_to_ssid(choice: str) -> str | None:
    if choice.startswith(("* ", "  ")):
        choice = choice[2:]

    if "(" in choice:
        ssid = choice.rsplit("(", 1)[0].strip()
    else:
        ssid = choice.strip()

    return ssid or None


def prompt_for_password() -> str | None:
    args = [
        "--prompt-only=Password: ",
        "--password",
        "--cache=/dev/null",
    ]
    result = run_fuzzel(None, args)
    if result.returncode != 0:
        return None
    password = result.stdout.strip()
    return password or None


def nm_no_agent_env() -> dict:
    env = os.environ.copy()
    env["NM_CLI_AGENT"] = "0"
    return env


def connect_network(choice: str, state: NetworkState) -> None:
    ssid = choice_to_ssid(choice)
    if not ssid:
        return

    net = find_network_by_ssid(ssid, state)

    security = (net.security if net else "").strip()
    no_agent_env = os.environ.copy()
    no_agent_env["NM_CLI_AGENT"] = "0"

    run_nmcli(["connection", "delete", ssid], check=False, env=no_agent_env)

    is_open = security == "" or security == "--"

    if is_open:
        r = run_nmcli(
            ["device", "wifi", "connect", ssid],
            check=False,
            env=no_agent_env,
        )
        if r.returncode != 0:
            print(r.stderr.strip() or r.stdout.strip())
        return

    password = prompt_for_password()
    if not password:
        return

    r = run_nmcli(
        ["device", "wifi", "connect", ssid, "password", password],
        check=False,
        env=no_agent_env,
    )

    if r.returncode != 0:
        print(r.stderr.strip() or r.stdout.strip())


def handle_choice(choice: str, state: NetworkState) -> Action:
    if choice.startswith("Toggle Wi-Fi"):
        new_state = "off" if state.wifi_enabled else "on"
        cmd = ["radio", "wifi", new_state]
        run_nmcli(cmd)
        return Action.DONE

    if choice.startswith("Available Networks..."):
        items = build_networks_menu(state)
        netchoice = show_menu(items)
        if netchoice is None:
            # should go back to main menu
            return Action.BACK

        connect_network(netchoice, state)
        return Action.DONE

    return Action.BACK


def main():
    while True:
        state = get_network_state()
        items = build_top_menu(state)
        choice = show_menu(items)

        if choice is None:
            return

        action = handle_choice(choice, state)
        if action is Action.BACK:
            continue
        if action is Action.DONE:
            return

        print(f"selected: {choice}")


if __name__ == "__main__":
    main()
